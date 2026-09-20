import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { cn } from "@/lib/utils";

export const Sheet = DialogPrimitive.Root;
export const SheetTrigger = DialogPrimitive.Trigger;
export const SheetClose = DialogPrimitive.Close;

export function SheetContent({
  className,
  children,
  side = "right",
}: {
  className?: string;
  children: React.ReactNode;
  side?: "right" | "left";
}) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-bg/70 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=open]:fade-in-0 data-[state=closed]:fade-out-0" />
      <DialogPrimitive.Content
        className={cn(
          "fixed inset-y-0 z-50 flex w-72 max-w-[88vw] flex-col bg-surface shadow-[var(--shadow-float),var(--shadow-border)] outline-none data-[state=open]:animate-in data-[state=closed]:animate-out",
          side === "right"
            ? "end-0 data-[state=open]:slide-in-from-right data-[state=closed]:slide-out-to-right"
            : "start-0 data-[state=open]:slide-in-from-left data-[state=closed]:slide-out-to-left",
          className,
        )}
      >
        <DialogPrimitive.Title className="sr-only">منو</DialogPrimitive.Title>
        {children}
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}
