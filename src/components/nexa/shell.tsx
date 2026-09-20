import type { ReactNode } from "react";
import {
  Activity,
  Clock3,
  Command,
  Filter,
  Home,
  Menu,
  MessageSquare,
  NotebookPen,
  Settings,
  Timer,
  UserRound,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetClose, SheetContent } from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";
import { useSelfStore, VIEW_LABEL } from "@/lib/store";
import type { ViewId } from "@/lib/types";
import { Avatar } from "./kit";
import { useState } from "react";

const NAV: { id: ViewId; icon: typeof Home; group: string }[] = [
  { id: "home", icon: Home, group: "اصلی" },
  { id: "chats", icon: MessageSquare, group: "اصلی" },
  { id: "autoreply", icon: Sparkles, group: "ماژول" },
  { id: "commands", icon: Command, group: "ماژول" },
  { id: "schedule", icon: Timer, group: "ماژول" },
  { id: "notes", icon: NotebookPen, group: "ماژول" },
  { id: "filters", icon: Filter, group: "ماژول" },
  { id: "snippets", icon: Clock3, group: "ماژول" },
  { id: "profile", icon: UserRound, group: "اکانت" },
  { id: "activity", icon: Activity, group: "اکانت" },
  { id: "settings", icon: Settings, group: "اکانت" },
];

function NavList({ onPick }: { onPick?: () => void }) {
  const view = useSelfStore((s) => s.view);
  const setView = useSelfStore((s) => s.setView);
  const unread = useSelfStore((s) => s.chats.reduce((n, c) => n + c.unread, 0));
  let last = "";
  return (
    <nav className="flex flex-col gap-1 px-2">
      {NAV.map((item) => {
        const Icon = item.icon;
        const showGroup = item.group !== last;
        last = item.group;
        const active = view === item.id;
        return (
          <div key={item.id}>
            {showGroup ? (
              <p className="px-3 pb-1 pt-4 text-[11px] font-medium tracking-wide text-subtle">{item.group}</p>
            ) : null}
            <button
              type="button"
              onClick={() => {
                setView(item.id);
                onPick?.();
              }}
              className={cn(
                "flex h-11 w-full items-center gap-2 rounded-md px-3 text-sm transition-colors duration-150",
                active ? "bg-surface-2 text-fg" : "text-muted hover:bg-surface-2/70 hover:text-fg",
              )}
            >
              <Icon className="size-4 shrink-0" />
              <span className="flex-1 text-start">{VIEW_LABEL[item.id]}</span>
              {item.id === "chats" && unread > 0 ? (
                <span className="rounded-full bg-accent px-1.5 text-[10px] font-medium text-accent-fg">
                  {unread}
                </span>
              ) : null}
            </button>
          </div>
        );
      })}
    </nav>
  );
}

export function Shell({ children }: { children: ReactNode }) {
  const profile = useSelfStore((s) => s.profile)!;
  const afk = useSelfStore((s) => s.afk);
  const setAfk = useSelfStore((s) => s.setAfk);
  const view = useSelfStore((s) => s.view);
  const setView = useSelfStore((s) => s.setView);
  const activeChatId = useSelfStore((s) => s.activeChatId);
  const [menu, setMenu] = useState(false);
  const hideDock = view === "chats" && Boolean(activeChatId);

  return (
    <div className="flex h-dvh min-h-dvh overflow-hidden bg-bg text-fg">
      <aside className="sticky top-0 hidden h-dvh w-60 shrink-0 flex-col border-e border-line lg:flex">
        <div className="px-5 pb-2 pt-6">
          <p className="text-[10px] font-medium tracking-[0.22em] text-subtle">SELF COMMAND</p>
          <p className="font-display text-3xl italic leading-none">Nexa</p>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto pb-4">
          <NavList />
        </div>
        <div className="border-t border-line p-3">
          <div className="flex items-center gap-2 rounded-lg bg-surface p-2 shadow-[var(--shadow-border)]">
            <Avatar name={profile.name} hue={200} size="sm" />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{profile.name}</p>
              <p className="truncate text-[11px] text-muted" dir="ltr">
                @{profile.username}
              </p>
            </div>
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex h-14 items-center gap-2 border-b border-line bg-bg/90 px-3 backdrop-blur-sm lg:h-16 lg:px-6">
          <Sheet open={menu} onOpenChange={setMenu}>
            <Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setMenu(true)} aria-label="منو">
              <Menu className="size-5" />
            </Button>
            <SheetContent side="right">
              <div className="px-5 pb-2 pt-6">
                <p className="font-display text-2xl italic">Nexa</p>
              </div>
              <SheetClose asChild>
                <div className="min-h-0 flex-1 overflow-y-auto">
                  <NavList onPick={() => setMenu(false)} />
                </div>
              </SheetClose>
            </SheetContent>
          </Sheet>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium lg:hidden">{VIEW_LABEL[view]}</p>
            <div className="hidden items-center gap-2 lg:flex">
              <span className="relative inline-flex size-2">
                <span className="nexa-pulse absolute inset-0 rounded-full bg-ok" />
              </span>
              <span className="text-xs text-muted">نشست فعال</span>
              <Badge tone="muted">{profile.sessionId}</Badge>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="hidden text-xs text-muted sm:inline">افک</span>
            <Switch checked={afk.on} onCheckedChange={(v) => setAfk(v, afk.reason || "کمی بعد برمی‌گردم.")} />
          </div>
        </header>

        <main
          className={cn(
            "flex min-h-0 flex-1 flex-col overflow-y-auto px-3 pb-20 pt-5 lg:px-8 lg:pb-8",
            view === "chats" && "overflow-hidden pt-3 lg:pt-4",
            hideDock && "pb-3",
          )}
        >
          {children}
        </main>

        <nav className={cn("fixed inset-x-0 bottom-0 z-20 grid grid-cols-4 border-t border-line bg-bg/95 px-2 py-1 backdrop-blur-sm lg:hidden", hideDock && "hidden")}>
          {(
            [
              ["home", Home],
              ["chats", MessageSquare],
              ["commands", Command],
              ["settings", Settings],
            ] as const
          ).map(([id, Icon]) => (
            <button
              key={id}
              type="button"
              onClick={() => setView(id)}
              className={cn(
                "flex h-12 flex-col items-center justify-center gap-0.5 text-[11px]",
                view === id ? "text-fg" : "text-muted",
              )}
            >
              <Icon className="size-4" />
              {VIEW_LABEL[id]}
            </button>
          ))}
        </nav>
      </div>
    </div>
  );
}
