import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { ArrowUp, Bot, ChevronRight, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { faNum, faRelative, faTime } from "@/lib/format";
import { useSelfStore } from "@/lib/store";
import type { Chat, Message } from "@/lib/types";
import { Avatar } from "./kit";
import { cn } from "@/lib/utils";

function chatKind(c: Chat): string {
  if (c.type === "saved") return "ذخیره";
  if (c.type === "group") return `گروه · ${faNum(c.members ?? 0)}`;
  return "خصوصی";
}

function Bubble({ m, selfName }: { m: Message; selfName: string }) {
  const mine = m.from === "self";
  const system = m.from === "system";
  return (
    <div className={cn("flex w-full", mine ? "justify-start" : "justify-end")}>
      <div
        className={cn(
          "max-w-[85%] rounded-lg px-3 py-2 text-sm leading-relaxed",
          system
            ? "bg-surface-2 text-muted shadow-[var(--shadow-border)]"
            : mine
              ? "bg-accent text-accent-fg"
              : "bg-surface-2 text-fg shadow-[var(--shadow-border)]",
        )}
      >
        {!mine && !system ? (
          <p className="mb-1 text-[11px] font-medium text-muted">{m.senderName}</p>
        ) : null}
        {system ? (
          <p className="mb-1 text-[11px] font-medium text-subtle">
            {m.kind === "command" ? "فرمان" : m.kind === "filter" ? "فیلتر" : "سیستم"}
          </p>
        ) : null}
        <p className="whitespace-pre-wrap">{m.text}</p>
        <p className={cn("mt-1 text-[10px] tabular", mine ? "text-accent-fg/60" : "text-subtle")}>
          {faTime(m.at)}
          {m.from === "self" && m.senderName === selfName && m.kind !== "text" ? ` · ${m.kind}` : ""}
        </p>
      </div>
    </div>
  );
}

export function ChatsView() {
  const chats = useSelfStore((s) => s.chats);
  const messages = useSelfStore((s) => s.messages);
  const activeId = useSelfStore((s) => s.activeChatId);
  const setActiveChat = useSelfStore((s) => s.setActiveChat);
  const sendSelf = useSelfStore((s) => s.sendSelf);
  const injectPeer = useSelfStore((s) => s.injectPeer);
  const profile = useSelfStore((s) => s.profile)!;
  const prefix = useSelfStore((s) => s.settings.prefix);
  const snippets = useSelfStore((s) => s.snippets);
  const [q, setQ] = useState("");
  const [draft, setDraft] = useState("");
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const filtered = useMemo(() => {
    const t = q.trim();
    if (!t) return chats;
    return chats.filter((c) => c.title.includes(t) || c.preview.includes(t));
  }, [chats, q]);

  const active = chats.find((c) => c.id === activeId) ?? null;
  const thread = useMemo(
    () => (active ? messages.filter((m) => m.chatId === active.id) : []),
    [messages, active],
  );

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [thread.length, active?.id]);

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!active || !draft.trim()) return;
    sendSelf(active.id, draft);
    setDraft("");
    inputRef.current?.focus();
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col lg:flex-row lg:gap-3">
      <aside className={cn("flex w-full shrink-0 flex-col lg:w-80", active && "hidden lg:flex")}>
        <div className="mb-3">
          <p className="text-[11px] font-medium tracking-[0.16em] text-subtle uppercase">Inbox</p>
          <h1 className="font-display text-3xl italic">گفتگوها</h1>
        </div>
        <div className="relative mb-3">
          <Search className="pointer-events-none absolute end-3 top-1/2 size-4 -translate-y-1/2 text-subtle" />
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="جستجوی گفتگو"
            className="pe-9"
          />
        </div>
        <ScrollArea className="h-[min(60dvh,28rem)] lg:h-auto lg:flex-1">
          <ul className="flex flex-col gap-1 pb-4">
            {filtered.map((c) => {
              const on = active?.id === c.id;
              return (
                <li key={c.id}>
                  <button
                    type="button"
                    onClick={() => setActiveChat(c.id)}
                    className={cn(
                      "flex w-full items-center gap-3 rounded-lg px-2 py-2 text-start transition-colors duration-150",
                      on ? "bg-surface-2" : "hover:bg-surface",
                    )}
                  >
                    <Avatar name={c.title} hue={c.hue} size="sm" />
                    <span className="min-w-0 flex-1">
                      <span className="flex items-center justify-between gap-2">
                        <span className="truncate text-sm font-medium">{c.title}</span>
                        <span className="shrink-0 text-[11px] text-subtle">{faRelative(c.lastAt)}</span>
                      </span>
                      <span className="mt-0.5 flex items-center gap-2">
                        <span className="truncate text-xs text-muted">{c.preview}</span>
                        {c.unread > 0 ? (
                          <span className="ms-auto inline-flex min-w-5 items-center justify-center rounded-full bg-accent px-1.5 text-[10px] font-medium text-accent-fg tabular">
                            {faNum(c.unread)}
                          </span>
                        ) : null}
                      </span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </ScrollArea>
      </aside>

      <section className={cn("flex min-h-0 min-w-0 flex-1 flex-col rounded-xl bg-surface shadow-[var(--shadow-border)]", !active && "hidden lg:flex")}>
        {active ? (
          <>
            <header className="flex items-center gap-3 border-b border-line px-3 py-3">
              <button
                type="button"
                className="inline-flex size-11 items-center justify-center rounded-sm text-muted hover:bg-surface-2 lg:hidden"
                onClick={() => useSelfStore.setState({ activeChatId: null })}
                aria-label="بازگشت"
              >
                <ChevronRight className="size-5" />
              </button>
              <Avatar name={active.title} hue={active.hue} size="sm" />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{active.title}</p>
                <p className="text-xs text-muted">{chatKind(active)}</p>
              </div>
              {active.type !== "saved" ? (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() =>
                    injectPeer(
                      active.id,
                      "سلام، این یک پیام آزمایشی است تا پاسخ خودکار را ببینید.",
                    )
                  }
                >
                  پیام آزمایشی
                </Button>
              ) : null}
            </header>
            <ScrollArea className="min-h-0 flex-1">
              <div className="flex flex-col gap-2 px-3 py-4">
                {thread.map((m) => (
                  <Bubble key={m.id} m={m} selfName={profile.name} />
                ))}
                <div ref={endRef} />
              </div>
            </ScrollArea>
            <div className="border-t border-line p-3">
              {snippets.length > 0 ? (
                <div className="mb-2 flex flex-wrap gap-1.5">
                  {snippets.slice(0, 4).map((s) => (
                    <button
                      key={s.id}
                      type="button"
                      className="rounded-full bg-surface-2 px-2.5 py-1 text-[11px] text-muted hover:text-fg"
                      onClick={() => setDraft(`/${s.shortcut}`)}
                    >
                      /{s.shortcut}
                    </button>
                  ))}
                  <Badge tone="muted">پیشوند {prefix}</Badge>
                </div>
              ) : null}
              <form onSubmit={submit} className="flex items-end gap-2">
                <Input
                  ref={inputRef}
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  placeholder={`${prefix}راهنما یا پیام…`}
                  className="flex-1"
                />
                <Button type="submit" size="icon" aria-label="ارسال">
                  <ArrowUp className="size-4" />
                </Button>
              </form>
              <p className="mt-2 flex items-center gap-1.5 text-[11px] text-subtle">
                <Bot className="size-3.5" />
                دستورها و ماژول‌ها روی همین گفتگو اجرا می‌شوند.
              </p>
            </div>
          </>
        ) : (
          <div className="flex flex-1 items-center justify-center p-8 text-sm text-muted">
            یک گفتگو را انتخاب کنید.
          </div>
        )}
      </section>
    </div>
  );
}
