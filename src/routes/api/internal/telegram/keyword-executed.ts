import { createFileRoute } from "@tanstack/react-router";
import { markKeywordRuleExecuted } from "@/lib/keyword-engine";

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
}

function authorized(request: Request) {
  const token = process.env.WORKER_API_TOKEN?.trim();
  return Boolean(token) && request.headers.get("X-Salf1-Worker-Token") === token;
}

export const Route = createFileRoute("/api/internal/telegram/keyword-executed")({
  server: {
    handlers: {
      POST: async ({ request }) => {
        if (!authorized(request)) {
          return json({ ok: false, error: "worker authentication required" }, 401);
        }

        let body: { customer_id?: string; rule_id?: number };
        try {
          body = await request.json();
        } catch {
          return json({ ok: false, error: "invalid json" }, 400);
        }

        const customerId = String(body.customer_id ?? "").trim();
        const ruleId = Number(body.rule_id);

        if (!customerId || !Number.isInteger(ruleId) || ruleId <= 0) {
          return json({ ok: false, error: "customer_id and valid rule_id are required" }, 400);
        }

        const rule = await markKeywordRuleExecuted(customerId, ruleId);
        if (!rule) {
          return json({ ok: false, error: "rule not found" }, 404);
        }

        return json({
          ok: true,
          rule_id: rule.id,
          execution_count: rule.executionCount,
          last_executed_at: rule.lastExecutedAt,
        });
      },
    },
  },
});
