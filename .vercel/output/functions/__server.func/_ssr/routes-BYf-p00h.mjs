import { i as __toESM } from "../_runtime.mjs";
import { n as require_react } from "../_libs/@radix-ui/react-compose-refs+[...].mjs";
import { n as require_jsx_runtime } from "../_libs/radix-ui__react-context+react.mjs";
import { C as Activity, S as ArrowUp, _ as Funnel, a as Timer, b as ChevronRight, c as Settings, d as Pin, f as NotebookPen, g as House, h as Menu, i as Trash2, l as Search, m as MessageSquare, n as UserRound, o as Sparkles, p as Moon, s as Shield, t as X, u as Plus, v as Command, x as Bot, y as Clock3 } from "../_libs/lucide-react.mjs";
import { a as DialogPortal, i as DialogOverlay, n as DialogClose, o as DialogTitle, p as Slot, r as DialogContent$1, s as DialogTrigger$1, t as Dialog$1 } from "../_libs/@radix-ui/react-dialog+[...].mjs";
import { n as toast, t as Toaster } from "../_libs/sonner.mjs";
import { t as Provider } from "../_libs/radix-ui__react-tooltip.mjs";
import { n as clsx, t as cva } from "../_libs/class-variance-authority+clsx.mjs";
import { t as twMerge } from "../_libs/tailwind-merge.mjs";
import { n as persist, r as create, t as createJSONStorage } from "../_libs/zustand.mjs";
import { n as SwitchThumb, t as Switch$1 } from "../_libs/radix-ui__react-switch.mjs";
import { a as CartesianGrid, i as Area, n as YAxis, o as ResponsiveContainer, r as XAxis, s as Tooltip, t as AreaChart } from "../_libs/recharts+[...].mjs";
import { i as Viewport, n as Scrollbar, r as Thumb, t as Root } from "../_libs/radix-ui__react-scroll-area.mjs";
//#region node_modules/.nitro/vite/services/ssr/assets/routes-BYf-p00h.js
var import_react = /* @__PURE__ */ __toESM(require_react());
var import_jsx_runtime = require_jsx_runtime();
function cn(...inputs) {
	return twMerge(clsx(inputs));
}
function uid(prefix = "id") {
	return `${prefix}_${Math.random().toString(36).slice(2, 10)}${Date.now().toString(36).slice(-4)}`;
}
function TooltipProvider({ children }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Provider, {
		delayDuration: 250,
		skipDelayDuration: 80,
		children
	});
}
function ago(minutes) {
	return Date.now() - minutes * 6e4;
}
function newSessionId() {
	return `nexa_${Math.random().toString(36).slice(2, 8)}${Date.now().toString(36).slice(-5)}`;
}
function emptyStats() {
	return {
		sent: 0,
		received: 0,
		autoReplies: 0,
		commandsRun: 0,
		filtered: 0,
		scheduledSent: 0,
		byDay: Array.from({ length: 7 }, (_, i) => {
			const d = /* @__PURE__ */ new Date();
			d.setDate(d.getDate() - (6 - i));
			return {
				day: d.toLocaleDateString("fa-IR", { weekday: "short" }),
				sent: 0,
				auto: 0,
				commands: 0
			};
		})
	};
}
function seedWorkspace(ownerName) {
	const savedId = uid("chat");
	const saraId = uid("chat");
	const productId = uid("chat");
	const kianId = uid("chat");
	const supportId = uid("chat");
	const contentId = uid("chat");
	return {
		chats: [
			{
				id: savedId,
				title: "پیام‌های ذخیره",
				type: "saved",
				preview: "آرشیو شخصی دستورها و یادداشت‌ها",
				lastAt: ago(4),
				unread: 0,
				muted: true,
				hue: 200,
				about: "چت خصوصی با خودتان."
			},
			{
				id: saraId,
				title: "سارا نوری",
				type: "private",
				preview: "فایل نهایی را شب می‌فرستم",
				lastAt: ago(12),
				unread: 1,
				muted: false,
				username: "saranouri",
				hue: 28,
				peerName: "سارا نوری",
				about: "طراح محصول · تهران"
			},
			{
				id: productId,
				title: "گروه محصول",
				type: "group",
				preview: "نسخه بعدی پنل را جمعه می‌بندیم",
				lastAt: ago(38),
				unread: 3,
				muted: false,
				members: 14,
				hue: 160,
				peerName: "نگار",
				about: "هماهنگی محصول و انتشار."
			},
			{
				id: kianId,
				title: "کیان رضایی",
				type: "private",
				preview: "سلام، فردا جلسه‌ات ساعت چند است؟",
				lastAt: ago(95),
				unread: 0,
				muted: false,
				username: "kianrz",
				hue: 250,
				peerName: "کیان رضایی",
				about: "مدیر عملیات"
			},
			{
				id: supportId,
				title: "راهنمای نکسا",
				type: "private",
				preview: "برای دیدن دستورها در هر چت بنویس .راهنما",
				lastAt: ago(6),
				unread: 0,
				muted: false,
				hue: 190,
				peerName: "نکسا",
				about: "راهنمای داخلی پنل."
			},
			{
				id: contentId,
				title: "تیم محتوا",
				type: "group",
				preview: "کپشن امشب آماده است",
				lastAt: ago(220),
				unread: 0,
				muted: false,
				members: 8,
				hue: 40,
				peerName: "هستی",
				about: "تقویم محتوا و انتشار."
			}
		],
		messages: [
			{
				id: uid("m"),
				chatId: savedId,
				from: "system",
				senderName: "نکسا",
				text: "این چت آرشیو شخصی شماست. با دستور .save متن را اینجا نگه دارید.",
				at: ago(180),
				kind: "text"
			},
			{
				id: uid("m"),
				chatId: saraId,
				from: "peer",
				senderName: "سارا نوری",
				text: "سلام، موکاپ صفحه پروفایل را دیدی؟",
				at: ago(80),
				kind: "text"
			},
			{
				id: uid("m"),
				chatId: saraId,
				from: "self",
				senderName: ownerName,
				text: "دیدم. فاصله‌ها بهتر شده. فقط تیتر را کمی کوچک‌تر کنیم.",
				at: ago(70),
				kind: "text"
			},
			{
				id: uid("m"),
				chatId: saraId,
				from: "peer",
				senderName: "سارا نوری",
				text: "باشه. فایل نهایی را شب می‌فرستم",
				at: ago(12),
				kind: "text"
			},
			{
				id: uid("m"),
				chatId: productId,
				from: "peer",
				senderName: "نگار",
				text: "چک‌لیست انتشار را در نوت‌ها گذاشتم.",
				at: ago(120),
				kind: "text"
			},
			{
				id: uid("m"),
				chatId: productId,
				from: "peer",
				senderName: "امیر",
				text: "ساعت در بیو را هم برای نسخه بعدی فعال کنیم.",
				at: ago(90),
				kind: "text"
			},
			{
				id: uid("m"),
				chatId: productId,
				from: "peer",
				senderName: "نگار",
				text: "نسخه بعدی پنل را جمعه می‌بندیم",
				at: ago(38),
				kind: "text"
			},
			{
				id: uid("m"),
				chatId: kianId,
				from: "peer",
				senderName: "کیان رضایی",
				text: "سلام، فردا جلسه‌ات ساعت چند است؟",
				at: ago(95),
				kind: "text"
			},
			{
				id: uid("m"),
				chatId: supportId,
				from: "peer",
				senderName: "نکسا",
				text: `سلام ${ownerName}. فضای کاری آماده است.`,
				at: ago(20),
				kind: "welcome"
			},
			{
				id: uid("m"),
				chatId: supportId,
				from: "peer",
				senderName: "نکسا",
				text: "در هر گفتگو پیشوند . را بزن: .راهنما  ·  .پینگ  ·  .ساعت  ·  .افک",
				at: ago(18),
				kind: "text"
			},
			{
				id: uid("m"),
				chatId: supportId,
				from: "peer",
				senderName: "نکسا",
				text: "برای دیدن دستورها در هر چت بنویس .راهنما",
				at: ago(6),
				kind: "text"
			},
			{
				id: uid("m"),
				chatId: contentId,
				from: "peer",
				senderName: "هستی",
				text: "کپشن امشب آماده است",
				at: ago(220),
				kind: "text"
			}
		],
		rules: [
			{
				id: uid("rule"),
				enabled: true,
				trigger: "سلام",
				match: "starts",
				reply: "سلام، پیام‌تان رسید. کمی بعد جواب می‌دهم.",
				delayMs: 600,
				scope: "private"
			},
			{
				id: uid("rule"),
				enabled: true,
				trigger: "قیمت",
				match: "contains",
				reply: "برای قیمت از مسیر پروفایل → یادداشت «تعرفه» استفاده کنید یا بعداً هماهنگ می‌کنیم.",
				delayMs: 800,
				scope: "all"
			},
			{
				id: uid("rule"),
				enabled: false,
				trigger: "فوری",
				match: "contains",
				reply: "پیام فوری‌تان دیده شد. در اولین فرصت برمی‌گردم.",
				delayMs: 400,
				scope: "all"
			}
		],
		commands: [{
			id: uid("cmd"),
			enabled: true,
			name: "قوانین",
			response: "۱. احترام ۲. بدون لینک تبلیغ ۳. بحث‌ها در تاپیک مربوط.",
			description: "قوانین گروه را می‌فرستد"
		}, {
			id: uid("cmd"),
			enabled: true,
			name: "لینک",
			response: "لینک دعوت این فضا فقط از تنظیمات گروه قابل کپی است.",
			description: "پاسخ آماده برای درخواست لینک"
		}],
		notes: [{
			id: uid("note"),
			title: "تعرفه",
			body: "مشاوره ساعتی: توافقی · پروژه طراحی: پس از بریف.",
			tags: ["کار", "پاسخ"],
			pinned: true,
			createdAt: ago(400)
		}, {
			id: uid("note"),
			title: "چک‌لیست انتشار",
			body: "کپی · اسکرین موبایل · پشتیبان تنظیمات · خاموش کردن دمو زنده.",
			tags: ["محصول"],
			pinned: false,
			createdAt: ago(130)
		}],
		snippets: [{
			id: uid("snip"),
			shortcut: "درود",
			body: "درود، پیام‌تان را خواندم. تا ساعاتی دیگر پاسخ دقیق می‌دهم."
		}, {
			id: uid("snip"),
			shortcut: "جلسه",
			body: "برای جلسه یک بازه ۳۰ دقیقه‌ای فردا بعدازظهر مناسب است. شما چه ساعتی راحتید؟"
		}],
		savedId
	};
}
var FA_DIGITS = "۰۱۲۳۴۵۶۷۸۹";
function faNum(value) {
	return String(value).replace(/\d/g, (d) => FA_DIGITS[Number(d)] ?? d);
}
function faTime(ts) {
	return new Date(ts).toLocaleTimeString("fa-IR", {
		hour: "2-digit",
		minute: "2-digit"
	});
}
function faDate(ts) {
	return new Date(ts).toLocaleDateString("fa-IR", {
		month: "short",
		day: "numeric"
	});
}
function faDateTime(ts) {
	return new Date(ts).toLocaleString("fa-IR", {
		month: "short",
		day: "numeric",
		hour: "2-digit",
		minute: "2-digit"
	});
}
function faRelative(ts, now = Date.now()) {
	const diff = Math.max(0, now - ts);
	const min = Math.floor(diff / 6e4);
	if (min < 1) return "همین الان";
	if (min < 60) return `${faNum(min)} دقیقه پیش`;
	const hr = Math.floor(min / 60);
	if (hr < 24) return `${faNum(hr)} ساعت پیش`;
	const day = Math.floor(hr / 24);
	if (day < 7) return `${faNum(day)} روز پیش`;
	return faDate(ts);
}
function initials(name) {
	const parts = name.trim().split(/\s+/).filter(Boolean);
	if (parts.length === 0) return "ن";
	if (parts.length === 1) return parts[0].slice(0, 2);
	return `${parts[0].slice(0, 1)}${parts[1].slice(0, 1)}`;
}
function formatDuration(ms) {
	const total = Math.max(0, Math.floor(ms / 1e3));
	const h = Math.floor(total / 3600);
	const m = Math.floor(total % 3600 / 60);
	if (h > 0) return `${faNum(h)} ساعت و ${faNum(m)} دقیقه`;
	return `${faNum(m)} دقیقه`;
}
var LINK_RE = /(https?:\/\/|t\.me\/|www\.)/i;
function matchesTrigger(text, trigger, mode) {
	const hay = text.trim().toLowerCase();
	const needle = trigger.trim().toLowerCase();
	if (!needle) return false;
	if (mode === "exact") return hay === needle;
	if (mode === "starts") return hay.startsWith(needle);
	return hay.includes(needle);
}
function findAutoReply(text, chat, rules) {
	for (const rule of rules) {
		if (!rule.enabled) continue;
		if (rule.scope === "private" && chat.type !== "private") continue;
		if (rule.scope === "group" && chat.type !== "group") continue;
		if (matchesTrigger(text, rule.trigger, rule.match)) return rule;
	}
	return null;
}
function hasBlockedWord(text, words) {
	const hay = text.toLowerCase();
	for (const w of words) {
		const t = w.trim().toLowerCase();
		if (t && hay.includes(t)) return w.trim();
	}
	return null;
}
function hasLink(text) {
	return LINK_RE.test(text);
}
function parseCommand(text, prefix) {
	const t = text.trim();
	if (!prefix || !t.startsWith(prefix)) return null;
	const rest = t.slice(prefix.length).trim();
	if (!rest) return null;
	const sp = rest.indexOf(" ");
	if (sp === -1) return {
		name: rest.toLowerCase(),
		arg: ""
	};
	return {
		name: rest.slice(0, sp).toLowerCase(),
		arg: rest.slice(sp + 1).trim()
	};
}
function safeCalc(expr) {
	const cleaned = expr.replace(/[×x]/gi, "*").replace(/÷/g, "/").replace(/\s+/g, "");
	if (!cleaned || !/^[-+]?\d+(\.\d+)?([+\-*/][-+]?\d+(\.\d+)?)*$/.test(cleaned)) return "فقط اعداد و چهار عمل اصلی.";
	try {
		const tokens = cleaned.match(/[+\-*/]|[-+]?\d+(\.\d+)?/g);
		if (!tokens || tokens.length < 1) return "عبارت نامعتبر.";
		let acc = Number(tokens[0]);
		for (let i = 1; i < tokens.length; i += 2) {
			const op = tokens[i];
			const n = Number(tokens[i + 1]);
			if (!op || Number.isNaN(n) || Number.isNaN(acc)) return "عبارت نامعتبر.";
			if (op === "+") acc += n;
			else if (op === "-") acc -= n;
			else if (op === "*") acc *= n;
			else if (op === "/") {
				if (n === 0) return "تقسیم بر صفر ممکن نیست.";
				acc /= n;
			}
		}
		return `= ${faNum(Number.isInteger(acc) ? String(acc) : acc.toFixed(4).replace(/0+$/, "").replace(/\.$/, ""))}`;
	} catch {
		return "عبارت نامعتبر.";
	}
}
var HELP_LINES = [
	"دستورهای داخلی:",
	".راهنما — همین فهرست",
	".پینگ — وضعیت پنل",
	".ساعت — زمان فعلی",
	".آیدی — شناسه این گفتگو",
	".وضعیت — خلاصه ماژول‌ها",
	".افک [متن] — روشن کردن حالت دور",
	".برگشت — خاموش کردن افک",
	".بیو [متن] — تغییر بیو",
	".save [متن] — ذخیره یادداشت",
	".نوت [عنوان] — خواندن یادداشت",
	".حساب ۱۲+۵ — ماشین‌حساب"
];
function runCommand(rawName, arg, ctx) {
	const name = {
		help: "راهنما",
		ping: "پینگ",
		time: "ساعت",
		id: "آیدی",
		status: "وضعیت",
		afk: "افک",
		unafk: "برگشت",
		back: "برگشت",
		bio: "بیو",
		save: "save",
		note: "نوت",
		calc: "حساب",
		حساب: "حساب"
	}[rawName] ?? rawName;
	if (name === "راهنما") {
		const extra = ctx.customs.filter((c) => c.enabled).map((c) => `${ctx.prefix}${c.name} — ${c.description || "سفارشی"}`);
		return { reply: [...HELP_LINES, ...extra.length ? [
			"",
			"سفارشی:",
			...extra
		] : []].join("\n") };
	}
	if (name === "پینگ") return { reply: `آنلاین · تأخیر ${faNum(12 + Date.now() % 17)}ms · ${ctx.profileName}` };
	if (name === "ساعت") return { reply: faDateTime(Date.now()) };
	if (name === "آیدی") {
		const kind = ctx.chat.type === "group" ? "گروه" : ctx.chat.type === "saved" ? "ذخیره" : "خصوصی";
		return { reply: `${ctx.chat.title}\nنوع: ${kind}\nشناسه: ${ctx.chat.id}\nشما: @${ctx.username}` };
	}
	if (name === "وضعیت") {
		const on = (v) => v ? "روشن" : "خاموش";
		const mins = Math.floor(ctx.uptimeMs / 6e4);
		return { reply: [
			`پاسخ خودکار: ${on(ctx.modules.autoReply)}`,
			`افک: ${ctx.afkOn ? `روشن — ${ctx.afkReason || "بدون توضیح"}` : "خاموش"}`,
			`دستورها: ${on(ctx.modules.commands)}`,
			`فیلتر: ${on(ctx.modules.filters)}`,
			`ساعت در بیو: ${on(ctx.modules.clockBio)}`,
			`آمار: ${faNum(ctx.stats.sent)} ارسال · ${faNum(ctx.stats.autoReplies)} پاسخ · ${faNum(ctx.stats.commandsRun)} دستور`,
			`آپ‌تایم: ${faNum(mins)} دقیقه`
		].join("\n") };
	}
	if (name === "افک") return {
		reply: `حالت دور فعال شد.${arg ? `\n${arg}` : ""}`,
		side: "afk-on",
		payload: arg
	};
	if (name === "برگشت") return {
		reply: "برگشتم؛ افک خاموش شد.",
		side: "afk-off"
	};
	if (name === "بیو") {
		if (!arg) return { reply: ctx.bio || "بیو خالی است." };
		return {
			reply: "بیو به‌روز شد.",
			side: "bio",
			payload: arg
		};
	}
	if (name === "save") {
		if (!arg) return { reply: "متن یادداشت را بعد از دستور بنویسید." };
		return {
			reply: "ذخیره شد.",
			side: "save-note",
			payload: arg
		};
	}
	if (name === "نوت") {
		if (!arg) {
			const list = ctx.notes.slice(0, 8).map((n) => `• ${n.title}`);
			return { reply: list.length ? `یادداشت‌ها:\n${list.join("\n")}` : "یادداشتی نیست." };
		}
		const found = ctx.notes.find((n) => n.title.includes(arg) || n.tags.some((t) => t.includes(arg)));
		return { reply: found ? `${found.title}\n${found.body}` : "پیدا نشد." };
	}
	if (name === "حساب") {
		if (!arg) return { reply: "مثال: .حساب 12+8*3" };
		return { reply: safeCalc(arg) };
	}
	const custom = ctx.customs.find((c) => c.enabled && c.name.toLowerCase() === rawName);
	if (custom) return { reply: custom.response };
	return { reply: `دستور «${rawName}» شناخته نشد. ${ctx.prefix}راهنما` };
}
function applySnippet(text, snippets) {
	const t = text.trim();
	const hit = snippets.find((s) => s.shortcut && t === `/${s.shortcut}`);
	return hit ? hit.body : text;
}
function stampBio(base, enabled, now = Date.now()) {
	if (!enabled) return base.replace(/\n?ساعت:.*$/u, "").trim();
	const clock = new Date(now).toLocaleTimeString("fa-IR", {
		hour: "2-digit",
		minute: "2-digit"
	});
	return `${base.replace(/\n?ساعت:.*$/u, "").trim()}\nساعت: ${clock}`.trim();
}
var DEMO_INCOMING = [
	{
		chatTitleHint: "سارا",
		text: "سلام، نسخه جدید را دیدی؟"
	},
	{
		chatTitleHint: "کیان",
		text: "سلام، فایل جلسه را فرستادی؟"
	},
	{
		chatTitleHint: "محصول",
		text: "یک لینک تست: https://example.com"
	},
	{
		chatTitleHint: "محتوا",
		text: "کپشن فردا نیاز به ویرایش دارد"
	},
	{
		chatTitleHint: "کیان",
		text: "قیمت این پلن چقدر است؟"
	}
];
var VIEW_LABEL = {
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
	settings: "تنظیمات"
};
var defaultModules = () => ({
	autoReply: true,
	afk: true,
	commands: true,
	scheduler: true,
	filters: true,
	clockBio: false,
	autoRead: true,
	welcome: true,
	snippets: true
});
var defaultFilters = () => ({
	antiLink: false,
	antiForward: false,
	blockedWords: ["اسپم", "قمار"],
	warnMessage: "این پیام با فیلترهای گفتگو سازگار نبود و حذف شد."
});
var defaultSettings = () => ({
	prefix: ".",
	typingDelay: true,
	liveDemo: true,
	compactChats: false,
	welcomeText: "سلام، پیام‌تان رسید. به‌زودی پاسخ می‌دهم."
});
function todayIndex(byDay) {
	const label = (/* @__PURE__ */ new Date()).toLocaleDateString("fa-IR", { weekday: "short" });
	const i = byDay.findIndex((d) => d.day === label);
	return i === -1 ? byDay.length - 1 : i;
}
function appendMessage(list, msg) {
	const next = [...list, msg];
	return next.length > 800 ? next.slice(next.length - 800) : next;
}
function touchChat(chats, chatId, preview, unreadInc) {
	const now = Date.now();
	return chats.map((c) => c.id === chatId ? {
		...c,
		preview,
		lastAt: now,
		unread: Math.max(0, c.unread + unreadInc)
	} : c).sort((a, b) => b.lastAt - a.lastAt);
}
var initialSlice = {
	hydrated: false,
	profile: null,
	view: "home",
	activeChatId: null,
	chats: [],
	messages: [],
	rules: [],
	commands: [],
	jobs: [],
	notes: [],
	snippets: [],
	activity: [],
	modules: defaultModules(),
	filters: defaultFilters(),
	afk: {
		on: false,
		reason: "",
		since: null,
		lastReplyAt: {}
	},
	settings: defaultSettings(),
	stats: emptyStats(),
	baseBio: ""
};
var useSelfStore = create()(persist((set, get) => ({
	...initialSlice,
	setHydrated: () => set({ hydrated: true }),
	setView: (view) => set({ view }),
	setActiveChat: (id) => {
		set({
			activeChatId: id,
			view: "chats"
		});
		if (id) get().markRead(id);
	},
	completeOnboarding: (name, username, bio) => {
		const cleanName = name.trim() || "کاربر نکسا";
		const cleanUser = username.replace(/^@/, "").trim() || "nexa_user";
		const seeded = seedWorkspace(cleanName);
		set({
			profile: {
				name: cleanName,
				username: cleanUser,
				bio: bio.trim(),
				sessionId: newSessionId(),
				connectedAt: Date.now()
			},
			baseBio: bio.trim(),
			chats: seeded.chats,
			messages: seeded.messages,
			rules: seeded.rules,
			commands: seeded.commands,
			notes: seeded.notes,
			snippets: seeded.snippets,
			jobs: [],
			activity: [{
				id: uid("act"),
				at: Date.now(),
				type: "session",
				detail: `فضای کاری «${cleanName}» متصل شد`
			}],
			stats: emptyStats(),
			view: "home",
			activeChatId: seeded.chats.find((c) => c.type === "private")?.id ?? seeded.chats[0]?.id ?? null,
			afk: {
				on: false,
				reason: "",
				since: null,
				lastReplyAt: {}
			}
		});
	},
	patchProfile: (patch) => {
		const profile = get().profile;
		if (!profile) return;
		const next = {
			...profile,
			...patch
		};
		if (patch.bio !== void 0) set({
			profile: next,
			baseBio: patch.bio
		});
		else set({ profile: next });
	},
	setBaseBio: (bio) => {
		const profile = get().profile;
		if (!profile) return;
		set({
			baseBio: bio,
			profile: {
				...profile,
				bio: stampBio(bio, get().modules.clockBio)
			}
		});
	},
	tickClockBio: () => {
		const { profile, modules, baseBio } = get();
		if (!profile || !modules.clockBio) return;
		const stamped = stampBio(baseBio, true);
		if (stamped !== profile.bio) set({ profile: {
			...profile,
			bio: stamped
		} });
	},
	toggleModule: (key) => {
		const modules = {
			...get().modules,
			[key]: !get().modules[key]
		};
		set({ modules });
		if (key === "clockBio") {
			const profile = get().profile;
			if (profile) set({ profile: {
				...profile,
				bio: stampBio(get().baseBio, modules.clockBio)
			} });
		}
		get().log("module", `ماژول ${key} ${modules[key] ? "روشن" : "خاموش"} شد`);
	},
	setAfk: (on, reason) => {
		set({ afk: {
			on,
			reason: reason ?? get().afk.reason,
			since: on ? Date.now() : null,
			lastReplyAt: on ? get().afk.lastReplyAt : {}
		} });
		get().log("afk", on ? `افک فعال شد${reason ? `: ${reason}` : ""}` : "افک خاموش شد");
	},
	patchSettings: (patch) => set({ settings: {
		...get().settings,
		...patch
	} }),
	patchFilters: (patch) => set({ filters: {
		...get().filters,
		...patch
	} }),
	log: (type, detail) => {
		set({ activity: [{
			id: uid("act"),
			at: Date.now(),
			type,
			detail
		}, ...get().activity].slice(0, 200) });
	},
	bumpStat: (key, also) => {
		const stats = {
			...get().stats,
			[key]: get().stats[key] + 1
		};
		const idx = todayIndex(stats.byDay);
		const byDay = stats.byDay.map((d, i) => {
			if (i !== idx) return d;
			if (also === "sent") return {
				...d,
				sent: d.sent + 1
			};
			if (also === "auto") return {
				...d,
				auto: d.auto + 1
			};
			if (also === "commands") return {
				...d,
				commands: d.commands + 1
			};
			return d;
		});
		set({ stats: {
			...stats,
			byDay
		} });
	},
	markRead: (chatId) => {
		set({ chats: get().chats.map((c) => c.id === chatId ? {
			...c,
			unread: 0
		} : c) });
	},
	sendSelf: (chatId, raw) => {
		const state = get();
		const chat = state.chats.find((c) => c.id === chatId);
		const profile = state.profile;
		if (!chat || !profile) return;
		let text = raw.trim();
		if (!text) return;
		if (state.modules.snippets) text = applySnippet(text, state.snippets);
		const selfMsg = {
			id: uid("m"),
			chatId,
			from: "self",
			senderName: profile.name,
			text,
			at: Date.now(),
			kind: "text"
		};
		set({
			messages: appendMessage(get().messages, selfMsg),
			chats: touchChat(get().chats, chatId, text, 0)
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
			uptimeMs: Date.now() - profile.connectedAt
		});
		if (!result) return;
		if (result.side === "afk-on") get().setAfk(true, result.payload ?? "");
		if (result.side === "afk-off") get().setAfk(false);
		if (result.side === "bio" && result.payload) get().setBaseBio(result.payload);
		if (result.side === "save-note" && result.payload) get().addNote(result.payload.slice(0, 24), result.payload, ["دستور"]);
		const reply = {
			id: uid("m"),
			chatId,
			from: "system",
			senderName: "نکسا",
			text: result.reply,
			at: Date.now() + 1,
			kind: "command"
		};
		const delay = state.settings.typingDelay ? 280 : 0;
		window.setTimeout(() => {
			set({
				messages: appendMessage(get().messages, reply),
				chats: touchChat(get().chats, chatId, result.reply, 0)
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
				const warn = {
					id: uid("m"),
					chatId,
					from: "system",
					senderName: "فیلتر",
					text: `${state.filters.warnMessage} (${why})`,
					at: Date.now(),
					kind: "filter"
				};
				set({
					messages: appendMessage(get().messages, warn),
					chats: touchChat(get().chats, chatId, warn.text, 0)
				});
				get().bumpStat("filtered");
				get().log("filter", `پیام در «${chat.title}» به‌خاطر ${why} حذف شد`);
				return;
			}
		}
		const incoming = {
			id: uid("m"),
			chatId,
			from: "peer",
			senderName: fromName,
			text: body,
			at: Date.now(),
			kind: "text"
		};
		const isOpen = get().activeChatId === chatId && get().view === "chats";
		const unreadInc = state.modules.autoRead || isOpen ? 0 : 1;
		set({
			messages: appendMessage(get().messages, incoming),
			chats: touchChat(get().chats, chatId, body, unreadInc)
		});
		get().bumpStat("received");
		const replyLater = (kind, textOut, type) => {
			const delay = state.settings.typingDelay ? 500 + Math.floor(Math.random() * 400) : 120;
			window.setTimeout(() => {
				const out = {
					id: uid("m"),
					chatId,
					from: "self",
					senderName: profile.name,
					text: textOut,
					at: Date.now(),
					kind
				};
				set({
					messages: appendMessage(get().messages, out),
					chats: touchChat(get().chats, chatId, textOut, 0)
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
			if (Date.now() - last > 18e4) {
				set({ afk: {
					...get().afk,
					lastReplyAt: {
						...get().afk.lastReplyAt,
						[chatId]: Date.now()
					}
				} });
				replyLater("afk", `الان در دسترس نیستم.${state.afk.reason ? `\n${state.afk.reason}` : ""}`, "afk");
				return;
			}
		}
		if (state.modules.autoReply) {
			const rule = findAutoReply(body, chat, get().rules);
			if (rule) window.setTimeout(() => replyLater("auto-reply", rule.reply, "auto"), rule.delayMs);
		}
	},
	addRule: (rule) => set({ rules: [{
		...rule,
		id: uid("rule")
	}, ...get().rules] }),
	updateRule: (id, patch) => set({ rules: get().rules.map((r) => r.id === id ? {
		...r,
		...patch
	} : r) }),
	removeRule: (id) => set({ rules: get().rules.filter((r) => r.id !== id) }),
	addCommand: (cmd) => set({ commands: [{
		...cmd,
		id: uid("cmd")
	}, ...get().commands] }),
	updateCommand: (id, patch) => set({ commands: get().commands.map((c) => c.id === id ? {
		...c,
		...patch
	} : c) }),
	removeCommand: (id) => set({ commands: get().commands.filter((c) => c.id !== id) }),
	addJob: (chatId, text, at) => {
		set({ jobs: [{
			id: uid("job"),
			chatId,
			text,
			at,
			status: "pending"
		}, ...get().jobs] });
		get().log("schedule", "پیام زمان‌بندی شد");
	},
	cancelJob: (id) => set({ jobs: get().jobs.map((j) => j.id === id ? {
		...j,
		status: "cancelled"
	} : j) }),
	flushDueJobs: () => {
		const { jobs, modules, profile } = get();
		if (!modules.scheduler || !profile) return;
		const now = Date.now();
		for (const job of jobs) {
			if (job.status !== "pending" || job.at > now) continue;
			const chat = get().chats.find((c) => c.id === job.chatId);
			const msg = {
				id: uid("m"),
				chatId: job.chatId,
				from: "self",
				senderName: profile.name,
				text: job.text,
				at: now,
				kind: "scheduled"
			};
			set({
				messages: appendMessage(get().messages, msg),
				chats: touchChat(get().chats, job.chatId, job.text, 0),
				jobs: get().jobs.map((j) => j.id === job.id ? {
					...j,
					status: "sent"
				} : j)
			});
			get().bumpStat("scheduledSent");
			get().bumpStat("sent", "sent");
			get().log("schedule", `ارسال زمان‌دار به «${chat?.title ?? "گفتگو"}»`);
		}
	},
	addNote: (title, body, tags) => {
		set({ notes: [{
			id: uid("note"),
			title: title.trim() || "بدون عنوان",
			body,
			tags,
			pinned: false,
			createdAt: Date.now()
		}, ...get().notes] });
	},
	updateNote: (id, patch) => set({ notes: get().notes.map((n) => n.id === id ? {
		...n,
		...patch
	} : n) }),
	removeNote: (id) => set({ notes: get().notes.filter((n) => n.id !== id) }),
	addSnippet: (shortcut, body) => set({ snippets: [{
		id: uid("snip"),
		shortcut: shortcut.replace(/^\//, ""),
		body
	}, ...get().snippets] }),
	removeSnippet: (id) => set({ snippets: get().snippets.filter((s) => s.id !== id) }),
	runLiveDemoTick: () => {
		const { settings, chats, profile } = get();
		if (!settings.liveDemo || !profile) return;
		const pool = chats.filter((c) => c.type !== "saved");
		if (pool.length === 0) return;
		const pick = DEMO_INCOMING[Math.floor(Math.random() * DEMO_INCOMING.length)];
		const chat = pool.find((c) => c.title.includes(pick.chatTitleHint)) ?? pool[Math.floor(Math.random() * pool.length)];
		get().injectPeer(chat.id, pick.text);
	},
	resetWorkspace: () => {
		set({
			...initialSlice,
			hydrated: true,
			stats: emptyStats(),
			modules: defaultModules()
		});
	},
	exportPayload: () => {
		const s = get();
		return JSON.stringify({
			profile: s.profile,
			baseBio: s.baseBio,
			rules: s.rules,
			commands: s.commands,
			notes: s.notes,
			snippets: s.snippets,
			modules: s.modules,
			filters: s.filters,
			settings: s.settings
		}, null, 2);
	},
	importPayload: (json) => {
		try {
			const data = JSON.parse(json);
			if (!data || typeof data !== "object") return false;
			set({
				rules: data.rules ?? get().rules,
				commands: data.commands ?? get().commands,
				notes: data.notes ?? get().notes,
				snippets: data.snippets ?? get().snippets,
				modules: data.modules ?? get().modules,
				filters: data.filters ?? get().filters,
				settings: {
					...get().settings,
					...data.settings ?? {}
				},
				baseBio: typeof data.baseBio === "string" ? data.baseBio : get().baseBio
			});
			get().log("settings", "پشتیبان تنظیمات وارد شد");
			return true;
		} catch {
			return false;
		}
	}
}), {
	name: "nexa-self-v1",
	storage: createJSONStorage(() => localStorage),
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
		baseBio: s.baseBio
	})
}));
function avatarTone(hue) {
	return `oklch(0.72 0.08 ${hue})`;
}
function displayInitials(name) {
	return initials(name);
}
var buttonVariants = cva("inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-[transform,background-color,opacity,box-shadow,color] duration-150 ease-[var(--ease-out)] disabled:pointer-events-none disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring [&_svg]:size-4 [&_svg]:shrink-0 active:not-disabled:scale-[0.96]", {
	variants: {
		variant: {
			default: "bg-accent text-accent-fg hover:opacity-90",
			secondary: "bg-surface-2 text-fg shadow-[var(--shadow-border)] hover:shadow-[var(--shadow-border-hover)]",
			ghost: "text-muted hover:bg-surface-2 hover:text-fg",
			danger: "bg-danger/15 text-danger hover:bg-danger/25",
			outline: "text-fg shadow-[var(--shadow-border)] hover:bg-surface-2"
		},
		size: {
			default: "h-11 min-h-11 px-4",
			sm: "h-9 min-h-9 px-3 text-xs rounded-sm",
			icon: "size-11 min-h-11",
			iconSm: "size-9 min-h-9 rounded-sm"
		}
	},
	defaultVariants: {
		variant: "default",
		size: "default"
	}
});
var Button = import_react.forwardRef(({ className, variant, size, asChild = false, ...props }, ref) => {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(asChild ? Slot : "button", {
		className: cn(buttonVariants({
			variant,
			size,
			className
		})),
		ref,
		...props
	});
});
Button.displayName = "Button";
var Input = import_react.forwardRef(({ className, type, ...props }, ref) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
	type,
	className: cn("flex h-11 w-full rounded-md bg-surface-2 px-3 text-sm text-fg shadow-[var(--shadow-border)] placeholder:text-subtle outline-none transition-[box-shadow] duration-150 focus-visible:shadow-[var(--shadow-border-hover)] focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50", className),
	ref,
	...props
}));
Input.displayName = "Input";
var Textarea = import_react.forwardRef(({ className, ...props }, ref) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
	className: cn("flex min-h-24 w-full rounded-md bg-surface-2 px-3 py-2.5 text-sm text-fg shadow-[var(--shadow-border)] placeholder:text-subtle outline-none transition-[box-shadow] duration-150 focus-visible:shadow-[var(--shadow-border-hover)] focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 resize-y", className),
	ref,
	...props
}));
Textarea.displayName = "Textarea";
function Label({ className, ...props }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
		className: cn("text-xs font-medium text-muted leading-none", className),
		...props
	});
}
var Switch = import_react.forwardRef(({ className, ...props }, ref) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch$1, {
	ref,
	dir: "ltr",
	className: cn("peer inline-flex h-6 w-10 shrink-0 cursor-pointer items-center rounded-full shadow-[var(--shadow-border)] transition-colors duration-150 data-[state=checked]:bg-accent data-[state=unchecked]:bg-surface-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-40", className),
	...props,
	children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SwitchThumb, { className: "pointer-events-none block size-5 rounded-full bg-fg transition-transform duration-150 data-[state=checked]:translate-x-[18px] data-[state=unchecked]:translate-x-0.5 data-[state=checked]:bg-accent-fg" })
}));
Switch.displayName = "Switch";
function Surface({ className, children }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: cn("rounded-lg bg-surface p-4 shadow-[var(--shadow-border)]", className),
		children
	});
}
function Eyebrow({ children }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
		className: "text-[11px] font-medium tracking-[0.16em] text-subtle uppercase",
		children
	});
}
function PageTitle({ kicker, title, hint }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("header", {
		className: "mb-6 flex flex-col gap-1",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Eyebrow, { children: kicker }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h1", {
				className: "font-display text-3xl font-medium tracking-tight text-fg italic",
				children: title
			}),
			hint ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "mt-1 max-w-xl text-sm text-muted",
				children: hint
			}) : null
		]
	});
}
function Avatar({ name, hue, size = "md" }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
		className: cn("inline-flex shrink-0 items-center justify-center rounded-full font-medium text-accent-fg", size === "lg" ? "size-14 text-lg" : size === "sm" ? "size-9 text-xs" : "size-11 text-sm"),
		style: { background: avatarTone(hue) },
		children: displayInitials(name)
	});
}
function EmptyState({ title, desc }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "px-4 py-12 text-center",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "text-sm font-medium text-fg",
			children: title
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "mt-1 text-sm text-muted",
			children: desc
		})]
	});
}
function Stat({ label, value, hint }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "rounded-lg bg-surface p-4 shadow-[var(--shadow-border)]",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-xs text-muted",
				children: label
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "mt-2 font-display text-3xl italic tabular tracking-tight",
				children: value
			}),
			hint ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "mt-1 text-xs text-subtle",
				children: hint
			}) : null
		]
	});
}
function FieldStack({ children }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "flex flex-col gap-2",
		children
	});
}
function Onboarding() {
	const complete = useSelfStore((s) => s.completeOnboarding);
	const [name, setName] = (0, import_react.useState)("");
	const [username, setUsername] = (0, import_react.useState)("");
	const [bio, setBio] = (0, import_react.useState)("");
	function submit(e) {
		e.preventDefault();
		complete(name, username, bio);
	}
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "relative min-h-dvh overflow-hidden bg-bg text-fg",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			"aria-hidden": true,
			className: "pointer-events-none absolute inset-x-0 top-0 h-72 bg-[linear-gradient(180deg,rgb(255_255_255/0.04),transparent)]"
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "mx-auto flex min-h-dvh w-full max-w-lg flex-col justify-center px-5 py-12",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "text-[11px] font-medium tracking-[0.22em] text-subtle",
					children: "SELF COMMAND"
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h1", {
					className: "mt-3 font-display text-5xl italic tracking-tight",
					children: "Nexa"
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "mt-3 max-w-sm text-sm leading-relaxed text-muted",
					children: "مرکز فرمان اکانت شما. پاسخ خودکار، دستورها، زمان‌بندی و گزارش — همه در یک فضای کاری محلی."
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("form", {
					onSubmit: submit,
					className: "mt-10 rounded-xl bg-surface p-5 shadow-[var(--shadow-border)]",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "rounded-lg bg-surface",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "text-sm font-medium",
								children: "فعال‌سازی فضای کاری"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "mt-1 text-xs text-muted",
								children: "هویت نمایشی پنل را مشخص کنید. نشست فقط روی همین دستگاه ذخیره می‌شود."
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "mt-5 flex flex-col gap-4",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(FieldStack, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, {
										htmlFor: "name",
										children: "نام نمایشی"
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
										id: "name",
										value: name,
										onChange: (e) => setName(e.target.value),
										placeholder: "مثلاً آرمین کاویانی",
										autoComplete: "nickname",
										required: true
									})] }),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(FieldStack, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, {
										htmlFor: "user",
										children: "نام کاربری"
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
										id: "user",
										value: username,
										onChange: (e) => setUsername(e.target.value),
										placeholder: "armin",
										autoComplete: "username",
										dir: "ltr",
										className: "text-start"
									})] }),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(FieldStack, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, {
										htmlFor: "bio",
										children: "بیو"
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Textarea, {
										id: "bio",
										value: bio,
										onChange: (e) => setBio(e.target.value),
										placeholder: "طراح محصول · پاسخ‌ها از پنل نکسا",
										rows: 3
									})] }),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
										type: "submit",
										className: "mt-1 w-full",
										children: "اتصال و ورود به پنل"
									})
								]
							})
						]
					})
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "mt-6 text-xs leading-relaxed text-subtle",
					children: "نکسا به تلگرام یا شبکهٔ واقعی وصل نمی‌شود؛ یک اتاق فرمان کامل است تا ماژول‌های سلف را همین‌جا بسازید، تست کنید و تنظیمات را نگه دارید."
				})
			]
		})]
	});
}
var Sheet = Dialog$1;
var SheetClose = DialogClose;
function SheetContent({ className, children, side = "right" }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogPortal, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogOverlay, { className: "fixed inset-0 z-50 bg-bg/70 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=open]:fade-in-0 data-[state=closed]:fade-out-0" }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogContent$1, {
		className: cn("fixed inset-y-0 z-50 flex w-72 max-w-[88vw] flex-col bg-surface shadow-[var(--shadow-float),var(--shadow-border)] outline-none data-[state=open]:animate-in data-[state=closed]:animate-out", side === "right" ? "end-0 data-[state=open]:slide-in-from-right data-[state=closed]:slide-out-to-right" : "start-0 data-[state=open]:slide-in-from-left data-[state=closed]:slide-out-to-left", className),
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogTitle, {
			className: "sr-only",
			children: "منو"
		}), children]
	})] });
}
function Badge({ className, tone = "muted", children }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
		className: cn("inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium tracking-wide", {
			muted: "text-muted bg-surface-2",
			ok: "text-ok bg-ok/10",
			warn: "text-warn bg-warn/10",
			danger: "text-danger bg-danger/10",
			accent: "text-accent-fg bg-accent"
		}[tone], className),
		children
	});
}
var NAV = [
	{
		id: "home",
		icon: House,
		group: "اصلی"
	},
	{
		id: "chats",
		icon: MessageSquare,
		group: "اصلی"
	},
	{
		id: "autoreply",
		icon: Sparkles,
		group: "ماژول"
	},
	{
		id: "commands",
		icon: Command,
		group: "ماژول"
	},
	{
		id: "schedule",
		icon: Timer,
		group: "ماژول"
	},
	{
		id: "notes",
		icon: NotebookPen,
		group: "ماژول"
	},
	{
		id: "filters",
		icon: Funnel,
		group: "ماژول"
	},
	{
		id: "snippets",
		icon: Clock3,
		group: "ماژول"
	},
	{
		id: "profile",
		icon: UserRound,
		group: "اکانت"
	},
	{
		id: "activity",
		icon: Activity,
		group: "اکانت"
	},
	{
		id: "settings",
		icon: Settings,
		group: "اکانت"
	}
];
function NavList({ onPick }) {
	const view = useSelfStore((s) => s.view);
	const setView = useSelfStore((s) => s.setView);
	const unread = useSelfStore((s) => s.chats.reduce((n, c) => n + c.unread, 0));
	let last = "";
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("nav", {
		className: "flex flex-col gap-1 px-2",
		children: NAV.map((item) => {
			const Icon = item.icon;
			const showGroup = item.group !== last;
			last = item.group;
			const active = view === item.id;
			return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [showGroup ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "px-3 pb-1 pt-4 text-[11px] font-medium tracking-wide text-subtle",
				children: item.group
			}) : null, /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
				type: "button",
				onClick: () => {
					setView(item.id);
					onPick?.();
				},
				className: cn("flex h-11 w-full items-center gap-2 rounded-md px-3 text-sm transition-colors duration-150", active ? "bg-surface-2 text-fg" : "text-muted hover:bg-surface-2/70 hover:text-fg"),
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Icon, { className: "size-4 shrink-0" }),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "flex-1 text-start",
						children: VIEW_LABEL[item.id]
					}),
					item.id === "chats" && unread > 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "rounded-full bg-accent px-1.5 text-[10px] font-medium text-accent-fg",
						children: unread
					}) : null
				]
			})] }, item.id);
		})
	});
}
function Shell({ children }) {
	const profile = useSelfStore((s) => s.profile);
	const afk = useSelfStore((s) => s.afk);
	const setAfk = useSelfStore((s) => s.setAfk);
	const view = useSelfStore((s) => s.view);
	const setView = useSelfStore((s) => s.setView);
	const activeChatId = useSelfStore((s) => s.activeChatId);
	const [menu, setMenu] = (0, import_react.useState)(false);
	const hideDock = view === "chats" && Boolean(activeChatId);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex h-dvh min-h-dvh overflow-hidden bg-bg text-fg",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("aside", {
			className: "sticky top-0 hidden h-dvh w-60 shrink-0 flex-col border-e border-line lg:flex",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "px-5 pb-2 pt-6",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-[10px] font-medium tracking-[0.22em] text-subtle",
						children: "SELF COMMAND"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "font-display text-3xl italic leading-none",
						children: "Nexa"
					})]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "min-h-0 flex-1 overflow-y-auto pb-4",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(NavList, {})
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "border-t border-line p-3",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-2 rounded-lg bg-surface p-2 shadow-[var(--shadow-border)]",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Avatar, {
							name: profile.name,
							hue: 200,
							size: "sm"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "min-w-0 flex-1",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "truncate text-sm font-medium",
								children: profile.name
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
								className: "truncate text-[11px] text-muted",
								dir: "ltr",
								children: ["@", profile.username]
							})]
						})]
					})
				})
			]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex min-w-0 flex-1 flex-col",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("header", {
					className: "sticky top-0 z-20 flex h-14 items-center gap-2 border-b border-line bg-bg/90 px-3 backdrop-blur-sm lg:h-16 lg:px-6",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Sheet, {
							open: menu,
							onOpenChange: setMenu,
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
								variant: "ghost",
								size: "icon",
								className: "lg:hidden",
								onClick: () => setMenu(true),
								"aria-label": "منو",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Menu, { className: "size-5" })
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(SheetContent, {
								side: "right",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "px-5 pb-2 pt-6",
									children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
										className: "font-display text-2xl italic",
										children: "Nexa"
									})
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SheetClose, {
									asChild: true,
									children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
										className: "min-h-0 flex-1 overflow-y-auto",
										children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(NavList, { onPick: () => setMenu(false) })
									})
								})]
							})]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "min-w-0 flex-1",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "truncate text-sm font-medium lg:hidden",
								children: VIEW_LABEL[view]
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "hidden items-center gap-2 lg:flex",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "relative inline-flex size-2",
										children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "nexa-pulse absolute inset-0 rounded-full bg-ok" })
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "text-xs text-muted",
										children: "نشست فعال"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
										tone: "muted",
										children: profile.sessionId
									})
								]
							})]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center gap-2",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "hidden text-xs text-muted sm:inline",
								children: "افک"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
								checked: afk.on,
								onCheckedChange: (v) => setAfk(v, afk.reason || "کمی بعد برمی‌گردم.")
							})]
						})
					]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("main", {
					className: cn("flex min-h-0 flex-1 flex-col overflow-y-auto px-3 pb-20 pt-5 lg:px-8 lg:pb-8", view === "chats" && "overflow-hidden pt-3 lg:pt-4", hideDock && "pb-3"),
					children
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("nav", {
					className: cn("fixed inset-x-0 bottom-0 z-20 grid grid-cols-4 border-t border-line bg-bg/95 px-2 py-1 backdrop-blur-sm lg:hidden", hideDock && "hidden"),
					children: [
						["home", House],
						["chats", MessageSquare],
						["commands", Command],
						["settings", Settings]
					].map(([id, Icon]) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
						type: "button",
						onClick: () => setView(id),
						className: cn("flex h-12 flex-col items-center justify-center gap-0.5 text-[11px]", view === id ? "text-fg" : "text-muted"),
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Icon, { className: "size-4" }), VIEW_LABEL[id]]
					}, id))
				})
			]
		})]
	});
}
var MODULE_META = [
	{
		key: "autoReply",
		title: "پاسخ خودکار",
		desc: "واکنش به کلیدواژه در گفتگوها",
		icon: MessageSquare,
		view: "autoreply"
	},
	{
		key: "afk",
		title: "حالت دور",
		desc: "پاسخ آماده وقتی در دسترس نیستید",
		icon: Moon
	},
	{
		key: "commands",
		title: "دستورها",
		desc: "پیشوند و فرمان‌های سفارشی",
		icon: Command,
		view: "commands"
	},
	{
		key: "scheduler",
		title: "زمان‌بندی",
		desc: "ارسال در ساعت مشخص",
		icon: Timer,
		view: "schedule"
	},
	{
		key: "filters",
		title: "فیلتر گفتگو",
		desc: "ضد لینک و واژه‌های مسدود",
		icon: Funnel,
		view: "filters"
	},
	{
		key: "clockBio",
		title: "ساعت در بیو",
		desc: "زمان جاری زیر بیو",
		icon: Clock3,
		view: "profile"
	},
	{
		key: "welcome",
		title: "خوشامد پیوی",
		desc: "اولین پیام خصوصی",
		icon: Sparkles
	},
	{
		key: "snippets",
		title: "الگوهای سریع",
		desc: "با /میانبر در ورودی چت",
		icon: Shield,
		view: "snippets"
	}
];
function HomeView() {
	const profile = useSelfStore((s) => s.profile);
	const stats = useSelfStore((s) => s.stats);
	const modules = useSelfStore((s) => s.modules);
	const activity = useSelfStore((s) => s.activity);
	const afk = useSelfStore((s) => s.afk);
	const chats = useSelfStore((s) => s.chats);
	const jobs = useSelfStore((s) => s.jobs);
	const toggleModule = useSelfStore((s) => s.toggleModule);
	const setAfk = useSelfStore((s) => s.setAfk);
	const setView = useSelfStore((s) => s.setView);
	const setActiveChat = useSelfStore((s) => s.setActiveChat);
	const unread = chats.reduce((n, c) => n + c.unread, 0);
	const pendingJobs = jobs.filter((j) => j.status === "pending").length;
	const up = Date.now() - profile.connectedAt;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "nexa-rise",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageTitle, {
				kicker: "Overview",
				title: "نمای کلی",
				hint: `سلام ${profile.name} — نشست ${profile.sessionId} فعال است.`
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "grid grid-cols-2 gap-3 lg:grid-cols-4",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Stat, {
						label: "ارسال امروز",
						value: faNum(stats.byDay[stats.byDay.length - 1]?.sent ?? 0),
						hint: "پیام‌های خودتان"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Stat, {
						label: "پاسخ خودکار",
						value: faNum(stats.autoReplies),
						hint: "شامل افک و خوشامد"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Stat, {
						label: "دستور اجراشده",
						value: faNum(stats.commandsRun),
						hint: "پیشوند فعال"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Stat, {
						label: "زمان نشست",
						value: faNum(Math.max(1, Math.floor(up / 6e4))),
						hint: "دقیقه از اتصال"
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mt-4 grid gap-3 lg:grid-cols-[1.4fr_1fr]",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Surface, {
					className: "p-2 sm:p-4",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "mb-3 flex items-center justify-between px-2 pt-2 sm:px-0 sm:pt-0",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
							className: "text-sm font-medium",
							children: "هفت روز اخیر"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
							tone: "muted",
							children: "محلی"
						})]
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "h-48 w-full",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ResponsiveContainer, {
							width: "100%",
							height: "100%",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(AreaChart, {
								data: stats.byDay,
								margin: {
									top: 8,
									right: 8,
									left: -18,
									bottom: 0
								},
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(CartesianGrid, {
										stroke: "rgba(255,255,255,0.06)",
										vertical: false
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(XAxis, {
										dataKey: "day",
										tick: {
											fill: "#9aa0a6",
											fontSize: 11
										},
										axisLine: false,
										tickLine: false
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(YAxis, {
										tick: {
											fill: "#6d737a",
											fontSize: 11
										},
										axisLine: false,
										tickLine: false,
										allowDecimals: false
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Tooltip, {
										contentStyle: {
											background: "#131517",
											border: "1px solid rgba(255,255,255,0.08)",
											borderRadius: 12,
											color: "#ecece8",
											fontSize: 12
										},
										formatter: (v, name) => [faNum(Number(v)), name === "sent" ? "ارسال" : name === "auto" ? "خودکار" : "دستور"]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Area, {
										type: "monotone",
										dataKey: "sent",
										stroke: "#c9d0d8",
										fill: "rgba(201,208,216,0.12)",
										strokeWidth: 1.6
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Area, {
										type: "monotone",
										dataKey: "auto",
										stroke: "#8aa58f",
										fill: "rgba(138,165,143,0.1)",
										strokeWidth: 1.4
									})
								]
							})
						})
					})]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Surface, { children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-start justify-between gap-3",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
							className: "text-sm font-medium",
							children: "حالت دور"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-1 text-xs text-muted",
							children: afk.on ? `از ${formatDuration(Date.now() - (afk.since ?? Date.now()))} پیش` : "وقتی روشن باشد به پیوی‌ها پاسخ آماده می‌دهد."
						})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
							checked: afk.on,
							onCheckedChange: (v) => setAfk(v, afk.reason || "کمی بعد برمی‌گردم.")
						})]
					}),
					afk.on && afk.reason ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "mt-4 rounded-md bg-surface-2 px-3 py-2 text-sm text-fg",
						children: afk.reason
					}) : null,
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "mt-5 flex flex-wrap gap-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
							tone: unread ? "warn" : "ok",
							children: unread ? `${faNum(unread)} خوانده‌نشده` : "صندوق خالی"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Badge, {
							tone: "muted",
							children: [faNum(pendingJobs), " زمان‌بندی مانده"]
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						variant: "secondary",
						className: "mt-5 w-full",
						onClick: () => {
							const c = chats[0];
							if (c) setActiveChat(c.id);
						},
						children: "رفتن به گفتگوها"
					})
				] })]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mt-4 grid gap-3 lg:grid-cols-[1.2fr_1fr]",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Surface, {
					className: "p-2",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
						className: "px-3 pb-1 pt-2 text-sm font-medium",
						children: "ماژول‌ها"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("ul", {
						className: "divide-y divide-line",
						children: MODULE_META.map((m) => {
							const Icon = m.icon;
							return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("li", {
								className: "flex items-center gap-3 px-3 py-2.5",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "inline-flex size-9 items-center justify-center rounded-sm bg-surface-2 text-muted",
										children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Icon, { className: "size-4" })
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
										type: "button",
										className: "min-w-0 flex-1 text-start",
										onClick: () => m.view && setView(m.view),
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
											className: "text-sm font-medium",
											children: m.title
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
											className: "truncate text-xs text-muted",
											children: m.desc
										})]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
										checked: modules[m.key],
										onCheckedChange: () => toggleModule(m.key)
									})
								]
							}, m.key);
						})
					})]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Surface, {
					className: "p-2",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
						className: "px-3 pb-1 pt-2 text-sm font-medium",
						children: "گزارش تازه"
					}), activity.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "px-3 py-8 text-sm text-muted",
						children: "هنوز رویدادی ثبت نشده. یک دستور در چت بزنید."
					}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("ul", {
						className: "max-h-80 space-y-1 overflow-auto",
						children: activity.slice(0, 10).map((a) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("li", {
							className: "rounded-md px-3 py-2 hover:bg-surface-2",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "text-sm text-fg",
								children: a.detail
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
								className: "text-[11px] text-subtle",
								children: [
									VIEW_LABEL[a.type] ? a.type : a.type,
									" · ",
									faRelative(a.at)
								]
							})]
						}, a.id))
					})]
				})]
			})
		]
	});
}
function ScrollArea({ className, children, ...props }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Root, {
		className: cn("relative overflow-hidden", className),
		...props,
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Viewport, {
			className: "h-full w-full rounded-[inherit]",
			children
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Scrollbar, {
			orientation: "vertical",
			className: "flex w-2 touch-none select-none p-0.5",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Thumb, { className: "relative flex-1 rounded-full bg-line-strong" })
		})]
	});
}
function chatKind(c) {
	if (c.type === "saved") return "ذخیره";
	if (c.type === "group") return `گروه · ${faNum(c.members ?? 0)}`;
	return "خصوصی";
}
function Bubble({ m, selfName }) {
	const mine = m.from === "self";
	const system = m.from === "system";
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: cn("flex w-full", mine ? "justify-start" : "justify-end"),
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: cn("max-w-[85%] rounded-lg px-3 py-2 text-sm leading-relaxed", system ? "bg-surface-2 text-muted shadow-[var(--shadow-border)]" : mine ? "bg-accent text-accent-fg" : "bg-surface-2 text-fg shadow-[var(--shadow-border)]"),
			children: [
				!mine && !system ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "mb-1 text-[11px] font-medium text-muted",
					children: m.senderName
				}) : null,
				system ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "mb-1 text-[11px] font-medium text-subtle",
					children: m.kind === "command" ? "فرمان" : m.kind === "filter" ? "فیلتر" : "سیستم"
				}) : null,
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "whitespace-pre-wrap",
					children: m.text
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
					className: cn("mt-1 text-[10px] tabular", mine ? "text-accent-fg/60" : "text-subtle"),
					children: [faTime(m.at), m.from === "self" && m.senderName === selfName && m.kind !== "text" ? ` · ${m.kind}` : ""]
				})
			]
		})
	});
}
function ChatsView() {
	const chats = useSelfStore((s) => s.chats);
	const messages = useSelfStore((s) => s.messages);
	const activeId = useSelfStore((s) => s.activeChatId);
	const setActiveChat = useSelfStore((s) => s.setActiveChat);
	const sendSelf = useSelfStore((s) => s.sendSelf);
	const injectPeer = useSelfStore((s) => s.injectPeer);
	const profile = useSelfStore((s) => s.profile);
	const prefix = useSelfStore((s) => s.settings.prefix);
	const snippets = useSelfStore((s) => s.snippets);
	const [q, setQ] = (0, import_react.useState)("");
	const [draft, setDraft] = (0, import_react.useState)("");
	const endRef = (0, import_react.useRef)(null);
	const inputRef = (0, import_react.useRef)(null);
	const filtered = (0, import_react.useMemo)(() => {
		const t = q.trim();
		if (!t) return chats;
		return chats.filter((c) => c.title.includes(t) || c.preview.includes(t));
	}, [chats, q]);
	const active = chats.find((c) => c.id === activeId) ?? null;
	const thread = (0, import_react.useMemo)(() => active ? messages.filter((m) => m.chatId === active.id) : [], [messages, active]);
	(0, import_react.useEffect)(() => {
		endRef.current?.scrollIntoView({ block: "end" });
	}, [thread.length, active?.id]);
	function submit(e) {
		e.preventDefault();
		if (!active || !draft.trim()) return;
		sendSelf(active.id, draft);
		setDraft("");
		inputRef.current?.focus();
	}
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex min-h-0 flex-1 flex-col lg:flex-row lg:gap-3",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("aside", {
			className: cn("flex w-full shrink-0 flex-col lg:w-80", active && "hidden lg:flex"),
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "mb-3",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-[11px] font-medium tracking-[0.16em] text-subtle uppercase",
						children: "Inbox"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("h1", {
						className: "font-display text-3xl italic",
						children: "گفتگوها"
					})]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "relative mb-3",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Search, { className: "pointer-events-none absolute end-3 top-1/2 size-4 -translate-y-1/2 text-subtle" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						value: q,
						onChange: (e) => setQ(e.target.value),
						placeholder: "جستجوی گفتگو",
						className: "pe-9"
					})]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ScrollArea, {
					className: "h-[min(60dvh,28rem)] lg:h-auto lg:flex-1",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("ul", {
						className: "flex flex-col gap-1 pb-4",
						children: filtered.map((c) => {
							const on = active?.id === c.id;
							return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("li", { children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
								type: "button",
								onClick: () => setActiveChat(c.id),
								className: cn("flex w-full items-center gap-3 rounded-lg px-2 py-2 text-start transition-colors duration-150", on ? "bg-surface-2" : "hover:bg-surface"),
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Avatar, {
									name: c.title,
									hue: c.hue,
									size: "sm"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
									className: "min-w-0 flex-1",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
										className: "flex items-center justify-between gap-2",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "truncate text-sm font-medium",
											children: c.title
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "shrink-0 text-[11px] text-subtle",
											children: faRelative(c.lastAt)
										})]
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
										className: "mt-0.5 flex items-center gap-2",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "truncate text-xs text-muted",
											children: c.preview
										}), c.unread > 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "ms-auto inline-flex min-w-5 items-center justify-center rounded-full bg-accent px-1.5 text-[10px] font-medium text-accent-fg tabular",
											children: faNum(c.unread)
										}) : null]
									})]
								})]
							}) }, c.id);
						})
					})
				})
			]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("section", {
			className: cn("flex min-h-0 min-w-0 flex-1 flex-col rounded-xl bg-surface shadow-[var(--shadow-border)]", !active && "hidden lg:flex"),
			children: active ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("header", {
					className: "flex items-center gap-3 border-b border-line px-3 py-3",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							type: "button",
							className: "inline-flex size-11 items-center justify-center rounded-sm text-muted hover:bg-surface-2 lg:hidden",
							onClick: () => useSelfStore.setState({ activeChatId: null }),
							"aria-label": "بازگشت",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ChevronRight, { className: "size-5" })
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Avatar, {
							name: active.title,
							hue: active.hue,
							size: "sm"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "min-w-0 flex-1",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "truncate text-sm font-medium",
								children: active.title
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "text-xs text-muted",
								children: chatKind(active)
							})]
						}),
						active.type !== "saved" ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							variant: "ghost",
							size: "sm",
							onClick: () => injectPeer(active.id, "سلام، این یک پیام آزمایشی است تا پاسخ خودکار را ببینید."),
							children: "پیام آزمایشی"
						}) : null
					]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ScrollArea, {
					className: "min-h-0 flex-1",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex flex-col gap-2 px-3 py-4",
						children: [thread.map((m) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Bubble, {
							m,
							selfName: profile.name
						}, m.id)), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", { ref: endRef })]
					})
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "border-t border-line p-3",
					children: [
						snippets.length > 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "mb-2 flex flex-wrap gap-1.5",
							children: [snippets.slice(0, 4).map((s) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
								type: "button",
								className: "rounded-full bg-surface-2 px-2.5 py-1 text-[11px] text-muted hover:text-fg",
								onClick: () => setDraft(`/${s.shortcut}`),
								children: ["/", s.shortcut]
							}, s.id)), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Badge, {
								tone: "muted",
								children: ["پیشوند ", prefix]
							})]
						}) : null,
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("form", {
							onSubmit: submit,
							className: "flex items-end gap-2",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
								ref: inputRef,
								value: draft,
								onChange: (e) => setDraft(e.target.value),
								placeholder: `${prefix}راهنما یا پیام…`,
								className: "flex-1"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
								type: "submit",
								size: "icon",
								"aria-label": "ارسال",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ArrowUp, { className: "size-4" })
							})]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
							className: "mt-2 flex items-center gap-1.5 text-[11px] text-subtle",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Bot, { className: "size-3.5" }), "دستورها و ماژول‌ها روی همین گفتگو اجرا می‌شوند."]
						})
					]
				})
			] }) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "flex flex-1 items-center justify-center p-8 text-sm text-muted",
				children: "یک گفتگو را انتخاب کنید."
			})
		})]
	});
}
var Dialog = Dialog$1;
var DialogTrigger = DialogTrigger$1;
function DialogContent({ className, children, title }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogPortal, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogOverlay, { className: "fixed inset-0 z-50 bg-bg/70 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=open]:fade-in-0 data-[state=closed]:fade-out-0" }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogContent$1, {
		className: cn("fixed left-1/2 top-1/2 z-50 w-[calc(100%-1.5rem)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-xl bg-surface p-4 shadow-[var(--shadow-float),var(--shadow-border)] outline-none data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95", className),
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "mb-4 flex items-center justify-between gap-3",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogTitle, {
				className: "text-base font-medium",
				children: title
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogClose, {
				className: "inline-flex size-9 items-center justify-center rounded-sm text-muted hover:bg-surface-2 hover:text-fg",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(X, { className: "size-4" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
					className: "sr-only",
					children: "بستن"
				})]
			})]
		}), children]
	})] });
}
var MATCH_LABEL = {
	contains: "شامل",
	exact: "دقیق",
	starts: "شروع"
};
function AutoReplyView() {
	const rules = useSelfStore((s) => s.rules);
	const addRule = useSelfStore((s) => s.addRule);
	const updateRule = useSelfStore((s) => s.updateRule);
	const removeRule = useSelfStore((s) => s.removeRule);
	const enabled = useSelfStore((s) => s.modules.autoReply);
	const toggle = useSelfStore((s) => s.toggleModule);
	const [open, setOpen] = (0, import_react.useState)(false);
	const [trigger, setTrigger] = (0, import_react.useState)("");
	const [reply, setReply] = (0, import_react.useState)("");
	const [match, setMatch] = (0, import_react.useState)("contains");
	const [scope, setScope] = (0, import_react.useState)("all");
	function save() {
		if (!trigger.trim() || !reply.trim()) return;
		addRule({
			enabled: true,
			trigger: trigger.trim(),
			reply: reply.trim(),
			match,
			scope,
			delayMs: 600
		});
		setTrigger("");
		setReply("");
		setOpen(false);
		toast("قانون جدید ذخیره شد");
	}
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "nexa-rise",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mb-5 flex flex-wrap items-end justify-between gap-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageTitle, {
					kicker: "Auto",
					title: "پاسخ خودکار",
					hint: "اگر پیام ورودی با قانون جور شود، پنل به‌جای شما جواب می‌دهد."
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "mb-6 flex items-center gap-3",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "text-xs text-muted",
						children: "ماژول"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
						checked: enabled,
						onCheckedChange: () => toggle("autoReply")
					})]
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "mb-4 flex justify-end",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Dialog, {
					open,
					onOpenChange: setOpen,
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogTrigger, {
						asChild: true,
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Plus, { className: "size-4" }), "قانون تازه"] })
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogContent, {
						title: "قانون پاسخ",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex flex-col gap-3",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(FieldStack, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "کلیدواژه" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
									value: trigger,
									onChange: (e) => setTrigger(e.target.value),
									placeholder: "سلام"
								})] }),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(FieldStack, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "پاسخ" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Textarea, {
									value: reply,
									onChange: (e) => setReply(e.target.value),
									rows: 3
								})] }),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "grid grid-cols-2 gap-2",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(FieldStack, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "نوع تطبیق" }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("select", {
										className: "h-11 rounded-md bg-surface-2 px-3 text-sm shadow-[var(--shadow-border)]",
										value: match,
										onChange: (e) => setMatch(e.target.value),
										children: [
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
												value: "contains",
												children: "شامل"
											}),
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
												value: "starts",
												children: "شروع متن"
											}),
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
												value: "exact",
												children: "دقیق"
											})
										]
									})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(FieldStack, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "محدوده" }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("select", {
										className: "h-11 rounded-md bg-surface-2 px-3 text-sm shadow-[var(--shadow-border)]",
										value: scope,
										onChange: (e) => setScope(e.target.value),
										children: [
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
												value: "all",
												children: "همه"
											}),
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
												value: "private",
												children: "فقط پیوی"
											}),
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
												value: "group",
												children: "فقط گروه"
											})
										]
									})] })]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
									onClick: save,
									children: "ذخیره"
								})
							]
						})
					})]
				})
			}),
			rules.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Surface, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyState, {
				title: "قانونی نیست",
				desc: "یک کلیدواژه و پاسخ اضافه کنید، بعد در گفتگو پیام آزمایشی بفرستید."
			}) }) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("ul", {
				className: "flex flex-col gap-2",
				children: rules.map((r) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("li", { children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Surface, {
					className: "flex flex-col gap-3 sm:flex-row sm:items-center",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "min-w-0 flex-1",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex flex-wrap items-center gap-2",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
									className: "font-medium",
									children: r.trigger
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, { children: MATCH_LABEL[r.match] }),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
									tone: "muted",
									children: r.scope === "all" ? "همه" : r.scope === "private" ? "پیوی" : "گروه"
								})
							]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-1 text-sm text-muted",
							children: r.reply
						})]
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
							checked: r.enabled,
							onCheckedChange: (v) => updateRule(r.id, { enabled: v })
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							variant: "ghost",
							size: "iconSm",
							onClick: () => removeRule(r.id),
							"aria-label": "حذف",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Trash2, { className: "size-4" })
						})]
					})]
				}) }, r.id))
			})
		]
	});
}
function CommandsView() {
	const commands = useSelfStore((s) => s.commands);
	const addCommand = useSelfStore((s) => s.addCommand);
	const updateCommand = useSelfStore((s) => s.updateCommand);
	const removeCommand = useSelfStore((s) => s.removeCommand);
	const prefix = useSelfStore((s) => s.settings.prefix);
	const enabled = useSelfStore((s) => s.modules.commands);
	const toggle = useSelfStore((s) => s.toggleModule);
	const [name, setName] = (0, import_react.useState)("");
	const [response, setResponse] = (0, import_react.useState)("");
	const [description, setDescription] = (0, import_react.useState)("");
	function save() {
		if (!name.trim() || !response.trim()) return;
		addCommand({
			enabled: true,
			name: name.trim().replace(/^\./, ""),
			response: response.trim(),
			description: description.trim()
		});
		setName("");
		setResponse("");
		setDescription("");
		toast("دستور اضافه شد");
	}
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "nexa-rise",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageTitle, {
				kicker: "Commands",
				title: "دستورها",
				hint: `در هر گفتگو ${prefix}راهنما را بزنید. دستورهای داخلی همیشه آماده‌اند.`
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mb-4 flex items-center justify-between rounded-lg bg-surface px-4 py-3 shadow-[var(--shadow-border)]",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "text-sm",
					children: "اجرای فرمان با پیشوند"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
					checked: enabled,
					onCheckedChange: () => toggle("commands")
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "grid gap-3 lg:grid-cols-[1fr_1fr]",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Surface, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
					className: "text-sm font-medium",
					children: "دستور تازه"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "mt-4 flex flex-col gap-3",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(FieldStack, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "نام فرمان" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
							value: name,
							onChange: (e) => setName(e.target.value),
							placeholder: "قوانین"
						})] }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(FieldStack, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "توضیح کوتاه" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
							value: description,
							onChange: (e) => setDescription(e.target.value)
						})] }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(FieldStack, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "پاسخ" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Textarea, {
							value: response,
							onChange: (e) => setResponse(e.target.value),
							rows: 4
						})] }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							onClick: save,
							children: "افزودن"
						})
					]
				})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Surface, {
					className: "p-2",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
						className: "px-3 pt-2 text-sm font-medium",
						children: "داخلی و سفارشی"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("ul", {
						className: "mt-2 divide-y divide-line",
						children: [[
							"راهنما",
							"پینگ",
							"ساعت",
							"آیدی",
							"وضعیت",
							"افک",
							"برگشت",
							"بیو",
							"save",
							"نوت",
							"حساب"
						].map((n) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("li", {
							className: "flex items-center justify-between px-3 py-2.5 text-sm",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
								className: "font-mono text-xs",
								dir: "ltr",
								children: [prefix, n]
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
								tone: "muted",
								children: "داخلی"
							})]
						}, n)), commands.map((c) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("li", {
							className: "flex items-center gap-2 px-3 py-2.5",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
									className: "min-w-0 flex-1",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
										className: "font-mono text-xs",
										dir: "ltr",
										children: [prefix, c.name]
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
										className: "truncate text-xs text-muted",
										children: c.description || c.response
									})]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
									checked: c.enabled,
									onCheckedChange: (v) => updateCommand(c.id, { enabled: v })
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
									variant: "ghost",
									size: "iconSm",
									onClick: () => removeCommand(c.id),
									"aria-label": "حذف",
									children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Trash2, { className: "size-4" })
								})
							]
						}, c.id))]
					})]
				})]
			})
		]
	});
}
function ScheduleView() {
	const jobs = useSelfStore((s) => s.jobs);
	const chats = useSelfStore((s) => s.chats);
	const addJob = useSelfStore((s) => s.addJob);
	const cancelJob = useSelfStore((s) => s.cancelJob);
	const [chatId, setChatId] = (0, import_react.useState)(chats[0]?.id ?? "");
	const [text, setText] = (0, import_react.useState)("");
	const [when, setWhen] = (0, import_react.useState)("");
	function save() {
		if (!chatId || !text.trim() || !when) return;
		const at = new Date(when).getTime();
		if (Number.isNaN(at) || at < Date.now() - 1e3) {
			toast("زمان معتبر در آینده انتخاب کنید");
			return;
		}
		addJob(chatId, text.trim(), at);
		setText("");
		toast("زمان‌بندی ثبت شد");
	}
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "nexa-rise",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageTitle, {
			kicker: "Schedule",
			title: "زمان‌بندی",
			hint: "پیام در ساعت مشخص به گفتگوی انتخابی ارسال می‌شود."
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "grid gap-3 lg:grid-cols-[1fr_1.1fr]",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Surface, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex flex-col gap-3",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(FieldStack, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "گفتگو" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("select", {
						className: "h-11 rounded-md bg-surface-2 px-3 text-sm shadow-[var(--shadow-border)]",
						value: chatId,
						onChange: (e) => setChatId(e.target.value),
						children: chats.map((c) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
							value: c.id,
							children: c.title
						}, c.id))
					})] }),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(FieldStack, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "زمان" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						type: "datetime-local",
						value: when,
						onChange: (e) => setWhen(e.target.value),
						dir: "ltr"
					})] }),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(FieldStack, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "متن" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Textarea, {
						value: text,
						onChange: (e) => setText(e.target.value),
						rows: 4
					})] }),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						onClick: save,
						children: "ثبت ارسال"
					})
				]
			}) }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "flex flex-col gap-2",
				children: jobs.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Surface, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyState, {
					title: "صف خالی است",
					desc: "یک پیام و زمان انتخاب کنید."
				}) }) : jobs.map((j) => {
					const chat = chats.find((c) => c.id === j.chatId);
					const tone = j.status === "sent" ? "ok" : j.status === "cancelled" ? "danger" : "warn";
					const label = j.status === "sent" ? "ارسال شد" : j.status === "cancelled" ? "لغو" : "در صف";
					return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Surface, {
						className: "flex items-start justify-between gap-3",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "min-w-0",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
									className: "text-sm font-medium",
									children: chat?.title ?? "گفتگو"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
									className: "mt-1 text-sm text-muted",
									children: j.text
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
									className: "mt-2 text-xs text-subtle",
									children: faDateTime(j.at)
								})
							]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex flex-col items-end gap-2",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
								tone,
								children: label
							}), j.status === "pending" ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
								variant: "ghost",
								size: "sm",
								onClick: () => cancelJob(j.id),
								children: "لغو"
							}) : null]
						})]
					}, j.id);
				})
			})]
		})]
	});
}
function NotesView() {
	const notes = useSelfStore((s) => s.notes);
	const addNote = useSelfStore((s) => s.addNote);
	const updateNote = useSelfStore((s) => s.updateNote);
	const removeNote = useSelfStore((s) => s.removeNote);
	const [title, setTitle] = (0, import_react.useState)("");
	const [body, setBody] = (0, import_react.useState)("");
	const [tags, setTags] = (0, import_react.useState)("");
	const [q, setQ] = (0, import_react.useState)("");
	const shown = (0, import_react.useMemo)(() => {
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
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "nexa-rise",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageTitle, {
			kicker: "Notes",
			title: "یادداشت‌ها",
			hint: "با .save در چت هم می‌توانید سریع ذخیره کنید. با .نوت عنوان را بخوانید."
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "grid gap-3 lg:grid-cols-[0.9fr_1.1fr]",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Surface, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex flex-col gap-3",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(FieldStack, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "عنوان" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						value: title,
						onChange: (e) => setTitle(e.target.value)
					})] }),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(FieldStack, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "متن" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Textarea, {
						value: body,
						onChange: (e) => setBody(e.target.value),
						rows: 5
					})] }),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(FieldStack, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "برچسب‌ها" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						value: tags,
						onChange: (e) => setTags(e.target.value),
						placeholder: "کار، پاسخ"
					})] }),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						onClick: save,
						children: "ذخیره یادداشت"
					})
				]
			}) }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
				value: q,
				onChange: (e) => setQ(e.target.value),
				placeholder: "جستجو",
				className: "mb-3"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("ul", {
				className: "flex flex-col gap-2",
				children: shown.map((n) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("li", { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Surface, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-start justify-between gap-2",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "font-medium",
							children: n.title
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-1 whitespace-pre-wrap text-sm text-muted",
							children: n.body
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "mt-2 flex flex-wrap gap-1",
							children: n.tags.map((t) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, { children: t }, t))
						})
					] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex gap-1",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							variant: "ghost",
							size: "iconSm",
							onClick: () => updateNote(n.id, { pinned: !n.pinned }),
							"aria-label": "پین",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Pin, { className: n.pinned ? "size-4 text-ok" : "size-4" })
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							variant: "ghost",
							size: "iconSm",
							onClick: () => removeNote(n.id),
							"aria-label": "حذف",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Trash2, { className: "size-4" })
						})]
					})]
				}) }) }, n.id))
			})] })]
		})]
	});
}
function FiltersView() {
	const filters = useSelfStore((s) => s.filters);
	const patch = useSelfStore((s) => s.patchFilters);
	const enabled = useSelfStore((s) => s.modules.filters);
	const toggle = useSelfStore((s) => s.toggleModule);
	const stats = useSelfStore((s) => s.stats);
	const [word, setWord] = (0, import_react.useState)("");
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "nexa-rise",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageTitle, {
				kicker: "Filters",
				title: "فیلترها",
				hint: "برای گفتگوهای خودتان: لینک و واژه‌های مشخص در پیام ورودی حذف آزمایشی می‌شوند."
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mb-4 flex items-center justify-between rounded-lg bg-surface px-4 py-3 shadow-[var(--shadow-border)]",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "text-sm",
					children: "موتور فیلتر"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
					checked: enabled,
					onCheckedChange: () => toggle("filters")
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "grid gap-3 md:grid-cols-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Surface, {
					className: "flex items-center justify-between",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-sm font-medium",
						children: "ضد لینک"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-xs text-muted",
						children: "پیام دارای آدرس وب"
					})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
						checked: filters.antiLink,
						onCheckedChange: (v) => patch({ antiLink: v })
					})]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Surface, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "text-sm font-medium",
					children: "حذف‌شده‌ها"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "mt-2 font-display text-3xl italic tabular",
					children: faNum(stats.filtered)
				})] })]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Surface, {
				className: "mt-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(FieldStack, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "متن هشدار" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Textarea, {
					value: filters.warnMessage,
					onChange: (e) => patch({ warnMessage: e.target.value }),
					rows: 2
				})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "mt-4",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "واژه‌های مسدود" }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "mt-2 flex gap-2",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
								value: word,
								onChange: (e) => setWord(e.target.value),
								placeholder: "افزودن واژه"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
								variant: "secondary",
								onClick: () => {
									const w = word.trim();
									if (!w) return;
									patch({ blockedWords: [...filters.blockedWords, w] });
									setWord("");
								},
								children: "افزودن"
							})]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "mt-3 flex flex-wrap gap-2",
							children: filters.blockedWords.map((w) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
								type: "button",
								className: "rounded-full bg-surface-2 px-3 py-1 text-xs text-muted hover:text-danger",
								onClick: () => patch({ blockedWords: filters.blockedWords.filter((x) => x !== w) }),
								children: [w, " ×"]
							}, w))
						})
					]
				})]
			})
		]
	});
}
function SnippetsView() {
	const snippets = useSelfStore((s) => s.snippets);
	const addSnippet = useSelfStore((s) => s.addSnippet);
	const removeSnippet = useSelfStore((s) => s.removeSnippet);
	const enabled = useSelfStore((s) => s.modules.snippets);
	const toggle = useSelfStore((s) => s.toggleModule);
	const [shortcut, setShortcut] = (0, import_react.useState)("");
	const [body, setBody] = (0, import_react.useState)("");
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "nexa-rise",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageTitle, {
				kicker: "Snippets",
				title: "الگوها",
				hint: "در ورودی گفتگو /میانبر را بفرستید تا متن کامل جایگزین شود."
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mb-4 flex items-center justify-between rounded-lg bg-surface px-4 py-3 shadow-[var(--shadow-border)]",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "text-sm",
					children: "جایگزینی الگو"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
					checked: enabled,
					onCheckedChange: () => toggle("snippets")
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "grid gap-3 lg:grid-cols-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Surface, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex flex-col gap-3",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(FieldStack, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "میانبر" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
							value: shortcut,
							onChange: (e) => setShortcut(e.target.value),
							placeholder: "درود"
						})] }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(FieldStack, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "متن کامل" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Textarea, {
							value: body,
							onChange: (e) => setBody(e.target.value),
							rows: 4
						})] }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							onClick: () => {
								if (!shortcut.trim() || !body.trim()) return;
								addSnippet(shortcut, body);
								setShortcut("");
								setBody("");
							},
							children: "افزودن الگو"
						})
					]
				}) }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("ul", {
					className: "flex flex-col gap-2",
					children: snippets.map((s) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("li", { children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Surface, {
						className: "flex items-start justify-between gap-3",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
							className: "font-mono text-xs text-muted",
							dir: "ltr",
							children: ["/", s.shortcut]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-1 text-sm",
							children: s.body
						})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							variant: "ghost",
							size: "iconSm",
							onClick: () => removeSnippet(s.id),
							"aria-label": "حذف",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Trash2, { className: "size-4" })
						})]
					}) }, s.id))
				})]
			})
		]
	});
}
function ProfileView() {
	const profile = useSelfStore((s) => s.profile);
	const baseBio = useSelfStore((s) => s.baseBio);
	const patchProfile = useSelfStore((s) => s.patchProfile);
	const setBaseBio = useSelfStore((s) => s.setBaseBio);
	const clock = useSelfStore((s) => s.modules.clockBio);
	const toggle = useSelfStore((s) => s.toggleModule);
	const [name, setName] = (0, import_react.useState)(profile.name);
	const [username, setUsername] = (0, import_react.useState)(profile.username);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "nexa-rise",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageTitle, {
			kicker: "Account",
			title: "پروفایل",
			hint: "هویت فضای کاری. ساعت در بیو هر دقیقه تازه می‌شود."
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "grid gap-3 lg:grid-cols-[1.1fr_0.9fr]",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Surface, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex flex-col gap-4",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(FieldStack, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "نام" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						value: name,
						onChange: (e) => setName(e.target.value)
					})] }),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(FieldStack, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "نام کاربری" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						value: username,
						onChange: (e) => setUsername(e.target.value),
						dir: "ltr",
						className: "text-start"
					})] }),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(FieldStack, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "بیو" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Textarea, {
						value: baseBio,
						onChange: (e) => setBaseBio(e.target.value),
						rows: 4
					})] }),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						onClick: () => {
							patchProfile({
								name: name.trim() || profile.name,
								username: username.replace(/^@/, "").trim()
							});
							toast("پروفایل ذخیره شد");
						},
						children: "ذخیره هویت"
					})
				]
			}) }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex flex-col gap-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Surface, {
					className: "flex items-center justify-between",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-sm font-medium",
						children: "ساعت در بیو"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-xs text-muted",
						children: "خط زمان به انتهای بیو اضافه می‌شود"
					})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
						checked: clock,
						onCheckedChange: () => toggle("clockBio")
					})]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Surface, { children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-xs text-muted",
						children: "پیش‌نمایش بیو"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "mt-2 whitespace-pre-wrap text-sm leading-relaxed",
						children: profile.bio || "خالی"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "mt-4 flex flex-wrap gap-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
							tone: "ok",
							children: "متصل"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
							tone: "muted",
							children: profile.sessionId
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
						className: "mt-3 text-xs text-subtle",
						children: ["از ", faDateTime(profile.connectedAt)]
					})
				] })]
			})]
		})]
	});
}
function ActivityView() {
	const activity = useSelfStore((s) => s.activity);
	const stats = useSelfStore((s) => s.stats);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "nexa-rise",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageTitle, {
				kicker: "Log",
				title: "گزارش فعالیت",
				hint: "هر فرمان، پاسخ خودکار و فیلتر اینجا ثبت می‌شود."
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Surface, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-xs text-muted",
						children: "ارسال"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "mt-1 font-display text-2xl italic tabular",
						children: faNum(stats.sent)
					})] }),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Surface, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-xs text-muted",
						children: "دریافت"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "mt-1 font-display text-2xl italic tabular",
						children: faNum(stats.received)
					})] }),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Surface, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-xs text-muted",
						children: "خودکار"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "mt-1 font-display text-2xl italic tabular",
						children: faNum(stats.autoReplies)
					})] }),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Surface, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-xs text-muted",
						children: "فیلتر"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "mt-1 font-display text-2xl italic tabular",
						children: faNum(stats.filtered)
					})] })
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Surface, {
				className: "p-2",
				children: activity.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "px-3 py-10 text-center text-sm text-muted",
					children: "هنوز رویدادی نیست."
				}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("ul", {
					className: "divide-y divide-line",
					children: activity.map((a) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("li", {
						className: "flex items-start justify-between gap-3 px-3 py-3",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "text-sm",
							children: a.detail
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "text-[11px] text-subtle",
							children: a.type
						})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "shrink-0 text-xs text-subtle",
							children: faRelative(a.at)
						})]
					}, a.id))
				})
			})
		]
	});
}
function SettingsView() {
	const settings = useSelfStore((s) => s.settings);
	const patch = useSelfStore((s) => s.patchSettings);
	const modules = useSelfStore((s) => s.modules);
	const toggle = useSelfStore((s) => s.toggleModule);
	const reset = useSelfStore((s) => s.resetWorkspace);
	const exportPayload = useSelfStore((s) => s.exportPayload);
	const importPayload = useSelfStore((s) => s.importPayload);
	const [prefix, setPrefix] = (0, import_react.useState)(settings.prefix);
	const [welcome, setWelcome] = (0, import_react.useState)(settings.welcomeText);
	function downloadBackup() {
		const blob = new Blob([exportPayload()], { type: "application/json" });
		const url = URL.createObjectURL(blob);
		const a = document.createElement("a");
		a.href = url;
		a.download = "nexa-backup.json";
		a.click();
		URL.revokeObjectURL(url);
		toast("فایل پشتیبان آماده شد");
	}
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "nexa-rise",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageTitle, {
			kicker: "Settings",
			title: "تنظیمات",
			hint: "پیشوند فرمان، دمو زنده و پشتیبان فضای کاری."
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex flex-col gap-3",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Surface, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "grid gap-4 sm:grid-cols-2",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(FieldStack, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "پیشوند دستور" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						value: prefix,
						maxLength: 2,
						dir: "ltr",
						className: "text-start",
						onChange: (e) => setPrefix(e.target.value),
						onBlur: () => patch({ prefix: prefix || "." })
					})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(FieldStack, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "پیام خوشامد پیوی" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Textarea, {
						value: welcome,
						onChange: (e) => setWelcome(e.target.value),
						rows: 2
					})] })]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					className: "mt-4",
					variant: "secondary",
					onClick: () => {
						patch({
							prefix: prefix || ".",
							welcomeText: welcome
						});
						toast("تنظیمات ذخیره شد");
					},
					children: "ذخیره تنظیمات"
				})] }),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Surface, {
					className: "p-2",
					children: [
						{
							key: "liveDemo",
							title: "دمو زنده ورودی",
							desc: "هر از گاهی پیام آزمایشی به گفتگوها می‌آید"
						},
						{
							key: "typingDelay",
							title: "تأخیر پاسخ",
							desc: "پاسخ ماژول‌ها کمی بعد ظاهر می‌شود"
						},
						{
							key: "autoRead",
							module: true,
							title: "خواندن خودکار",
							desc: "پیام ورودی بدون شمارنده می‌ماند"
						}
					].map((row) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center justify-between gap-3 px-3 py-3",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "text-sm font-medium",
							children: row.title
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "text-xs text-muted",
							children: row.desc
						})] }), "module" in row ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
							checked: modules.autoRead,
							onCheckedChange: () => toggle("autoRead")
						}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
							checked: settings[row.key],
							onCheckedChange: (v) => patch({ [row.key]: v })
						})]
					}, row.title))
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Surface, { children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-sm font-medium",
						children: "پشتیبان"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "mt-1 text-xs text-muted",
						children: "قوانین، دستورها، یادداشت‌ها و تنظیمات — بدون گفتگوها."
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "mt-4 flex flex-wrap gap-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							variant: "secondary",
							onClick: downloadBackup,
							children: "دریافت JSON"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
							className: "inline-flex h-11 cursor-pointer items-center rounded-md bg-surface-2 px-4 text-sm shadow-[var(--shadow-border)]",
							children: ["ورود فایل", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
								type: "file",
								accept: "application/json",
								className: "hidden",
								onChange: async (e) => {
									const file = e.target.files?.[0];
									if (!file) return;
									const text = await file.text();
									const ok = importPayload(text);
									toast(ok ? "وارد شد" : "فایل نامعتبر بود");
								}
							})]
						})]
					})
				] }),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Surface, { children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-sm font-medium",
						children: "بازنشانی فضای کاری"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "mt-1 text-xs text-muted",
						children: "هویت و گفتگوها پاک می‌شود و صفحهٔ اتصال دوباره می‌آید."
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						variant: "danger",
						className: "mt-4",
						onClick: () => {
							if (window.confirm("فضای کاری پاک شود؟")) reset();
						},
						children: "پاک کردن نشست"
					})
				] })
			]
		})]
	});
}
function ViewSwitch() {
	switch (useSelfStore((s) => s.view)) {
		case "home": return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(HomeView, {});
		case "chats": return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ChatsView, {});
		case "autoreply": return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(AutoReplyView, {});
		case "commands": return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CommandsView, {});
		case "schedule": return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ScheduleView, {});
		case "notes": return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(NotesView, {});
		case "filters": return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(FiltersView, {});
		case "snippets": return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SnippetsView, {});
		case "profile": return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ProfileView, {});
		case "activity": return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ActivityView, {});
		case "settings": return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SettingsView, {});
		default: return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(HomeView, {});
	}
}
function Runtime() {
	const flushDueJobs = useSelfStore((s) => s.flushDueJobs);
	const tickClockBio = useSelfStore((s) => s.tickClockBio);
	const runLiveDemoTick = useSelfStore((s) => s.runLiveDemoTick);
	const liveDemo = useSelfStore((s) => s.settings.liveDemo);
	const clockBio = useSelfStore((s) => s.modules.clockBio);
	(0, import_react.useEffect)(() => {
		const id = window.setInterval(() => flushDueJobs(), 4e3);
		return () => window.clearInterval(id);
	}, [flushDueJobs]);
	(0, import_react.useEffect)(() => {
		if (!clockBio) return;
		tickClockBio();
		const id = window.setInterval(() => tickClockBio(), 3e4);
		return () => window.clearInterval(id);
	}, [clockBio, tickClockBio]);
	(0, import_react.useEffect)(() => {
		if (!liveDemo) return;
		const id = window.setInterval(() => runLiveDemoTick(), 28e3);
		return () => window.clearInterval(id);
	}, [liveDemo, runLiveDemoTick]);
	return null;
}
function NexaApp() {
	const hydrated = useSelfStore((s) => s.hydrated);
	const setHydrated = useSelfStore((s) => s.setHydrated);
	const profile = useSelfStore((s) => s.profile);
	(0, import_react.useEffect)(() => {
		const unsub = useSelfStore.persist.onFinishHydration(() => setHydrated());
		Promise.resolve(useSelfStore.persist.rehydrate());
		if (useSelfStore.persist.hasHydrated()) setHydrated();
		return unsub;
	}, [setHydrated]);
	if (!hydrated) return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "flex min-h-dvh items-center justify-center bg-bg text-muted",
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "text-sm",
			children: "در حال آماده‌سازی پنل…"
		})
	});
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(TooltipProvider, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Toaster, {
		theme: "dark",
		position: "top-center",
		toastOptions: { style: {
			background: "#131517",
			color: "#ecece8",
			border: "1px solid rgba(255,255,255,0.08)",
			fontFamily: "Vazirmatn, sans-serif"
		} }
	}), profile ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Runtime, {}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Shell, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ViewSwitch, {}) })] }) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Onboarding, {})] });
}
function Home() {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(NexaApp, {});
}
//#endregion
export { Home as component };
