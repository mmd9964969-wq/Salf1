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
  return <div className="salf-shell">
    <aside className="salf-sidebar"><div className="salf-sidebar-brand"><div className="salf-sidebar-mark">S<span>1</span></div><div><strong>SALF<span>1</span></strong><small>ACCOUNT CONTROL</small></div></div><div className="salf-sidebar-status"><span/> سیستم فعال <b>LIVE</b></div><div className="salf-sidebar-scroll"><NavList/></div><div className="salf-sidebar-user"><Avatar name={profile.name} hue={200} size="sm"/><div><strong>{profile.name}</strong><span dir="ltr">@{profile.username}</span></div><Settings className="size-4"/></div></aside>
    <div className="salf-workspace"><header className="salf-topbar"><div className="salf-mobile-menu"><Sheet open={menu} onOpenChange={setMenu}><Button variant="ghost" size="icon" onClick={()=>setMenu(true)} aria-label="منو"><Menu className="size-5"/></Button><SheetContent side="right"><div className="p-5"><div className="salf-sidebar-brand"><div className="salf-sidebar-mark">S<span>1</span></div><div><strong>SALF<span>1</span></strong><small>ACCOUNT CONTROL</small></div></div></div><SheetClose asChild><div className="min-h-0 flex-1 overflow-y-auto"><NavList onPick={()=>setMenu(false)}/></div></SheetClose></SheetContent></Sheet></div><div className="salf-topbar-title"><span className="salf-topbar-dot"/><div><strong>{VIEW_LABEL[view]}</strong><small>CONTROL CENTER / SALF1</small></div></div><div className="salf-topbar-actions"><div className="salf-session"><span>SESSION</span><b dir="ltr">{profile.sessionId}</b></div><div className="salf-afk"><span>AFK</span><Switch checked={afk.on} onCheckedChange={(v)=>setAfk(v,afk.reason||"کمی بعد برمی‌گردم.")}/></div><Avatar name={profile.name} hue={200} size="sm"/></div></header>
    <main className={cn("salf-main",view==="chats"&&"salf-main-chat",hideDock&&"salf-main-chat-active")}>{children}</main>
    <nav className={cn("salf-mobile-dock",hideDock&&"hidden")}>{([["home",Home],["chats",MessageSquare],["commands",Command],["settings",Settings]] as const).map(([id,Icon])=><button key={id} type="button" onClick={()=>setView(id)} className={view===id?"active":""}><Icon className="size-4"/><span>{VIEW_LABEL[id]}</span></button>)}</nav></div>
  </div>;
}