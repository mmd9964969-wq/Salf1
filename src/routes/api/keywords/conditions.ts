import { createFileRoute } from "@tanstack/react-router";
import {
  getKeywordRule,
  updateKeywordRuleConditions,
  type KeywordConditions,
} from "@/lib/keyword-engine";
import { requireUserId, UnauthorizedError } from "@/lib/auth/verify.server";

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
}

function cleanList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.map((item) => String(item).trim()).filter(Boolean);
}

function validTime(value: unknown) {
  return value == null || value === "" || /^\d{2}:\d{2}$/.test(String(value));
}

function normalizeConditions(input: unknown): KeywordConditions {
  if (!input || typeof input !== "object") throw new Error("شرایط نامعتبر است.");
  const raw = input as Record<string, unknown>;
  const conditions: KeywordConditions = {};

  const userIds = cleanList(raw.user_ids);
  const chatIds = cleanList(raw.chat_ids);
  const chatTypes = cleanList(raw.chat_types).map((x) => x.toLocaleLowerCase());
  const excludedUsers = cleanList(raw.excluded_user_ids);
  const excludedChats = cleanList(raw.excluded_chat_ids);

  if (userIds.length) conditions.user_ids = userIds;
  if (chatIds.length) conditions.chat_ids = chatIds;
  if (chatTypes.length) conditions.chat_types = chatTypes;
  if (excludedUsers.length) conditions.excluded_user_ids = excludedUsers;
  if (excludedChats.length) conditions.excluded_chat_ids = excludedChats;

  if (!validTime(raw.time_start) || !validTime(raw.time_end)) {
    throw new Error("فرمت زمان باید HH:MM باشد.");
  }
  if (raw.time_start) conditions.time_start = String(raw.time_start);
  if (raw.time_end) conditions.time_end = String(raw.time_end);

  if (raw.max_executions !== undefined && raw.max_executions !== "" && raw.max_executions !== null) {
    const max = Number(raw.max_executions);
    if (!Number.isInteger(max) || max < 1) throw new Error("حداکثر اجرا باید عدد صحیح مثبت باشد.");
    conditions.max_executions = max;
  }

  return conditions;
}

export const Route = createFileRoute("/api/keywords/conditions")({
  server: {
    handlers: {
      GET: async ({ request }) => {
        try {
          const ownerId = await requireUserId();
          const url = new URL(request.url);
          const ruleId = Number(url.searchParams.get("rule_id"));
          if (!Number.isInteger(ruleId) || ruleId <= 0) {
            return json({ ok: false, error: "rule_id معتبر نیست" }, 400);
          }
          const rule = await getKeywordRule(ownerId, ruleId);
          if (!rule) return json({ ok: false, error: "قانون پیدا نشد" }, 404);
          return json({ ok: true, rule_id: rule.id, conditions: rule.conditions });
        } catch (error) {
          if (error instanceof UnauthorizedError) return json({ ok: false, error: "unauthorized" }, 401);
          return json({ ok: false, error: error instanceof Error ? error.message : "خطای داخلی" }, 500);
        }
      },
      POST: async ({ request }) => {
        try {
          const ownerId = await requireUserId();
          const body = await request.json() as { rule_id?: number; conditions?: unknown };
          const ruleId = Number(body.rule_id);
          if (!Number.isInteger(ruleId) || ruleId <= 0) {
            return json({ ok: false, error: "rule_id معتبر نیست" }, 400);
          }
          const existing = await getKeywordRule(ownerId, ruleId);
          if (!existing) return json({ ok: false, error: "قانون پیدا نشد" }, 404);

          const conditions = normalizeConditions(body.conditions);
          const rule = await updateKeywordRuleConditions(ownerId, ruleId, conditions);
          if (!rule) return json({ ok: false, error: "ذخیره شرایط انجام نشد" }, 500);

          return json({ ok: true, rule_id: rule.id, conditions: rule.conditions });
        } catch (error) {
          if (error instanceof UnauthorizedError) return json({ ok: false, error: "unauthorized" }, 401);
          if (error instanceof SyntaxError) return json({ ok: false, error: "invalid json" }, 400);
          return json({ ok: false, error: error instanceof Error ? error.message : "خطای داخلی" }, 400);
        }
      },
    },
  },
});
