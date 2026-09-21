export type CommandDefinition = {
  key: string;
  aliases: string[];
  description: string;
  usage: string[];
  category: string;
};

export type ParsedCommand = {
  key: string;
  args: string[];
  raw: string;
};

const definitions: CommandDefinition[] = [
  {
    key: "panel",
    aliases: ["panel", "پنل"],
    description: "باز کردن پنل مدیریت Salf1",
    usage: ["پنل", "/panel"],
    category: "core",
  },
  {
    key: "balance",
    aliases: ["balance", "موجودی"],
    description: "نمایش موجودی و وضعیت مصرف ترون",
    usage: ["/موجودی", "/balance"],
    category: "billing",
  },
  {
    key: "keyword",
    aliases: ["keyword", "کلمه"],
    description: "مدیریت حرفه‌ای اقدامات کلمه‌ای و قوانین خودکار",
    usage: ["کلمه افزودن", "کلمه لیست", "کلمه اطلاعات 7", "کلمه تست 7", "کلمه شرط 7 وضعیت", "کلمه شرط 7 کاربر 123", "کلمه شرط 7 گفتگو -100123", "کلمه شرط 7 نوع گروه", "کلمه شرط 7 زمان 09:00 18:00", "کلمه شرط 7 حداکثر 10", "کلمه شرط 7 پاکسازی", "کلمه توقف 7", "کلمه ادامه 7", "کلمه حذف 7", "کلمه وضعیت", "/keyword add", "/keyword list", "/keyword info 7"],
    category: "automation",
  },
  {
    key: "autoread",
    aliases: ["autoread", "خواندن"],
    description: "مدیریت خواندن خودکار",
    usage: ["خواندن وضعیت", "/autoread status"],
    category: "automation",
  },
  {
    key: "autoreact",
    aliases: ["autoreact", "واکنش"],
    description: "مدیریت واکنش خودکار",
    usage: ["واکنش لیست", "/autoreact list"],
    category: "automation",
  },
  {
    key: "autoreply",
    aliases: ["autoreply", "پاسخ"],
    description: "مدیریت پاسخ خودکار",
    usage: ["پاسخ لیست", "/autoreply list"],
    category: "automation",
  },
  {
    key: "afk",
    aliases: ["afk", "عدم", "عدم‌دسترسی"],
    description: "مدیریت وضعیت عدم دسترسی",
    usage: ["عدم‌دسترسی وضعیت", "/afk status"],
    category: "automation",
  },
  {
    key: "profile",
    aliases: ["profile", "پروفایل"],
    description: "نمایش یا مدیریت پروفایل",
    usage: ["پروفایل", "/profile"],
    category: "account",
  },
  {
    key: "security",
    aliases: ["security", "امنیت"],
    description: "مدیریت وضعیت امنیت و نشست‌ها",
    usage: ["امنیت وضعیت", "/security status"],
    category: "security",
  },
];

const normalize = (value: string) =>
  value
    .trim()
    .replace(/^\//, "")
    .replace(/[\u200c]/g, "")
    .toLocaleLowerCase();

export const commandDefinitions = definitions;

export function resolveCommand(input: string): ParsedCommand | null {
  const raw = input.trim();
  if (!raw) return null;

  const parts = raw.split(/\s+/);
  const head = normalize(parts.shift() ?? "");

  const definition = definitions.find((item) =>
    item.aliases.some((alias) => normalize(alias) === head),
  );

  if (!definition) return null;

  return {
    key: definition.key,
    args: parts,
    raw,
  };
}

export function getCommandDefinition(key: string) {
  return definitions.find((item) => item.key === key) ?? null;
}

export function getAllCommandDefinitions() {
  return [...definitions];
}
