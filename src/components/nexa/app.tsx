import { useEffect, useLayoutEffect, useState } from "react";
import { useSelfStore } from "@/lib/store";
import { Shell } from "./shell";
import { HomeView } from "./home";
import { ChatsView } from "./chats";
import { ProfileView, ActivityView, SettingsView } from "./account";
import {
  AutoReplyView,
  CommandsView,
  ScheduleView,
  NotesView,
  FiltersView,
  SnippetsView,
} from "./ops";
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
    const finish = () => {
      if (!cancelled) {
        setHydrated();
        setReady(true);
      }
    };

    const persistApi = useSelfStore.persist;
    if (!persistApi) {
      finish();
      return;
    }

    const unsub = persistApi.onFinishHydration(finish);
    void Promise.resolve(persistApi.rehydrate()).finally(finish);
    if (persistApi.hasHydrated()) finish();

    const fallback = window.setTimeout(finish, 400);
    return () => {
      cancelled = true;
      unsub();
      window.clearTimeout(fallback);
    };
  }, [setHydrated]);

  useEffect(() => {
    if (!ready) return;

    tickClockBio();
    flushDueJobs();

    const timer = window.setInterval(() => {
      tickClockBio();
      flushDueJobs();
    }, 30_000);

    const demo = window.setInterval(() => {
      runLiveDemoTick();
    }, 20_000);

    return () => {
      window.clearInterval(timer);
      window.clearInterval(demo);
    };
  }, [ready, tickClockBio, flushDueJobs, runLiveDemoTick]);

  if (!ready || !hydrated) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-bg text-muted">
        در حال آماده‌سازی فضای Nexa…
      </div>
    );
  }

  if (!profile) return <Onboarding />;

  const content = (() => {
    switch (view) {
      case "home":
        return <HomeView />;
      case "chats":
        return <ChatsView />;
      case "autoreply":
        return <AutoReplyView />;
      case "commands":
        return <CommandsView />;
      case "schedule":
        return <ScheduleView />;
      case "notes":
        return <NotesView />;
      case "filters":
        return <FiltersView />;
      case "snippets":
        return <SnippetsView />;
      case "profile":
        return <ProfileView />;
      case "activity":
        return <ActivityView />;
      case "settings":
        return <SettingsView />;
      default:
        return <HomeView />;
    }
  })();

  return <Shell>{content}</Shell>;
}
