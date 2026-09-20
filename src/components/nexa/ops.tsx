import { useMemo, useState } from "react";
import { Pin, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/dialog";
import { faDateTime, faNum } from "@/lib/format";
import { useSelfStore } from "@/lib/store";
import type { MatchMode } from "@/lib/types";
import { EmptyState, FieldStack, PageTitle, Surface } from "./kit";

const MATCH_LABEL: Record<MatchMode, string> = {
  contains: "شامل",
  exact: "دقیق",
  starts: "شروع",
};

export function AutoReplyView() {
  const rules = useSelfStore((s) => s.rules);
  const addRule = useSelfStore((s) => s.addRule);
  const updateRule = useSelfStore((s) => s.updateRule);
  const removeRule = useSelfStore((s) => s.removeRule);
  const enabled = useSelfStore((s) => s.modules.autoReply);
  const toggle = useSelfStore((s) => s.toggleModule);
  const [open, setOpen] = useState(false);
  const [trigger, setTrigger] = useState("");
  const [reply, setReply] = useState("");
  const [match, setMatch] = useState<MatchMode>("contains");
  const [scope, setScope] = useState<"all" | "private" | "group">("all");

  function save() {
    if (!trigger.trim() || !reply.trim()) return;
    addRule({ enabled: true, trigger: trigger.trim(), reply: reply.trim(), match, scope, delayMs: 600 });
    setTrigger("");
    setReply("");
    setOpen(false);
    toast("قانون جدید ذخیره شد");
  }

  return (
    <div className="nexa-rise">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <PageTitle
          kicker="Auto"
          title="پاسخ خودکار"
          hint="اگر پیام ورودی با قانون جور شود، پنل به‌جای شما جواب می‌دهد."
        />
        <div className="mb-6 flex items-center gap-3">
          <span className="text-xs text-muted">ماژول</span>
          <Switch checked={enabled} onCheckedChange={() => toggle("autoReply")} />
        </div>
      </div>
      <div className="mb-4 flex justify-end">
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="size-4" />
              قانون تازه
            </Button>
          </DialogTrigger>
          <DialogContent title="قانون پاسخ">
            <div className="flex flex-col gap-3">
              <FieldStack>
                <Label>کلیدواژه</Label>
                <Input value={trigger} onChange={(e) => setTrigger(e.target.value)} placeholder="سلام" />
              </FieldStack>
              <FieldStack>
                <Label>پاسخ</Label>
                <Textarea value={reply} onChange={(e) => setReply(e.target.value)} rows={3} />
              </FieldStack>
              <div className="grid grid-cols-2 gap-2">
                <FieldStack>
                  <Label>نوع تطبیق</Label>
                  <select
                    className="h-11 rounded-md bg-surface-2 px-3 text-sm shadow-[var(--shadow-border)]"
                    value={match}
                    onChange={(e) => setMatch(e.target.value as MatchMode)}
                  >
                    <option value="contains">شامل</option>
                    <option value="starts">شروع متن</option>
                    <option value="exact">دقیق</option>
                  </select>
                </FieldStack>
                <FieldStack>
                  <Label>محدوده</Label>
                  <select
                    className="h-11 rounded-md bg-surface-2 px-3 text-sm shadow-[var(--shadow-border)]"
                    value={scope}
                    onChange={(e) => setScope(e.target.value as "all" | "private" | "group")}
                  >
                    <option value="all">همه</option>
                    <option value="private">فقط پیوی</option>
                    <option value="group">فقط گروه</option>
                  </select>
                </FieldStack>
              </div>
              <Button onClick={save}>ذخیره</Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>
      {rules.length === 0 ? (
        <Surface>
          <EmptyState title="قانونی نیست" desc="یک کلیدواژه و پاسخ اضافه کنید، بعد در گفتگو پیام آزمایشی بفرستید." />
        </Surface>
      ) : (
        <ul className="flex flex-col gap-2">
          {rules.map((r) => (
            <li key={r.id}>
              <Surface className="flex flex-col gap-3 sm:flex-row sm:items-center">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-medium">{r.trigger}</p>
                    <Badge>{MATCH_LABEL[r.match]}</Badge>
                    <Badge tone="muted">{r.scope === "all" ? "همه" : r.scope === "private" ? "پیوی" : "گروه"}</Badge>
                  </div>
                  <p className="mt-1 text-sm text-muted">{r.reply}</p>
                </div>
                <div className="flex items-center gap-2">
                  <Switch checked={r.enabled} onCheckedChange={(v) => updateRule(r.id, { enabled: v })} />
                  <Button variant="ghost" size="iconSm" onClick={() => removeRule(r.id)} aria-label="حذف">
                    <Trash2 className="size-4" />
                  </Button>
                </div>
              </Surface>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function CommandsView() {
  const commands = useSelfStore((s) => s.commands);
  const addCommand = useSelfStore((s) => s.addCommand);
  const updateCommand = useSelfStore((s) => s.updateCommand);
  const removeCommand = useSelfStore((s) => s.removeCommand);
  const prefix = useSelfStore((s) => s.settings.prefix);
  const enabled = useSelfStore((s) => s.modules.commands);
  const toggle = useSelfStore((s) => s.toggleModule);
  const [name, setName] = useState("");
  const [response, setResponse] = useState("");
  const [description, setDescription] = useState("");

  function save() {
    if (!name.trim() || !response.trim()) return;
    addCommand({
      enabled: true,
      name: name.trim().replace(/^\./, ""),
      response: response.trim(),
      description: description.trim(),
    });
    setName("");
    setResponse("");
    setDescription("");
    toast("دستور اضافه شد");
  }

  return (
    <div className="nexa-rise">
      <PageTitle
        kicker="Commands"
        title="دستورها"
        hint={`در هر گفتگو ${prefix}راهنما را بزنید. دستورهای داخلی همیشه آماده‌اند.`}
      />
      <div className="mb-4 flex items-center justify-between rounded-lg bg-surface px-4 py-3 shadow-[var(--shadow-border)]">
        <p className="text-sm">اجرای فرمان با پیشوند</p>
        <Switch checked={enabled} onCheckedChange={() => toggle("commands")} />
      </div>
      <div className="grid gap-3 lg:grid-cols-[1fr_1fr]">
        <Surface>
          <h2 className="text-sm font-medium">دستور تازه</h2>
          <div className="mt-4 flex flex-col gap-3">
            <FieldStack>
              <Label>نام فرمان</Label>
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="قوانین" />
            </FieldStack>
            <FieldStack>
              <Label>توضیح کوتاه</Label>
              <Input value={description} onChange={(e) => setDescription(e.target.value)} />
            </FieldStack>
            <FieldStack>
              <Label>پاسخ</Label>
              <Textarea value={response} onChange={(e) => setResponse(e.target.value)} rows={4} />
            </FieldStack>
            <Button onClick={save}>افزودن</Button>
          </div>
        </Surface>
        <Surface className="p-2">
          <h2 className="px-3 pt-2 text-sm font-medium">داخلی و سفارشی</h2>
          <ul className="mt-2 divide-y divide-line">
            {["راهنما", "پینگ", "ساعت", "آیدی", "وضعیت", "افک", "برگشت", "بیو", "save", "نوت", "حساب"].map((n) => (
              <li key={n} className="flex items-center justify-between px-3 py-2.5 text-sm">
                <span className="font-mono text-xs" dir="ltr">
                  {prefix}
                  {n}
                </span>
                <Badge tone="muted">داخلی</Badge>
              </li>
            ))}
            {commands.map((c) => (
              <li key={c.id} className="flex items-center gap-2 px-3 py-2.5">
                <span className="min-w-0 flex-1">
                  <span className="font-mono text-xs" dir="ltr">
                    {prefix}
                    {c.name}
                  </span>
                  <p className="truncate text-xs text-muted">{c.description || c.response}</p>
                </span>
                <Switch checked={c.enabled} onCheckedChange={(v) => updateCommand(c.id, { enabled: v })} />
                <Button variant="ghost" size="iconSm" onClick={() => removeCommand(c.id)} aria-label="حذف">
                  <Trash2 className="size-4" />
                </Button>
              </li>
            ))}
          </ul>
        </Surface>
      </div>
    </div>
  );
}

export function ScheduleView() {
  const jobs = useSelfStore((s) => s.jobs);
  const chats = useSelfStore((s) => s.chats);
  const addJob = useSelfStore((s) => s.addJob);
  const cancelJob = useSelfStore((s) => s.cancelJob);
  const [chatId, setChatId] = useState(chats[0]?.id ?? "");
  const [text, setText] = useState("");
  const [when, setWhen] = useState("");

  function save() {
    if (!chatId || !text.trim() || !when) return;
    const at = new Date(when).getTime();
    if (Number.isNaN(at) || at < Date.now() - 1000) {
      toast("زمان معتبر در آینده انتخاب کنید");
      return;
    }
    addJob(chatId, text.trim(), at);
    setText("");
    toast("زمان‌بندی ثبت شد");
  }

  return (
    <div className="nexa-rise">
      <PageTitle kicker="Schedule" title="زمان‌بندی" hint="پیام در ساعت مشخص به گفتگوی انتخابی ارسال می‌شود." />
      <div className="grid gap-3 lg:grid-cols-[1fr_1.1fr]">
        <Surface>
          <div className="flex flex-col gap-3">
            <FieldStack>
              <Label>گفتگو</Label>
              <select
                className="h-11 rounded-md bg-surface-2 px-3 text-sm shadow-[var(--shadow-border)]"
                value={chatId}
                onChange={(e) => setChatId(e.target.value)}
              >
                {chats.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.title}
                  </option>
                ))}
              </select>
            </FieldStack>
            <FieldStack>
              <Label>زمان</Label>
              <Input type="datetime-local" value={when} onChange={(e) => setWhen(e.target.value)} dir="ltr" />
            </FieldStack>
            <FieldStack>
              <Label>متن</Label>
              <Textarea value={text} onChange={(e) => setText(e.target.value)} rows={4} />
            </FieldStack>
            <Button onClick={save}>ثبت ارسال</Button>
          </div>
        </Surface>
        <div className="flex flex-col gap-2">
          {jobs.length === 0 ? (
            <Surface>
              <EmptyState title="صف خالی است" desc="یک پیام و زمان انتخاب کنید." />
            </Surface>
          ) : (
            jobs.map((j) => {
              const chat = chats.find((c) => c.id === j.chatId);
              const tone = j.status === "sent" ? "ok" : j.status === "cancelled" ? "danger" : "warn";
              const label = j.status === "sent" ? "ارسال شد" : j.status === "cancelled" ? "لغو" : "در صف";
              return (
                <Surface key={j.id} className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm font-medium">{chat?.title ?? "گفتگو"}</p>
                    <p className="mt-1 text-sm text-muted">{j.text}</p>
                    <p className="mt-2 text-xs text-subtle">{faDateTime(j.at)}</p>
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    <Badge tone={tone}>{label}</Badge>
                    {j.status === "pending" ? (
                      <Button variant="ghost" size="sm" onClick={() => cancelJob(j.id)}>
                        لغو
                      </Button>
                    ) : null}
                  </div>
                </Surface>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}

export function NotesView() {
  const notes = useSelfStore((s) => s.notes);
  const addNote = useSelfStore((s) => s.addNote);
  const updateNote = useSelfStore((s) => s.updateNote);
  const removeNote = useSelfStore((s) => s.removeNote);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [tags, setTags] = useState("");
  const [q, setQ] = useState("");

  const shown = useMemo(() => {
    const t = q.trim();
    const list = [...notes].sort((a, b) => Number(b.pinned) - Number(a.pinned) || b.createdAt - a.createdAt);
    if (!t) return list;
    return list.filter((n) => n.title.includes(t) || n.body.includes(t) || n.tags.some((x) => x.includes(t)));
  }, [notes, q]);

  function save() {
    if (!title.trim() && !body.trim()) return;
    addNote(title, body, tags.split(/[،,]/).map((x) => x.trim()).filter(Boolean));
    setTitle("");
    setBody("");
    setTags("");
  }

  return (
    <div className="nexa-rise">
      <PageTitle kicker="Notes" title="یادداشت‌ها" hint="با .save در چت هم می‌توانید سریع ذخیره کنید. با .نوت عنوان را بخوانید." />
      <div className="grid gap-3 lg:grid-cols-[0.9fr_1.1fr]">
        <Surface>
          <div className="flex flex-col gap-3">
            <FieldStack>
              <Label>عنوان</Label>
              <Input value={title} onChange={(e) => setTitle(e.target.value)} />
            </FieldStack>
            <FieldStack>
              <Label>متن</Label>
              <Textarea value={body} onChange={(e) => setBody(e.target.value)} rows={5} />
            </FieldStack>
            <FieldStack>
              <Label>برچسب‌ها</Label>
              <Input value={tags} onChange={(e) => setTags(e.target.value)} placeholder="کار، پاسخ" />
            </FieldStack>
            <Button onClick={save}>ذخیره یادداشت</Button>
          </div>
        </Surface>
        <div>
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="جستجو" className="mb-3" />
          <ul className="flex flex-col gap-2">
            {shown.map((n) => (
              <li key={n.id}>
                <Surface>
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="font-medium">{n.title}</p>
                      <p className="mt-1 whitespace-pre-wrap text-sm text-muted">{n.body}</p>
                      <div className="mt-2 flex flex-wrap gap-1">
                        {n.tags.map((t) => (
                          <Badge key={t}>{t}</Badge>
                        ))}
                      </div>
                    </div>
                    <div className="flex gap-1">
                      <Button
                        variant="ghost"
                        size="iconSm"
                        onClick={() => updateNote(n.id, { pinned: !n.pinned })}
                        aria-label="پین"
                      >
                        <Pin className={n.pinned ? "size-4 text-ok" : "size-4"} />
                      </Button>
                      <Button variant="ghost" size="iconSm" onClick={() => removeNote(n.id)} aria-label="حذف">
                        <Trash2 className="size-4" />
                      </Button>
                    </div>
                  </div>
                </Surface>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

export function FiltersView() {
  const filters = useSelfStore((s) => s.filters);
  const patch = useSelfStore((s) => s.patchFilters);
  const enabled = useSelfStore((s) => s.modules.filters);
  const toggle = useSelfStore((s) => s.toggleModule);
  const stats = useSelfStore((s) => s.stats);
  const [word, setWord] = useState("");

  return (
    <div className="nexa-rise">
      <PageTitle
        kicker="Filters"
        title="فیلترها"
        hint="برای گفتگوهای خودتان: لینک و واژه‌های مشخص در پیام ورودی حذف آزمایشی می‌شوند."
      />
      <div className="mb-4 flex items-center justify-between rounded-lg bg-surface px-4 py-3 shadow-[var(--shadow-border)]">
        <p className="text-sm">موتور فیلتر</p>
        <Switch checked={enabled} onCheckedChange={() => toggle("filters")} />
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        <Surface className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium">ضد لینک</p>
            <p className="text-xs text-muted">پیام دارای آدرس وب</p>
          </div>
          <Switch checked={filters.antiLink} onCheckedChange={(v) => patch({ antiLink: v })} />
        </Surface>
        <Surface>
          <p className="text-sm font-medium">حذف‌شده‌ها</p>
          <p className="mt-2 font-display text-3xl italic tabular">{faNum(stats.filtered)}</p>
        </Surface>
      </div>
      <Surface className="mt-3">
        <FieldStack>
          <Label>متن هشدار</Label>
          <Textarea value={filters.warnMessage} onChange={(e) => patch({ warnMessage: e.target.value })} rows={2} />
        </FieldStack>
        <div className="mt-4">
          <Label>واژه‌های مسدود</Label>
          <div className="mt-2 flex gap-2">
            <Input value={word} onChange={(e) => setWord(e.target.value)} placeholder="افزودن واژه" />
            <Button
              variant="secondary"
              onClick={() => {
                const w = word.trim();
                if (!w) return;
                patch({ blockedWords: [...filters.blockedWords, w] });
                setWord("");
              }}
            >
              افزودن
            </Button>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {filters.blockedWords.map((w) => (
              <button
                key={w}
                type="button"
                className="rounded-full bg-surface-2 px-3 py-1 text-xs text-muted hover:text-danger"
                onClick={() => patch({ blockedWords: filters.blockedWords.filter((x) => x !== w) })}
              >
                {w} ×
              </button>
            ))}
          </div>
        </div>
      </Surface>
    </div>
  );
}

export function SnippetsView() {
  const snippets = useSelfStore((s) => s.snippets);
  const addSnippet = useSelfStore((s) => s.addSnippet);
  const removeSnippet = useSelfStore((s) => s.removeSnippet);
  const enabled = useSelfStore((s) => s.modules.snippets);
  const toggle = useSelfStore((s) => s.toggleModule);
  const [shortcut, setShortcut] = useState("");
  const [body, setBody] = useState("");

  return (
    <div className="nexa-rise">
      <PageTitle kicker="Snippets" title="الگوها" hint="در ورودی گفتگو /میانبر را بفرستید تا متن کامل جایگزین شود." />
      <div className="mb-4 flex items-center justify-between rounded-lg bg-surface px-4 py-3 shadow-[var(--shadow-border)]">
        <p className="text-sm">جایگزینی الگو</p>
        <Switch checked={enabled} onCheckedChange={() => toggle("snippets")} />
      </div>
      <div className="grid gap-3 lg:grid-cols-2">
        <Surface>
          <div className="flex flex-col gap-3">
            <FieldStack>
              <Label>میانبر</Label>
              <Input value={shortcut} onChange={(e) => setShortcut(e.target.value)} placeholder="درود" />
            </FieldStack>
            <FieldStack>
              <Label>متن کامل</Label>
              <Textarea value={body} onChange={(e) => setBody(e.target.value)} rows={4} />
            </FieldStack>
            <Button
              onClick={() => {
                if (!shortcut.trim() || !body.trim()) return;
                addSnippet(shortcut, body);
                setShortcut("");
                setBody("");
              }}
            >
              افزودن الگو
            </Button>
          </div>
        </Surface>
        <ul className="flex flex-col gap-2">
          {snippets.map((s) => (
            <li key={s.id}>
              <Surface className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-mono text-xs text-muted" dir="ltr">
                    /{s.shortcut}
                  </p>
                  <p className="mt-1 text-sm">{s.body}</p>
                </div>
                <Button variant="ghost" size="iconSm" onClick={() => removeSnippet(s.id)} aria-label="حذف">
                  <Trash2 className="size-4" />
                </Button>
              </Surface>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
