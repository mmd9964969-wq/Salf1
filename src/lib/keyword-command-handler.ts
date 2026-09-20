import {
  createKeywordRule,
  deleteKeywordRule,
  getKeywordRule,
  listKeywordRules,
  matchesKeywordRule,\n  explainKeywordConditions,\n  explainKeywordMatch,\n  getKeywordCooldownRemaining,
  setKeywordRuleEnabled,\n  updateKeywordRuleConditions,
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

  if (sub === "condition" || sub === "شرط") {
    if (!id) return fail(command.key, command.args, "شناسه قانون را وارد کنید؛ مثال: keyword condition 7 time 09:00 18:00");
    const action = (rest[1] ?? "status").toLocaleLowerCase();
    const rule = await getKeywordRule(ownerId, id);
    if (!rule) return fail(command.key, command.args, "قانون موردنظر پیدا نشد.");
    const current = { ...(rule.conditions ?? {}) };
    if (action === "check" || action === "بررسی") {
      const userId = rest[2] ?? "";
      const chatId = rest[3] ?? "";
      const chatType = rest[4] ?? "";
      const result = explainKeywordConditions(rule, { userId, chatId, chatType });
      const cooldownRemaining = getKeywordCooldownRemaining(rule);
      const maxExecutions = Number((rule.conditions ?? {}).max_executions);
      const maxReached = Number.isFinite(maxExecutions) && maxExecutions > 0 && rule.executionCount >= maxExecutions;
      return ok(command.key, command.args, [
        `◈ بررسی شرایط قانون #${id}`,
        "",
        `⛂ - کاربر : ${userId || "—"}`,
        `⛂ - گفتگو : ${chatId || "—"}`,
        `⛂ - نوع : ${chatType || "—"}`,
        `⛂ - نتیجه : ${result.matched ? "● مجاز برای اجرا" : "○ مسدود"}`,
        `⛂ - دلیل : ${result.reason}`,\n        `⛂ - Cooldown : ${cooldownRemaining > 0 ? `${cooldownRemaining} ثانیه باقی‌مانده` : "آزاد"}`,\n        `⛂ - سقف اجرا : ${maxReached ? "● تکمیل شده" : Number.isFinite(maxExecutions) && maxExecutions > 0 ? `${rule.executionCount}/${maxExecutions}` : "نامحدود"}`,
      ].join("\\n"));
    }

    if (action === "status" || action === "وضعیت") {
      return ok(command.key, command.args, [
        `◈ شرایط قانون #${id}`,
        "",
        `⛂ - کاربرها : ${Array.isArray(current.user_ids) ? current.user_ids.join(", ") || "همه" : "همه"}`,
        `⛂ - گفتگوها : ${Array.isArray(current.chat_ids) ? current.chat_ids.join(", ") || "همه" : "همه"}`,
        `⛂ - نوع گفتگو : ${Array.isArray(current.chat_types) ? current.chat_types.join(", ") || "همه" : "همه"}`,
        `⛂ - استثنای کاربر : ${Array.isArray(current.excluded_user_ids) ? current.excluded_user_ids.join(", ") || "ندارد" : "ندارد"}`,
        `⛂ - استثنای گفتگو : ${Array.isArray(current.excluded_chat_ids) ? current.excluded_chat_ids.join(", ") || "ندارد" : "ندارد"}`,
        `⛂ - زمان : ${current.time_start && current.time_end ? `${current.time_start} تا ${current.time_end}` : "همیشه"}`,
        `⛂ - سقف اجرا : ${current.max_executions ?? "نامحدود"}`,
      ].join("\n"));
    }

    let next = { ...current } as Record<string, unknown>;
    if (action === "user" || action === "کاربر") next.user_ids = rest.slice(2);
    else if (action === "chat" || action === "گفتگو") next.chat_ids = rest.slice(2);
    else if (action === "type" || action === "نوع") next.chat_types = rest.slice(2);
    else if (action === "exclude-user" || action === "استثنای-کاربر") next.excluded_user_ids = rest.slice(2);
    else if (action === "exclude-chat" || action === "استثنای-گفتگو") next.excluded_chat_ids = rest.slice(2);
    else if (action === "time" || action === "زمان") {
      if (!/^\\d{2}:\\d{2}$/.test(rest[2] ?? "") || !/^\\d{2}:\\d{2}$/.test(rest[3] ?? "")) {
        return fail(command.key, command.args, "زمان را به شکل HH:MM وارد کنید؛ مثال: keyword condition 7 time 09:00 18:00");
      }
      next.time_start = rest[2];
      next.time_end = rest[3];
    } else if (action === "max" || action === "حداکثر") {
      const max = Number(rest[2]);
      if (!Number.isInteger(max) || max < 1) return fail(command.key, command.args, "حداکثر اجرا باید یک عدد صحیح مثبت باشد.");
      next.max_executions = max;
    } else if (action === "clear" || action === "پاکسازی") {
      next = {};
    } else {
      return fail(command.key, command.args, "شرط ناشناخته است. گزینه‌ها: user, chat, type, exclude-user, exclude-chat, time, max, clear, status");
    }

    const updated = await updateKeywordRuleConditions(ownerId, id, next);
    if (!updated) return fail(command.key, command.args, "قانون موردنظر پیدا نشد.");
    return ok(command.key, command.args, `◈ شرایط قانون #${id} به‌روزرسانی شد\\n\\n⛂ - وضعیت : ● ذخیره شد\\n⛂ - برای مشاهده: keyword condition ${id} status`);
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

    const testText = rest.slice(1).join(" ").trim();
    if (!testText) {
      return ok(
        command.key,
        command.args,
        [
          `◈ تست قانون #${id}`,
          "",
          `⛂ - محرک : ${rule.triggerType} «${rule.triggerValue}»`,
          `⛂ - وضعیت قانون : ${rule.enabled ? "● فعال" : "○ متوقف"}`,
          "",
          "⛂ - برای شبیه‌سازی پیام، متن را بعد از شناسه وارد کنید.",
          `⛂ - مثال : keyword test ${id} قیمت لطفاً`,
          "",
          "⛂ - این تست هیچ اجرای واقعی را ثبت نمی‌کند.",
        ].join("\n"),
      );
    }

    const matched = matchesKeywordRule(rule, testText);
    return ok(
      command.key,
      command.args,
      [
        `◈ نتیجه تست قانون #${id}`,
        "",
        `⛂ - متن آزمایشی : «${testText}»`,
        `⛂ - نتیجه محرک : ${matched ? "● Match شد" : "○ Match نشد"}`,
        `⛂ - وضعیت قانون : ${rule.enabled ? "● فعال" : "○ متوقف"}`,
        "⛂ - اجرا : بدون ثبت در آمار واقعی",
        matched
          ? "⛂ - موتور Keyword این متن را واجد شرایط تشخیص داد."
          : "⛂ - موتور Keyword این متن را مطابق محرک فعلی تشخیص نداد.",
      ].join("\n"),
    );
  }

  return fail(
    command.key,
    command.args,
    "دستور اقدامات کلمه‌ای شناخته نشد.\n\nراهنما: keyword list | keyword add | keyword info 7 | keyword test 7 [text] | keyword pause 7 | keyword resume 7 | keyword del 7 | keyword status",
  );
};
