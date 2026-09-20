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
    lastExecutedAt: row.last_executed_at
      ? String(row.last_executed_at)
      : null,
  };
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

  const rows = await sql.query<Record<string, unknown>>(
    `insert into keyword_actions
      (owner_id, name, trigger_type, trigger_value, scope, conditions, actions,
       delay_min, delay_max, cooldown_seconds)
     values ($1,$2,$3,$4,$5,$6::jsonb,$7::jsonb,$8,$9,$10)
     returning *`,
    [
      input.ownerId,
      input.name,
      input.triggerType ?? "contains",
      input.triggerValue,
      input.scope ?? "all",
      JSON.stringify(input.conditions ?? {}),
      JSON.stringify(input.actions ?? []),
      input.delayMin ?? 0,
      input.delayMax ?? 0,
      input.cooldownSeconds ?? 0,
    ],
  );

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

export function matchesKeywordRule(rule: KeywordRule, text: string) {
  const source = text.trim();
  const target = rule.triggerValue.trim();

  switch (rule.triggerType) {
    case "exact":
      return source.localeCompare(target, undefined, {
        sensitivity: "accent",
      }) === 0;
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
