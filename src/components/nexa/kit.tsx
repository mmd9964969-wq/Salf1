import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { avatarTone, displayInitials } from "@/lib/store";
import { Switch } from "@/components/ui/switch";

export function Panel({
  className,
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return (
    <section
      className={cn(
        "rounded-xl bg-surface p-2 shadow-[var(--shadow-border)]",
        className,
      )}
    >
      <div className="rounded-lg bg-surface">{children}</div>
    </section>
  );
}

export function Surface({
  className,
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return (
    <div className={cn("rounded-lg bg-surface p-4 shadow-[var(--shadow-border)]", className)}>
      {children}
    </div>
  );
}

export function Eyebrow({ children }: { children: ReactNode }) {
  return (
    <p className="text-[11px] font-medium tracking-[0.16em] text-subtle uppercase">
      {children}
    </p>
  );
}

export function PageTitle({
  kicker,
  title,
  hint,
}: {
  kicker: string;
  title: string;
  hint?: string;
}) {
  return (
    <header className="mb-6 flex flex-col gap-1">
      <Eyebrow>{kicker}</Eyebrow>
      <h1 className="font-display text-3xl font-medium tracking-tight text-fg italic">{title}</h1>
      {hint ? <p className="mt-1 max-w-xl text-sm text-muted">{hint}</p> : null}
    </header>
  );
}

export function Avatar({
  name,
  hue,
  size = "md",
}: {
  name: string;
  hue: number;
  size?: "sm" | "md" | "lg";
}) {
  const dim = size === "lg" ? "size-14 text-lg" : size === "sm" ? "size-9 text-xs" : "size-11 text-sm";
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-full font-medium text-accent-fg",
        dim,
      )}
      style={{ background: avatarTone(hue) }}
    >
      {displayInitials(name)}
    </span>
  );
}

export function ModuleRow({
  title,
  desc,
  checked,
  onCheckedChange,
}: {
  title: string;
  desc: string;
  checked: boolean;
  onCheckedChange: (v: boolean) => void;
}) {
  return (
    <label className="flex cursor-pointer items-center gap-3 rounded-md px-3 py-3 hover:bg-surface-2">
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-fg">{title}</p>
        <p className="text-xs text-muted">{desc}</p>
      </div>
      <Switch checked={checked} onCheckedChange={onCheckedChange} />
    </label>
  );
}

export function EmptyState({ title, desc }: { title: string; desc: string }) {
  return (
    <div className="px-4 py-12 text-center">
      <p className="text-sm font-medium text-fg">{title}</p>
      <p className="mt-1 text-sm text-muted">{desc}</p>
    </div>
  );
}

export function Stat({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="rounded-lg bg-surface p-4 shadow-[var(--shadow-border)]">
      <p className="text-xs text-muted">{label}</p>
      <p className="mt-2 font-display text-3xl italic tabular tracking-tight">{value}</p>
      {hint ? <p className="mt-1 text-xs text-subtle">{hint}</p> : null}
    </div>
  );
}

export function FieldStack({ children }: { children: ReactNode }) {
  return <div className="flex flex-col gap-2">{children}</div>;
}
