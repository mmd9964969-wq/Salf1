export type ChatType = "private" | "group" | "saved";
export type MatchMode = "contains" | "exact" | "starts";
export type MessageFrom = "self" | "peer" | "system";
export type MessageKind = "text" | "command" | "auto-reply" | "scheduled" | "afk" | "welcome" | "filter";
export type JobStatus = "pending" | "sent" | "cancelled";
export type ViewId =
  | "home"
  | "chats"
  | "autoreply"
  | "commands"
  | "schedule"
  | "notes"
  | "filters"
  | "snippets"
  | "profile"
  | "activity"
  | "settings";

export type Profile = {
  name: string;
  username: string;
  bio: string;
  sessionId: string;
  connectedAt: number;
};

export type Chat = {
  id: string;
  title: string;
  type: ChatType;
  preview: string;
  lastAt: number;
  unread: number;
  muted: boolean;
  members?: number;
  username?: string;
  about?: string;
  hue: number;
  peerName?: string;
};

export type Message = {
  id: string;
  chatId: string;
  from: MessageFrom;
  senderName: string;
  text: string;
  at: number;
  kind: MessageKind;
};

export type AutoReplyRule = {
  id: string;
  enabled: boolean;
  trigger: string;
  match: MatchMode;
  reply: string;
  delayMs: number;
  scope: "all" | "private" | "group";
};

export type CustomCommand = {
  id: string;
  enabled: boolean;
  name: string;
  response: string;
  description: string;
};

export type ScheduledJob = {
  id: string;
  chatId: string;
  text: string;
  at: number;
  status: JobStatus;
};

export type Note = {
  id: string;
  title: string;
  body: string;
  tags: string[];
  pinned: boolean;
  createdAt: number;
};

export type Snippet = {
  id: string;
  shortcut: string;
  body: string;
};

export type Activity = {
  id: string;
  at: number;
  type: string;
  detail: string;
};

export type Modules = {
  autoReply: boolean;
  afk: boolean;
  commands: boolean;
  scheduler: boolean;
  filters: boolean;
  clockBio: boolean;
  autoRead: boolean;
  welcome: boolean;
  snippets: boolean;
};

export type FilterConfig = {
  antiLink: boolean;
  antiForward: boolean;
  blockedWords: string[];
  warnMessage: string;
};

export type AfkState = {
  on: boolean;
  reason: string;
  since: number | null;
  lastReplyAt: Record<string, number>;
};

export type Settings = {
  prefix: string;
  typingDelay: boolean;
  liveDemo: boolean;
  compactChats: boolean;
  welcomeText: string;
};

export type DayStat = {
  day: string;
  sent: number;
  auto: number;
  commands: number;
};

export type Stats = {
  sent: number;
  received: number;
  autoReplies: number;
  commandsRun: number;
  filtered: number;
  scheduledSent: number;
  byDay: DayStat[];
};
