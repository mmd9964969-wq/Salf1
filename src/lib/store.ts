import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type {
  Activity,
  AfkState,
  AutoReplyRule,
  Chat,
  CustomCommand,
  FilterConfig,
  Message,
  Modules,
  Note,
  Profile,
  ScheduledJob,
  Settings,
  Snippet,
  Stats,
  ViewId,
} from "./types";
import { uid } from "./utils";
import { emptyStats, newSessionId, seedWorkspace } from "./seed";
import {
  applySnippet,
  DEMO_INCOMING,
  findAutoReply,
  hasBlockedWord,
  hasLink,
  parseCommand,
  runCommand,
  stampBio,
} from "./engine";
import { initials } from "./format";

export const VIEW_LABEL: Record<ViewId, string> = {
  home: "نمای کلی",
  chats: "گفتگوها",
  autoreply: "پاسخ خودکار",
  commands: "دستورها",
  schedule: "زمان‌بندی",
  notes: "یادداشت‌ها",
  filters: "فیلترها",
  snippets: "الگوها",
  profile: "پروفایل",
  activity: "گزارش",
  settings: "تنظیمات",
};

function memoryStorage(): Storage {
  const map = new Map<string, string>();
  return {
    get length() {
      return map.size;
    },
    clear: () => map.clear(),
    getItem: (key) => map.get(key) ?? null,
    key: (index) => [...map.keys()][index] ?? null,
    removeItem: (key) => {
      map.delete(key);
    },
    setItem: (key, value) => {
      map.set(key, value);
    },
  };
}

const persistStorage = createJSONStorage(() =>
  typeof window === "undefined" ? memoryStorage() : window.localStorage,
);

const defaultModules = (): Modules => ({
  autoReply: true,
  afk: true,
  commands: true,
  scheduler: true,
  filters: true,
  clockBio: false,
  autoRead: true,
  welcome: true,
  snippets: true,
});

const defaultFilters = (): FilterConfig => ({
  antiLink: false,
  antiForward: false,
  blockedWords: ["اسپم", "قمار"],
  warnMessage: "این پیام با فیلترهای گفتگو سازگار نبود و حذف شد.",
});

const defaultSettings = (): Settings => ({
  prefix: ".",
  typingDelay: true,
  liveDemo: true,
  compactChats: false,
  welcomeText: "سلام، پیام‌تان رسید. به‌زودی پاسخ می‌دهم.",
});

type SelfState = {
  hydrated: boolean;
  profile: Profile | null;
  view: ViewId;
  activeChatId: string | null;
  chats: Chat[];
  messages: Message[];
  rules: AutoReplyRule[];
  commands: CustomCommand[];
  jobs: ScheduledJob[];
  notes: Note[];
  snippets: Snippet[];
  activity: Activity[];
  modules: Modules;
  filters: FilterConfig;
  afk: AfkState;
  settings: Settings;
  stats: Stats;
  baseBio: string;
  setHydrated: () => void;
  setView: (view: ViewId) => void;
  setActiveChat: (id: string | null) => void;
  completeOnboarding: (name: string, username: string, bio: string) => void;
  patchProfile: (patch: Partial<Profile>) => void;
  setBaseBio: (bio: string) => void;
  tickClockBio: () => void;
  toggleModule: (key: keyof Modules) => void;
  setAfk: (on: boolean, reason?: string) => void;
  patchSettings: (patch: Partial<Settings>) => void;
  patchFilters: (patch: Partial<FilterConfig>) => void;
  log: (type: string, detail: string) => void;
  bumpStat: (key: Exclude<keyof Stats, "byDay">, also?: "sent" | "auto" | "commands") => void;
  sendSelf: (chatId: string, text: string) => void;
  injectPeer: (chatId: string, text: string, senderName?: string) => void;
  markRead: (chatId: string) => void;
  addRule: (rule: Omit<AutoReplyRule, "id">) => void;
  updateRule: (id: string, patch: Partial<AutoReplyRule>) => void;
  removeRule: (id: string) => void;
  addCommand: (cmd: Omit<CustomCommand, "id">) => void;
  updateCommand: (id: string, patch: Partial<CustomCommand>) => void;
  removeCommand: (id: string) => void;
  addJob: (chatId: string, text: string, at: number) => void;
  cancelJob: (id: string) => void;
  flushDueJobs: () => void;
  addNote: (title: string, body: string, tags: string[]) => void;
  updateNote: (id: string, patch: Partial<Note>) => void;
  removeNote: (id: string) => void;
  addSnippet: (shortcut: string, body: string) => void;
  removeSnippet: (id: string) => void;
  runLiveDemoTick: () => void;
  resetWorkspace: () => void;
  exportPayload: () => string;
  importPayload: (json: string) => boolean;
};

function todayIndex(byDay: Stats["byDay"]): number {
  const label = new Date().toLocaleDateString("fa-IR", { weekday: "short" });
  const i = byDay.findIndex((d) => d.day === label);
  return i === -1 ? byDay.length - 1 : i;
}

function appendMessage(list: Message[], msg: Message): Message[] {
  const next = [...list, msg];
  return next.length > 800 ? next.slice(next.length - 800) : next;
}

function touchChat(chats: Chat[], chatId: string, preview: string, unreadInc: number): Chat[] {
  const now = Date.now();
  return chats
    .map((c) =>
      c.id === chatId
        ? { ...c, preview, lastAt: now, unread: Math.max(0, c.unread + unreadInc) }
        : c,
    )
    .sort((a, b) => b.lastAt - a.lastAt);
}

const initialSlice = {
  hydrated: false,
  profile: null as Profile | null,
  view: "home" as ViewId,
  activeChatId: null as string | null,
  chats: [] as Chat[],
  messages: [] as Message[],
  rules: [] as AutoReplyRule[],
  commands: [] as CustomCommand[],
  jobs: [] as ScheduledJob[],
  notes: [] as Note[],
  snippets: [] as Snippet[],
  activity: [] as Activity[],
  modules: defaultModules(),
  filters: defaultFilters(),
  afk: { on: false, reason: "", since: null, lastReplyAt: {} } as AfkState,
  settings: defaultSettings(),
  stats: emptyStats(),
  baseBio: "",
};

export const useSelfStore = create<SelfState>()(
  persist(
    (set, get) => ({
      ...initialSlice,

      setHydrated: () => set({ hydrated: true }),
      setView: (view) => set({ view }),
      setActiveChat: (id) => {
        set({ activeChatId: id, view: "chats" });
        if (id) get().markRead(id);
      },

      completeOnboarding: (name, username, bio) => {
        const cleanName = name.trim() || "کاربر نکسا";
        const cleanUser = username.replace(/^@/, "").trim() || "nexa_user";
        const seeded = seedWorkspace(cleanName);
        const profile: Profile = {
          name: cleanName,
          username: cleanUser,
          bio: bio.trim(),
          sessionId: newSessionId(),
          connectedAt: Date.now(),
        };
        set({
          profile,
          baseBio: bio.trim(),
          chats: seeded.chats,
          messages: seeded.messages,
          rules: seeded.rules,
          commands: seeded.commands,
          notes: seeded.notes,
          snippets: seeded.snippets,
          jobs: [],
          activity: [
            {
              id: uid("act"),
              at: Date.now(),
              type: "session",
              detail: `فضای کاری «${cleanName}» متصل شد`,
            },
          ],
          stats: emptyStats(),
          view: "home",
          activeChatId: seeded.chats.find((c) => c.type === "private")?.id ?? seeded.chats[0]?.id ?? null,
          afk: { on: false, reason: "", since: null, lastReplyAt: {} },
        });
      },

      patchProfile: (patch) => {
        const profile = get().profile;
        if (!profile) return;
        const next = { ...profile, ...patch };
        if (patch.bio !== undefined) set({ profile: next, baseBio: patch.bio });
        else set({ profile: next });
      },

      setBaseBio: (bio) => {
        const profile = get().profile;
        if (!profile) return;
        set({
          baseBio: bio,
          profile: { ...profile, bio: stampBio(bio, get().modules.clockBio) },
        });
      },

      tickClockBio: () => {
        const { profile, modules, baseBio } = get();
        if (!profile || !modules.clockBio) return;
        const stamped = stampBio(baseBio, true);
        if (stamped !== profile.bio) set({ profile: { ...profile, bio: stamped } });
      },

      toggleModule: (key) => {
        const modules = { ...get().modules, [key]: !get().modules[key] };
        set({ modules });
        if (key === "clockBio") {
          const profile = get().profile;
          if (profile) {
            set({
              profile: { ...profile, bio: stampBio(get().baseBio, modules.clockBio) },
            });
          }
        }
        get().log("module", `ماژول ${key} ${modules[key] ? "روشن" : "خاموش"} شد`);
      },

      setAfk: (on, reason) => {
        set({
          afk: {
            on,
            reason: reason ?? get().afk.reason,
            since: on ? Date.now() : null,
            lastReplyAt: on ? get().afk.lastReplyAt : {},
          },
        });
        get().log("afk", on ? `افک فعال شد${reason ? `: ${reason}` : ""}` : "افک خاموش شد");
      },

      patchSettings: (patch) => set({ settings: { ...get().settings, ...patch } }),
      patchFilters: (patch) => set({ filters: { ...get().filters, ...patch } }),

      log: (type, detail) => {
        const item: Activity = { id: uid("act"), at: Date.now(), type, detail };
        const activity = [item, ...get().activity].slice(0, 200);
        set({ activity });
      },

      bumpStat: (key, also) => {
        const stats = { ...get().stats, [key]: get().stats[key] + 1 };
        const idx = todayIndex(stats.byDay);
        const byDay = stats.byDay.map((d, i) => {
          if (i !== idx) return d;
          if (also === "sent") return { ...d, sent: d.sent + 1 };
          if (also === "auto") return { ...d, auto: d.auto + 1 };
          if (also === "commands") return { ...d, commands: d.commands + 1 };
          return d;
        });
        set({ stats: { ...stats, byDay } });
      },

      markRead: (chatId) => {
        set({
          chats: get().chats.map((c) => (c.id === chatId ? { ...c, unread: 0 } : c)),
        });
      },

      sendSelf: (chatId, raw) => {
        const state = get();
        const chat = state.chats.find((c) => c.id === chatId);
        const profile = state.profile;
        if (!chat || !profile) return;

        let text = raw.trim();
        if (!text) return;
        if (state.modules.snippets) text = applySnippet(text, state.snippets);

        const selfMsg: Message = {
          id: uid("m"),
          chatId,
          from: "self",
          senderName: profile.name,
          text,
          at: Date.now(),
          kind: "text",
        };
        set({
          messages: appendMessage(get().messages, selfMsg),
          chats: touchChat(get().chats, chatId, text, 0),
        });
        get().bumpStat("sent", "sent");

        if (!state.modules.commands) return;
        const parsed = parseCommand(text, state.settings.prefix);
        if (!parsed) return;

        const result = runCommand(parsed.name, parsed.arg, {
          prefix: state.settings.prefix,
          profileName: profile.name,
          username: profile.username,
          bio: profile.bio,
          chat,
          afkOn: state.afk.on,
          afkReason: state.afk.reason,
          modules: state.modules,
          notes: state.notes,
          customs: state.commands,
          stats: state.stats,
          uptimeMs: Date.now() - profile.connectedAt,
        });
        if (!result) return;

        if (result.side === "afk-on") get().setAfk(true, result.payload ?? "");
        if (result.side === "afk-off") get().setAfk(false);
        if (result.side === "bio" && result.payload) get().setBaseBio(result.payload);
        if (result.side === "save-note" && result.payload) {
          get().addNote(result.payload.slice(0, 24), result.payload, ["دستور"]);
        }

        const reply: Message = {
          id: uid("m"),
          chatId,
          from: "system",
          senderName: "نکسا",
          text: result.reply,
          at: Date.now() + 1,
          kind: "command",
        };
        const delay = state.settings.typingDelay ? 280 : 0;
        window.setTimeout(() => {
          set({
            messages: appendMessage(get().messages, reply),
            chats: touchChat(get().chats, chatId, result.reply, 0),
          });
          get().bumpStat("commandsRun", "commands");
          get().log("command", `${state.settings.prefix}${parsed.name} در «${chat.title}»`);
        }, delay);
      },

      injectPeer: (chatId, text, senderName) => {
        const state = get();
        const chat = state.chats.find((c) => c.id === chatId);
        const profile = state.profile;
        if (!chat || !profile || chat.type === "saved") return;
        const body = text.trim();
        if (!body) return;
        const fromName = senderName || chat.peerName || chat.title;

        if (state.modules.filters) {
          const blocked = hasBlockedWord(body, state.filters.blockedWords);
          const linkHit = state.filters.antiLink && hasLink(body);
          if (blocked || linkHit) {
            const why = blocked ? `واژه «${blocked}»` : "لینک";
            const warn: Message = {
              id: uid("m"),
              chatId,
              from: "system",
              senderName: "فیلتر",
              text: `${state.filters.warnMessage} (${why})`,
              at: Date.now(),
              kind: "filter",
            };
            set({
              messages: appendMessage(get().messages, warn),
              chats: touchChat(get().chats, chatId, warn.text, 0),
            });
            get().bumpStat("filtered");
            get().log("filter", `پیام در «${chat.title}» به‌خاطر ${why} حذف شد`);
            return;
          }
        }

        const incoming: Message = {
          id: uid("m"),
          chatId,
          from: "peer",
          senderName: fromName,
          text: body,
          at: Date.now(),
          kind: "text",
        };
        const isOpen = get().activeChatId === chatId && get().view === "chats";
        const unreadInc = state.modules.autoRead || isOpen ? 0 : 1;
        set({
          messages: appendMessage(get().messages, incoming),
          chats: touchChat(get().chats, chatId, body, unreadInc),
        });
        get().bumpStat("received");

        const replyLater = (kind: Message["kind"], textOut: string, type: string) => {
          const delay = state.settings.typingDelay ? 500 + Math.floor(Math.random() * 400) : 120;
          window.setTimeout(() => {
            const out: Message = {
              id: uid("m"),
              chatId,
              from: "self",
              senderName: profile.name,
              text: textOut,
              at: Date.now(),
              kind,
            };
            set({
              messages: appendMessage(get().messages, out),
              chats: touchChat(get().chats, chatId, textOut, 0),
            });
            if (kind === "auto-reply" || kind === "afk" || kind === "welcome") {
              get().bumpStat("autoReplies", "auto");
              get().bumpStat("sent", "sent");
            }
            get().log(type, `پاسخ ${type} در «${chat.title}»`);
          }, delay);
        };

        const peerCount = get().messages.filter((m) => m.chatId === chatId && m.from === "peer").length;
        if (state.modules.welcome && chat.type === "private" && peerCount <= 1) {
          replyLater("welcome", state.settings.welcomeText, "welcome");
          return;
        }

        if (state.modules.afk && state.afk.on && chat.type === "private") {
          const last = state.afk.lastReplyAt[chatId] ?? 0;
          if (Date.now() - last > 3 * 60_000) {
            set({
              afk: {
                ...get().afk,
                lastReplyAt: { ...get().afk.lastReplyAt, [chatId]: Date.now() },
              },
            });
            const reason = state.afk.reason ? `\n${state.afk.reason}` : "";
            replyLater("afk", `الان در دسترس نیستم.${reason}`, "afk");
            return;
          }
        }

        if (state.modules.autoReply) {
          const rule = findAutoReply(body, chat, get().rules);
          if (rule) {
            window.setTimeout(() => replyLater("auto-reply", rule.reply, "auto"), rule.delayMs);
          }
        }
      },

      addRule: (rule) => set({ rules: [{ ...rule, id: uid("rule") }, ...get().rules] }),
      updateRule: (id, patch) =>
        set({ rules: get().rules.map((r) => (r.id === id ? { ...r, ...patch } : r)) }),
      removeRule: (id) => set({ rules: get().rules.filter((r) => r.id !== id) }),

      addCommand: (cmd) => set({ commands: [{ ...cmd, id: uid("cmd") }, ...get().commands] }),
      updateCommand: (id, patch) =>
        set({ commands: get().commands.map((c) => (c.id === id ? { ...c, ...patch } : c)) }),
      removeCommand: (id) => set({ commands: get().commands.filter((c) => c.id !== id) }),

      addJob: (chatId, text, at) => {
        const job: ScheduledJob = { id: uid("job"), chatId, text, at, status: "pending" };
        set({ jobs: [job, ...get().jobs] });
        get().log("schedule", "پیام زمان‌بندی شد");
      },
      cancelJob: (id) =>
        set({
          jobs: get().jobs.map((j) => (j.id === id ? { ...j, status: "cancelled" as const } : j)),
        }),

      flushDueJobs: () => {
        const { jobs, modules, profile } = get();
        if (!modules.scheduler || !profile) return;
        const now = Date.now();
        for (const job of jobs) {
          if (job.status !== "pending" || job.at > now) continue;
          const chat = get().chats.find((c) => c.id === job.chatId);
          const msg: Message = {
            id: uid("m"),
            chatId: job.chatId,
            from: "self",
            senderName: profile.name,
            text: job.text,
            at: now,
            kind: "scheduled",
          };
          set({
            messages: appendMessage(get().messages, msg),
            chats: touchChat(get().chats, job.chatId, job.text, 0),
            jobs: get().jobs.map((j) => (j.id === job.id ? { ...j, status: "sent" as const } : j)),
          });
          get().bumpStat("scheduledSent");
          get().bumpStat("sent", "sent");
          get().log("schedule", `ارسال زمان‌دار به «${chat?.title ?? "گفتگو"}»`);
        }
      },

      addNote: (title, body, tags) => {
        const note: Note = {
          id: uid("note"),
          title: title.trim() || "بدون عنوان",
          body,
          tags,
          pinned: false,
          createdAt: Date.now(),
        };
        set({ notes: [note, ...get().notes] });
      },
      updateNote: (id, patch) =>
        set({ notes: get().notes.map((n) => (n.id === id ? { ...n, ...patch } : n)) }),
      removeNote: (id) => set({ notes: get().notes.filter((n) => n.id !== id) }),

      addSnippet: (shortcut, body) =>
        set({
          snippets: [{ id: uid("snip"), shortcut: shortcut.replace(/^\//, ""), body }, ...get().snippets],
        }),
      removeSnippet: (id) => set({ snippets: get().snippets.filter((s) => s.id !== id) }),

      runLiveDemoTick: () => {
        const { settings, chats, profile } = get();
        if (!settings.liveDemo || !profile) return;
        const pool = chats.filter((c) => c.type !== "saved");
        if (pool.length === 0) return;
        const pick = DEMO_INCOMING[Math.floor(Math.random() * DEMO_INCOMING.length)]!;
        const chat =
          pool.find((c) => c.title.includes(pick.chatTitleHint)) ??
          pool[Math.floor(Math.random() * pool.length)]!;
        get().injectPeer(chat.id, pick.text);
      },

      resetWorkspace: () => {
        set({ ...initialSlice, hydrated: true, stats: emptyStats(), modules: defaultModules() });
      },

      exportPayload: () => {
        const s = get();
        return JSON.stringify(
          {
            profile: s.profile,
            baseBio: s.baseBio,
            rules: s.rules,
            commands: s.commands,
            notes: s.notes,
            snippets: s.snippets,
            modules: s.modules,
            filters: s.filters,
            settings: s.settings,
          },
          null,
          2,
        );
      },

      importPayload: (json) => {
        try {
          const data = JSON.parse(json) as Partial<SelfState>;
          if (!data || typeof data !== "object") return false;
          set({
            rules: data.rules ?? get().rules,
            commands: data.commands ?? get().commands,
            notes: data.notes ?? get().notes,
            snippets: data.snippets ?? get().snippets,
            modules: data.modules ?? get().modules,
            filters: data.filters ?? get().filters,
            settings: { ...get().settings, ...(data.settings ?? {}) },
            baseBio: typeof data.baseBio === "string" ? data.baseBio : get().baseBio,
          });
          get().log("settings", "پشتیبان تنظیمات وارد شد");
          return true;
        } catch {
          return false;
        }
      },
    }),
    {
      name: "nexa-self-v1",
      storage: persistStorage,
      skipHydration: true,
      partialize: (s) => ({
        profile: s.profile,
        view: s.view,
        activeChatId: s.activeChatId,
        chats: s.chats,
        messages: s.messages,
        rules: s.rules,
        commands: s.commands,
        jobs: s.jobs,
        notes: s.notes,
        snippets: s.snippets,
        activity: s.activity,
        modules: s.modules,
        filters: s.filters,
        afk: s.afk,
        settings: s.settings,
        stats: s.stats,
        baseBio: s.baseBio,
      }),
    },
  ),
);

export function avatarTone(hue: number): string {
  return `oklch(0.72 0.08 ${hue})`;
}

export function displayInitials(name: string): string {
  return initials(name);
}
