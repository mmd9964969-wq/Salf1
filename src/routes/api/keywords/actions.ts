import { createFileRoute } from "@tanstack/react-router";
import {
  getKeywordRule,
  updateKeywordRuleActions,
  type KeywordAction,\n  validateKeywordActionPolicy,
} from "@/lib/keyword-engine";
import { requireUserId, UnauthorizedError } from "@/lib/auth/verify.server";

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
}

function normalizeActions(input: unknown): KeywordAction[] {
  if (!Array.isArray(input)) throw new Error("اقدامات نامعتبر هستند.");
  return input.map((item) => {
    if (!item || typeof item !== "object") throw new Error("ساختار اقدام نامعتبر است.");
    const value = item as Record<string, unknown>;
    const type = String(value.type ?? "");
    if (!["reply","notify","log","react","delete","forward"].includes(type)) {
      throw new Error("نوع اقدام نامعتبر است.");
    }
    const text = value.text == null ? undefined : String(value.text).trim();
    if (["reply","notify","react","forward"].includes(type) && !text) throw new Error("این اقدام به مقدار متنی/شناسه نیاز دارد.");
    const delayMin = Math.max(0, Math.floor(Number(value.delayMin ?? value.delay_min ?? 0) || 0));\n    const delayMax = Math.max(delayMin, Math.floor(Number(value.delayMax ?? value.delay_max ?? delayMin) || 0));\n    if (delayMin > 3600 || delayMax > 3600) throw new Error("تأخیر هر اقدام نمی‌تواند بیشتر از ۳۶۰۰ ثانیه باشد.");\n    const action = { type, ...(text ? { text } : {}), delayMin, delayMax } as KeywordAction;\n    const policy = validateKeywordActionPolicy(action);\n    if (!policy.allowed) throw new Error(policy.reason);\n    return action;
  });
}

export const Route = createFileRoute("/api/keywords/actions")({
  server: {
    handlers: {
      GET: async ({ request }) => {
        try {
          const ownerId = await requireUserId();
          const id = Number(new URL(request.url).searchParams.get("rule_id"));
          if (!Number.isInteger(id) || id <= 0) return json({ ok: false, error: "rule_id معتبر نیست" }, 400);
          const rule = await getKeywordRule(ownerId, id);
          if (!rule) return json({ ok: false, error: "قانون پیدا نشد" }, 404);
          return json({ ok: true, rule_id: id, actions: rule.actions });
        } catch (error) {
          if (error instanceof UnauthorizedError) return json({ ok: false, error: "unauthorized" }, 401);
          return json({ ok: false, error: "خطای داخلی" }, 500);
        }
      },
      POST: async ({ request }) => {
        try {
          const ownerId = await requireUserId();
          const body = await request.json() as { rule_id?: number; actions?: unknown };
          const id = Number(body.rule_id);
          if (!Number.isInteger(id) || id <= 0) return json({ ok: false, error: "rule_id معتبر نیست" }, 400);
          if (!(await getKeywordRule(ownerId, id))) return json({ ok: false, error: "قانون پیدا نشد" }, 404);
          const actions = normalizeActions(body.actions);
          const rule = await updateKeywordRuleActions(ownerId, id, actions);
          if (!rule) return json({ ok: false, error: "ذخیره اقدامات انجام نشد" }, 500);
          return json({ ok: true, rule_id: id, actions: rule.actions });
        } catch (error) {
          if (error instanceof UnauthorizedError) return json({ ok: false, error: "unauthorized" }, 401);
          if (error instanceof SyntaxError) return json({ ok: false, error: "invalid json" }, 400);
          return json({ ok: false, error: error instanceof Error ? error.message : "خطای داخلی" }, 400);
        }
      },
    },
  },
});
