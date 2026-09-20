import { getSql } from "./db";

export type KeywordTriggerType =
  | "exact"
  | "contains"
  | "starts_with"
  | "ends_with"
  | "regex";

export type KeywordAction = {
  type: "reply" | "notify" | "log";
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

export function isKeywordRuleOnCooldown(rule: KeywordRule, now = Date.now()) {
  if (!rule.lastExecutedAt || rule.cooldownSeconds <= 0) return false;
  const last = new Date(rule.lastExecutedAt).getTime();
  return Number.isFinite(last)
    && now - last < rule.cooldownSeconds * 1000;
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
) {
  const rules = await listKeywordRules(ownerId);
  return rules.filter(
    (rule) => matchesKeywordRule(rule, text) && !isKeywordRuleOnCooldown(rule),
  );
}
