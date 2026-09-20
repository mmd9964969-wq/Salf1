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
    usage: ["/panel", "پنل"],
    category: "core",
  },
  {
    key: "balance",
    aliases: ["balance", "موجودی"],
    description: "نمایش موجودی و وضعیت مصرف ترون",
    usage: ["/balance", "/موجودی"],
    category: "billing",
  },
  {
    key: "keyword",
    aliases: ["keyword", "کلمه"],
    description: "مدیریت حرفه‌ای اقدامات کلمه‌ای و قوانین خودکار",
    usage: ["/keyword add", "/keyword list", "/keyword info 7", "/keyword test 7", "/keyword pause 7", "/keyword resume 7", "/keyword del 7", "/keyword status"],
    category: "automation",
  },
  {
    key: "autoread",
    aliases: ["autoread", "خواندن"],
    description: "مدیریت خواندن خودکار",
    usage: ["/autoread status", "خواندن status"],
    category: "automation",
  },
  {
    key: "autoreact",
    aliases: ["autoreact", "واکنش"],
    description: "مدیریت واکنش خودکار",
    usage: ["/autoreact list", "واکنش list"],
    category: "automation",
  },
  {
    key: "autoreply",
    aliases: ["autoreply", "پاسخ"],
    description: "مدیریت پاسخ خودکار",
    usage: ["/autoreply list", "پاسخ list"],
    category: "automation",
  },
  {
    key: "afk",
    aliases: ["afk", "عدم", "عدم‌دسترسی"],
    description: "مدیریت وضعیت عدم دسترسی",
    usage: ["/afk status", "عدم status"],
    category: "automation",
  },
  {
    key: "profile",
    aliases: ["profile", "پروفایل"],
    description: "نمایش یا مدیریت پروفایل",
    usage: ["/profile", "پروفایل"],
    category: "account",
  },
  {
    key: "security",
    aliases: ["security", "امنیت"],
    description: "مدیریت وضعیت امنیت و نشست‌ها",
    usage: ["/security status", "امنیت status"],
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
