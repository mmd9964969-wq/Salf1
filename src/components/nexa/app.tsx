import { useEffect, useLayoutEffect, useState } from "react";
import { useSelfStore } from "@/lib/store";
import { Shell } from "./shell";
import { ChatsView } from "./chats";
import { ProfileView, ActivityView, SettingsView } from "./account";
import { AutoReplyView, CommandsView, ScheduleView, NotesView, FiltersView, SnippetsView } from "./ops";
import { Onboarding } from "./onboarding";

export function NexaApp() {
  const hydrated = useSelfStore((s) => s.hydrated);
  const profile = useSelfStore((s) => s.profile);
  const view = useSelfStore((s) => s.view);
  const setHydrated = useSelfStore((s) => s.setHydrated);
  const tickClockBio = useSelfStore((s) => s.tickClockBio);
  const flushDueJobs = useSelfStore((s) => s.flushDueJobs);
  const runLiveDemoTick = useSelfStore((s) => s.runLiveDemoTick);
  const [ready, setReady] = useState(false);

  useLayoutEffect(() => {
    let cancelled = false;
    const finish = () => { if (!cancelled) { setHydrated(); setReady(true); } };
    const persistApi = useSelfStore.persist;
    if (!persistApi) { finish(); return; }
    const unsub = persistApi.onFinishHydration(finish);
    try { void Promise.resolve(persistApi.rehydrate()).finally(finish); } catch { finish(); }
    if (persistApi.hasHydrated()) finish();
    const fallback = window.setTimeout(finish, 700);
    return () => { cancelled = true; unsub(); window.clearTimeout(fallback); };
  }, [setHydrated]);

  useEffect(() => {
    if (!ready) return;
    tickClockBio();
    flushDueJobs();
    const timer = window.setInterval(() => { tickClockBio(); flushDueJobs(); }, 30_000);
    const demo = window.setInterval(() => { runLiveDemoTick(); }, 20_000);
    return () => { window.clearInterval(timer); window.clearInterval(demo); };
  }, [ready, tickClockBio, flushDueJobs, runLiveDemoTick]);

  if (!ready || !hydrated) {
    return <div className="flex min-h-dvh items-center justify-center bg-bg text-muted">در حال آماده‌سازی قلمرو سلف…</div>;
  }

  // The legacy control center is intentionally removed from the active route.
  // Authenticated users now enter the new Panthera realm foundation.
  if (!profile) return <Onboarding />;
  return <Onboarding />;

  // Reserved for the next dashboard phase.
  // The old Shell/control-center route must not be mounted again.
  void view;
  void Shell;
  void ChatsView;
  void ProfileView;
  void ActivityView;
  void SettingsView;
  void AutoReplyView;
  void CommandsView;
  void ScheduleView;
  void NotesView;
  void FiltersView;
  void SnippetsView;
}
