import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function Badge({
  className,
  tone = "muted",
  children,
}: {
  className?: string;
  tone?: "muted" | "ok" | "warn" | "danger" | "accent";
  children: ReactNode;
}) {
  const tones = {
    muted: "text-muted bg-surface-2",
    ok: "text-ok bg-ok/10",
    warn: "text-warn bg-warn/10",
    danger: "text-danger bg-danger/10",
    accent: "text-accent-fg bg-accent",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium tracking-wide",
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}
