import { createFileRoute } from "@tanstack/react-router";
import { NexaApp } from "@/components/nexa/app";

export const Route = createFileRoute("/")({ component: Home });

function Home() {
  return <NexaApp />;
}
