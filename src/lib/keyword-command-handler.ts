import {
  createKeywordRule,
  deleteKeywordRule,
  getKeywordRule,
  listKeywordRules,
  markKeywordRuleExecuted,
  setKeywordRuleEnabled,
  type KeywordTriggerType,
} from "./keyword-engine";
import type { CommandContext, CommandHandler, CommandResult } from "./command-router";

const triggerTypes = new Set<KeywordTriggerType>([
  "exact",
  "contains",
  "starts_with",
  "ends_with",
  "regex",
]);

function ok(key: string, args: string[], message: string): CommandResult {
  return { ok: true, key, args, message };
}

function fail(key: string, args: string[], message: string): CommandResult {
  return { ok: false, key, args, message };
}

function requireUser(context: CommandContext) {
  return context.userId?.trim() || null;
}

function parseId(value?: string) {
  if (!value || !/^\d+$/.test(value)) return null;
  return Number(value);
}

function ruleLine(rule: Awaited<ReturnType<typeof listKeywordRules>>[number]) {
  const status = rule.enabled ? "● فعال" : "○ متوقف";
  return [
    `⛂ - #${rule.id} | ${rule.name}`,
    `⛂ - وضعیت : ${status}`,
    `⛂ - محرک : ${rule.triggerType} «${rule.triggerValue}»`,
    `⛂ - محدوده : ${rule.scope}`,
    `⛂ - اجرا : ${rule.executionCount}`,
  ].join("\n");
}

export const keywordCommandHandler: CommandHandler = async (command, context) => {
  const ownerId = requireUser(context);
  if (!ownerId) {
    return fail(command.key, command.args, "شناسه حساب برای مدیریت قوانین مشخص نیست.");
  }

  const [subcommand, ...rest] = command.args;
  const sub = (subcommand ?? "status").toLocaleLowerCase();

  if (sub === "list" || sub === "لیست") {
    const rules = await listKeywordRules(ownerId);
    if (!rules.length) {
      return ok(
        command.key,
        command.args,
        "◈ اقدامات کلمه‌ای\n\n⛂ - هنوز قانونی برای این حساب ساخته نشده است.\n⛂ - برای ساخت قانون از «keyword add» استفاده کنید.",
      );
    }

    return ok(
      command.key,
      command.args,
      `◈ فهرست اقدامات کلمه‌ای\n\n${rules.map(ruleLine).join("\n\n─────━━─────\n\n")}`,
    );
  }

  if (sub === "status" || sub === "وضعیت") {
    const rules = await listKeywordRules(ownerId);
    const active = rules.filter((rule) => rule.enabled).length;
    return ok(
      command.key,
      command.args,
      [
        "◈ وضعیت اقدامات کلمه‌ای",
        "",
        `★ - وضعیت سیستم : ${active ? "● فعال" : "○ بدون قانون فعال"}`,
        `⛂ - کل قوانین : ${rules.length}`,
        `⛂ - قوانین فعال : ${active}`,
        `⛂ - قوانین متوقف : ${rules.length - active}`,
      ].join("\n"),
    );
  }

  const id = parseId(rest[0]);

  if (sub === "info" || sub === "اطلاعات") {
    if (!id) return fail(command.key, command.args, "شناسه قانون را وارد کنید؛ مثال: keyword info 7");
    const rule = await getKeywordRule(ownerId, id);
    if (!rule) return fail(command.key, command.args, "قانون موردنظر پیدا نشد.");

    return ok(
      command.key,
      command.args,
      [
        `◈ قانون کلمه‌ای #${rule.id}`,
        "",
        "★ - اطلاعات قانون",
        `⛂ - نام : ${rule.name}`,
        `⛂ - وضعیت : ${rule.enabled ? "● فعال" : "○ متوقف"}`,
        `⛂ - محرک : ${rule.triggerType} «${rule.triggerValue}»`,
        `⛂ - محدوده : ${rule.scope}`,
        `⛂ - Cooldown : ${rule.cooldownSeconds} ثانیه`,
        `⛂ - تأخیر : ${rule.delayMin} تا ${rule.delayMax} ثانیه`,
        "",
        "★ - عملکرد",
        `⛂ - تعداد اجرا : ${rule.executionCount}`,
        `⛂ - آخرین اجرا : ${rule.lastExecutedAt ?? "هنوز اجرا نشده"}`,
      ].join("\n"),
    );
  }

  if (sub === "pause" || sub === "توقف") {
    if (!id) return fail(command.key, command.args, "شناسه قانون را وارد کنید؛ مثال: keyword pause 7");
    const rule = await setKeywordRuleEnabled(ownerId, id, false);
    if (!rule) return fail(command.key, command.args, "قانون موردنظر پیدا نشد.");
    return ok(command.key, command.args, `◈ قانون #${id}\n\n⛂ - وضعیت : ○ متوقف\n⛂ - قانون بدون حذف، متوقف شد.`);
  }

  if (sub === "resume" || sub === "ادامه") {
    if (!id) return fail(command.key, command.args, "شناسه قانون را وارد کنید؛ مثال: keyword resume 7");
    const rule = await setKeywordRuleEnabled(ownerId, id, true);
    if (!rule) return fail(command.key, command.args, "قانون موردنظر پیدا نشد.");
    return ok(command.key, command.args, `◈ قانون #${id}\n\n⛂ - وضعیت : ● فعال\n⛂ - قانون دوباره فعال شد.`);
  }

  if (sub === "del" || sub === "delete" || sub === "حذف") {
    if (!id) return fail(command.key, command.args, "شناسه قانون را وارد کنید؛ مثال: keyword del 7");
    const deleted = await deleteKeywordRule(ownerId, id);
    if (!deleted) return fail(command.key, command.args, "قانون موردنظر پیدا نشد.");
    return ok(command.key, command.args, `◈ حذف قانون #${id}\n\n⛂ - وضعیت : ● انجام شد\n⛂ - قانون با موفقیت حذف شد.`);
  }

  if (sub === "add" || sub === "افزودن") {
    const [name, triggerTypeRaw, triggerValue, scope = "all"] = rest;
    const triggerType = (triggerTypeRaw ?? "contains") as KeywordTriggerType;
    if (!name || !triggerValue) {
      return fail(
        command.key,
        command.args,
        "ساختار دستور کامل نیست.\n\nمثال:\nkeyword add قیمت contains قیمت pm",
      );
    }
    if (!triggerTypes.has(triggerType)) {
      return fail(command.key, command.args, "نوع محرک معتبر نیست. گزینه‌ها: exact, contains, starts_with, ends_with, regex");
    }

    try {
      const rule = await createKeywordRule({
        ownerId,
        name,
        triggerType,
        triggerValue,
        scope,
      });
      return ok(
        command.key,
        command.args,
        [
          "◈ قانون کلمه‌ای ساخته شد",
          "",
          `★ - شناسه : #${rule.id}`,
          `⛂ - نام : ${rule.name}`,
          `⛂ - محرک : ${rule.triggerType} «${rule.triggerValue}»`,
          `⛂ - محدوده : ${rule.scope}`,
          "⛂ - وضعیت : ● فعال",
          "",
          "برای مشاهده جزئیات:",
          `keyword info ${rule.id}`,
        ].join("\n"),
      );
    } catch (error) {
      return fail(
        command.key,
        command.args,
        error instanceof Error ? error.message : "ساخت قانون ناموفق بود.",
      );
    }
  }

  if (sub === "test" || sub === "تست") {
    if (!id) return fail(command.key, command.args, "شناسه قانون را وارد کنید؛ مثال: keyword test 7");
    const rule = await getKeywordRule(ownerId, id);
    if (!rule) return fail(command.key, command.args, "قانون موردنظر پیدا نشد.");
    await markKeywordRuleExecuted(ownerId, id);
    return ok(
      command.key,
      command.args,
      `◈ تست قانون #${id}\n\n⛂ - وضعیت : ● موفق\n⛂ - قانون قابل اجراست.\n⛂ - تست به‌عنوان یک اجرای آزمایشی ثبت شد.`,
    );
  }

  return fail(
    command.key,
    command.args,
    "دستور اقدامات کلمه‌ای شناخته نشد.\n\nراهنما: keyword list | keyword add | keyword info 7 | keyword test 7 | keyword pause 7 | keyword resume 7 | keyword del 7 | keyword status",
  );
};
