import { createFileRoute } from "@tanstack/react-router";
import { findMatchingKeywordRules } from "@/lib/keyword-engine";

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

export const Route = createFileRoute("/api/internal/telegram/events")({
  server: {
    handlers: {
      POST: async ({ request }) => {
        if (!authorized(request)) {
          return json({ ok: false, error: "worker authentication required" }, 401);
        }

        let body: {
          type?: string;
          customer_id?: string;
          message?: {
            chat_id?: number | string | null;
            sender_id?: number | string | null;
            text?: string;
            message_id?: number | string | null;
            date?: string | null;
          };
        };

        try {
          body = await request.json();
        } catch {
          return json({ ok: false, error: "invalid json" }, 400);
        }

        if (body.type !== "telegram.message") {
          return json({ ok: false, error: "unsupported event type" }, 400);
        }

        const customerId = String(body.customer_id ?? "").trim();
        const text = String(body.message?.text ?? "").trim();

        if (!customerId || !text) {
          return json(
            { ok: false, error: "customer_id and message.text are required" },
            400,
          );
        }

        const rules = await findMatchingKeywordRules(customerId, text);

        return json({
          ok: true,
          customer_id: customerId,
          message_id: body.message?.message_id ?? null,
          matches: rules.map((rule) => ({
            id: rule.id,
            name: rule.name,
            actions: rule.actions,
            delay_min: rule.delayMin,
            delay_max: rule.delayMax,
            cooldown_seconds: rule.cooldownSeconds,
            scope: rule.scope,
            conditions: rule.conditions,
          })),
        });
      },
    },
  },
});
