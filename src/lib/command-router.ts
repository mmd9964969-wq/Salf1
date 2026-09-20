import {
  getCommandDefinition,
  resolveCommand,
  type ParsedCommand,
} from "./command-registry";

export type CommandContext = {
  userId?: string;
  chatId?: string;
  isOwner?: boolean;
};

export type CommandResult =
  | { ok: true; key: string; message: string; args: string[] }
  | { ok: false; key?: string; message: string; args?: string[] };

export type CommandHandler = (
  command: ParsedCommand,
  context: CommandContext,
) => Promise<CommandResult> | CommandResult;

const handlers = new Map<string, CommandHandler>();

export function registerCommandHandler(key: string, handler: CommandHandler) {
  if (!getCommandDefinition(key)) {
    throw new Error(`Unknown command: ${key}`);
  }

  handlers.set(key, handler);
  return () => handlers.delete(key);
}

export function unregisterCommandHandler(key: string) {
  handlers.delete(key);
}

export function hasCommandHandler(key: string) {
  return handlers.has(key);
}

export async function executeCommand(
  input: string,
  context: CommandContext = {},
): Promise<CommandResult> {
  const command = resolveCommand(input);

  if (!command) {
    return {
      ok: false,
      message: "دستور شناخته نشد. از پنل راهنمای Salf1 استفاده کنید.",
    };
  }

  const handler = handlers.get(command.key);

  if (!handler) {
    return {
      ok: false,
      key: command.key,
      args: command.args,
      message: `دستور «${command.key}» در حال حاضر در موتور Salf1 متصل نشده است.`,
    };
  }

  try {
    return await handler(command, context);
  } catch {
    return {
      ok: false,
      key: command.key,
      args: command.args,
      message: "اجرای دستور با خطای داخلی متوقف شد.",
    };
  }
}

export function getRegisteredCommands() {
  return [...handlers.keys()]
    .map((key) => getCommandDefinition(key))
    .filter((item): item is NonNullable<typeof item> => Boolean(item));
}
