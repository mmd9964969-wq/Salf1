import { getSql } from "./db";

export type KeywordTriggerType =
  | "exact"
  | "contains"
  | "starts_with"
  | "ends_with"
  | "regex";

export type KeywordMatchContext = {
  userId?: string | number | null;
  chatId?: string | number | null;
  chatType?: string | null;
  now?: Date;
};

export type KeywordConditions = {
  user_ids?: Array<string | number>;
  chat_ids?: Array<string | number>;
  chat_types?: string[];
  excluded_user_ids?: Array<string | number>;
  excluded_chat_ids?: Array<string | number>;
  time_start?: string;
  time_end?: string;
  max_executions?: number;
};

export type KeywordAction = {
  type: "reply" | "notify" | "log" | "react" | "delete" | "forward";
  text?: string;
};

export type KeywordRule = {
  id: number;
  ownerId: string;
  name: string;
  triggerType: KeywordTriggerType;
  triggerValue: string;
  scope: string;
  conditions: Record<string, unknown>;
  actions: KeywordAction[];
  delayMin: number;
  delayMax: number;
  cooldownSeconds: number;
  enabled: boolean;
  executionCount: number;
  lastExecutedAt: string | null;
};

function parseJson<T>(value: unknown, fallback: T): T {
  if (typeof value !== "string") return (value as T) ?? fallback;
  try {
    return JSON.parse(value) as T;
  } catch {
    return fallback;
  }
}

function mapRule(row: Record<string, unknown>): KeywordRule {
  return {
    id: Number(row.id),
    ownerId: String(row.owner_id),
    name: String(row.name),
    triggerType: String(row.trigger_type) as KeywordTriggerType,
    triggerValue: String(row.trigger_value),
    scope: String(row.scope),
    conditions: parseJson(row.conditions, {}),
    actions: parseJson(row.actions, []),
    delayMin: Number(row.delay_min),
    delayMax: Number(row.delay_max),
    cooldownSeconds: Number(row.cooldown_seconds),
    enabled: Boolean(row.enabled),
    executionCount: Number(row.execution_count),
    lastExecutedAt: row.last_executed_at ? String(row.last_executed_at) : null,
  };
}

function validateInput(input: {
  name: string;
  triggerValue: string;
  triggerType?: KeywordTriggerType;
  delayMin?: number;
  delayMax?: number;
  cooldownSeconds?: number;
}) {
  const name = input.name.trim();
  const triggerValue = input.triggerValue.trim();
  const type = input.triggerType ?? "contains";
  const delayMin = Math.max(0, Math.floor(input.delayMin ?? 0));
  const delayMax = Math.max(delayMin, Math.floor(input.delayMax ?? delayMin));
  const cooldownSeconds = Math.max(0, Math.floor(input.cooldownSeconds ?? 0));

  if (!name) throw new Error("نام قانون نمی‌تواند خالی باشد.");
  if (!triggerValue) throw new Error("محرک قانون نمی‌تواند خالی باشد.");
  if (type === "regex") {
    try {
      new RegExp(triggerValue, "iu");
    } catch {
      throw new Error("الگوی Regex معتبر نیست.");
    }
  }

  return { name, triggerValue, type, delayMin, delayMax, cooldownSeconds };
}

export async function createKeywordRule(input: {
  ownerId: string;
  name: string;
  triggerType?: KeywordTriggerType;
  triggerValue: string;
  scope?: string;
  conditions?: Record<string, unknown>;
  actions?: KeywordAction[];
  delayMin?: number;
  delayMax?: number;
  cooldownSeconds?: number;
}) {
  const sql = await getSql();
  const value = validateInput(input);

  const rows = await sql.query<Record<string, unknown>>(
    `insert into keyword_actions
      (owner_id, name, trigger_type, trigger_value, scope, conditions, actions,
       delay_min, delay_max, cooldown_seconds)
     values ($1,$2,$3,$4,$5,$6::jsonb,$7::jsonb,$8,$9,$10)
     returning *`,
    [
      input.ownerId,
      value.name,
      value.type,
      value.triggerValue,
      input.scope?.trim() || "all",
      JSON.stringify(input.conditions ?? {}),
      JSON.stringify(input.actions ?? []),
      value.delayMin,
      value.delayMax,
      value.cooldownSeconds,
    ],
  );

  if (!rows[0]) throw new Error("قانون ایجاد نشد.");
  return mapRule(rows[0]);
}

export async function listKeywordRules(ownerId: string) {
  const sql = await getSql();
  const rows = await sql.query<Record<string, unknown>>(
    "select * from keyword_actions where owner_id = $1 order by id desc",
    [ownerId],
  );
  return rows.map(mapRule);
}

export async function getKeywordRule(ownerId: string, id: number) {
  const sql = await getSql();
  const rows = await sql.query<Record<string, unknown>>(
    "select * from keyword_actions where owner_id = $1 and id = $2 limit 1",
    [ownerId, id],
  );
  return rows[0] ? mapRule(rows[0]) : null;
}

export async function updateKeywordRuleConditions(
  ownerId: string,
  id: number,
  conditions: Record<string, unknown>,
) {
  const sql = await getSql();
  const rows = await sql.query<Record<string, unknown>>(
    `update keyword_actions
     set conditions = $3::jsonb, updated_at = now()
     where owner_id = $1 and id = $2
     returning *`,
    [ownerId, id, JSON.stringify(conditions)],
  );
  return rows[0] ? mapRule(rows[0]) : null;
}

export async function updateKeywordRuleActions(
  ownerId: string,
  id: number,
  actions: KeywordAction[],
) {
  const sql = await getSql();
  const rows = await sql.query<Record<string, unknown>>(
    `update keyword_actions
     set actions = $3::jsonb, updated_at = now()
     where owner_id = $1 and id = $2
     returning *`,
    [ownerId, id, JSON.stringify(actions)],
  );
  return rows[0] ? mapRule(rows[0]) : null;
}

export async function setKeywordRuleEnabled(
  ownerId: string,
  id: number,
  enabled: boolean,
) {
  const sql = await getSql();
  const rows = await sql.query<Record<string, unknown>>(
    `update keyword_actions
     set enabled = $3, updated_at = now()
     where owner_id = $1 and id = $2
     returning *`,
    [ownerId, id, enabled],
  );
  return rows[0] ? mapRule(rows[0]) : null;
}

export async function deleteKeywordRule(ownerId: string, id: number) {
  const sql = await getSql();
  const rows = await sql.query<Record<string, unknown>>(
    "delete from keyword_actions where owner_id = $1 and id = $2 returning id",
    [ownerId, id],
  );
  return rows.length > 0;
}

export async function markKeywordRuleExecuted(ownerId: string, id: number) {
  const sql = await getSql();
  const rows = await sql.query<Record<string, unknown>>(
    `update keyword_actions
     set execution_count = execution_count + 1,
         last_executed_at = now(),
         updated_at = now()
     where owner_id = $1 and id = $2
     returning *`,
    [ownerId, id],
  );
  return rows[0] ? mapRule(rows[0]) : null;
}

function normalizeList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.map((item) => String(item).trim()).filter(Boolean);
}

function timeInWindow(now: Date, start?: string, end?: string) {
  if (!start || !end) return true;
  const startMatch = /^(\\d{2}):(\\d{2})$/.exec(start);
  const endMatch = /^(\\d{2}):(\\d{2})$/.exec(end);
  if (!startMatch || !endMatch) return false;
  const startMinutes = Number(startMatch[1]) * 60 + Number(startMatch[2]);
  const endMinutes = Number(endMatch[1]) * 60 + Number(endMatch[2]);
  const current = now.getHours() * 60 + now.getMinutes();
  if (startMinutes === endMinutes) return true;
  if (startMinutes < endMinutes) return current >= startMinutes && current < endMinutes;
  return current >= startMinutes || current < endMinutes;
}

export type KeywordActionPolicyResult = { allowed: true } | { allowed: false; reason: string };

export function validateKeywordActionPolicy(action: KeywordAction): KeywordActionPolicyResult {
  if (!action || !action.type) return { allowed: false, reason: "نوع اقدام مشخص نیست." };
  if (["reply", "react", "forward"].includes(action.type) && !String(action.text ?? "").trim()) {
    return { allowed: false, reason: "این اقدام به مقدار نیاز دارد." };
  }
  if (action.type === "react") {
    const value = String(action.text ?? "").trim();
    if (value.length > 16) return { allowed: false, reason: "واکنش نامعتبر است." };
  }
  if (action.type === "forward") {
    const target = String(action.text ?? "").trim();
    if (!/^(?:-?\\d+|@[A-Za-z0-9_]{5,32})$/.test(target)) {
      return { allowed: false, reason: "مقصد فوروارد باید شناسه عددی یا @username معتبر باشد." };
    }
  }
  if (!["reply", "notify", "log", "react", "delete", "forward"].includes(action.type)) {
    return { allowed: false, reason: "نوع اقدام پشتیبانی نمی‌شود." };
  }
  return { allowed: true };
}

export function explainKeywordConditions(
  rule: KeywordRule,
  context: KeywordMatchContext = {},
): { matched: boolean; reason: string } {
  const conditions = (rule.conditions ?? {}) as KeywordConditions;
  const userId = context.userId == null ? "" : String(context.userId);
  const chatId = context.chatId == null ? "" : String(context.chatId);
  const chatType = String(context.chatType ?? "").trim().toLocaleLowerCase();
  const userIds = normalizeList(conditions.user_ids);
  const chatIds = normalizeList(conditions.chat_ids);
  const chatTypes = normalizeList(conditions.chat_types).map(x => x.toLocaleLowerCase());
  const excludedUsers = normalizeList(conditions.excluded_user_ids);
  const excludedChats = normalizeList(conditions.excluded_chat_ids);
  if (userIds.length && !userIds.includes(userId)) return { matched:false, reason:"user_not_allowed" };
  if (chatIds.length && !chatIds.includes(chatId)) return { matched:false, reason:"chat_not_allowed" };
  if (chatTypes.length && !chatTypes.includes(chatType)) return { matched:false, reason:"chat_type_not_allowed" };
  if (excludedUsers.includes(userId)) return { matched:false, reason:"user_excluded" };
  if (excludedChats.includes(chatId)) return { matched:false, reason:"chat_excluded" };
  const maxExecutions = Number(conditions.max_executions);
  if (Number.isFinite(maxExecutions) && maxExecutions > 0 && rule.executionCount >= maxExecutions) return { matched:false, reason:"max_executions_reached" };
  if (!timeInWindow(context.now ?? new Date(), conditions.time_start, conditions.time_end)) return { matched:false, reason:"outside_time_window" };
  return { matched:true, reason:"matched" };
}

export function matchesKeywordConditions(
  rule: KeywordRule,
  context: KeywordMatchContext = {},
) {
  const conditions = (rule.conditions ?? {}) as KeywordConditions;
  const userId = context.userId == null ? "" : String(context.userId);
  const chatId = context.chatId == null ? "" : String(context.chatId);
  const chatType = String(context.chatType ?? "").trim().toLocaleLowerCase();

  const userIds = normalizeList(conditions.user_ids);
  const chatIds = normalizeList(conditions.chat_ids);
  const chatTypes = normalizeList(conditions.chat_types).map((item) =>
    item.toLocaleLowerCase(),
  );
  const excludedUsers = normalizeList(conditions.excluded_user_ids);
  const excludedChats = normalizeList(conditions.excluded_chat_ids);

  if (userIds.length && !userIds.includes(userId)) return false;
  if (chatIds.length && !chatIds.includes(chatId)) return false;
  if (chatTypes.length && !chatTypes.includes(chatType)) return false;
  if (excludedUsers.includes(userId)) return false;
  if (excludedChats.includes(chatId)) return false;

  const maxExecutions = Number(conditions.max_executions);
  if (Number.isFinite(maxExecutions) && maxExecutions > 0 && rule.executionCount >= maxExecutions) {
    return false;
  }

  if (!timeInWindow(context.now ?? new Date(), conditions.time_start, conditions.time_end)) {
    return false;
  }

  return true;
}

export function getKeywordCooldownRemaining(rule: KeywordRule, now = Date.now()) {
  if (!rule.lastExecutedAt || rule.cooldownSeconds <= 0) return 0;
  const last = new Date(rule.lastExecutedAt).getTime();
  if (!Number.isFinite(last)) return 0;
  return Math.max(0, rule.cooldownSeconds - Math.floor((now - last) / 1000));
}

export function isKeywordRuleOnCooldown(rule: KeywordRule, now = Date.now()) {
  return getKeywordCooldownRemaining(rule, now) > 0;
}

export function matchesKeywordRule(rule: KeywordRule, text: string) {
  if (!rule.enabled || !text.trim()) return false;
  const source = text.trim();
  const target = rule.triggerValue.trim();

  switch (rule.triggerType) {
    case "exact":
      return source.toLocaleLowerCase() === target.toLocaleLowerCase();
    case "contains":
      return source.toLocaleLowerCase().includes(target.toLocaleLowerCase());
    case "starts_with":
      return source.toLocaleLowerCase().startsWith(target.toLocaleLowerCase());
    case "ends_with":
      return source.toLocaleLowerCase().endsWith(target.toLocaleLowerCase());
    case "regex":
      try {
        return new RegExp(target, "iu").test(source);
      } catch {
        return false;
      }
  }
}

export async function findMatchingKeywordRules(
  ownerId: string,
  text: string,
  context: KeywordMatchContext = {},
) {
  const rules = await listKeywordRules(ownerId);
  return rules.filter(
    (rule) =>
      matchesKeywordRule(rule, text) &&
      matchesKeywordConditions(rule, context) &&
      !isKeywordRuleOnCooldown(rule),
  );
}
