"use client";

import { Header }  from "@/components/Header";
import { Toaster } from "@/components/ui/toaster";

import { SettingsProvider } from "@/app/contexts/SettingsContext";
import { PostHogProvider } from "@/app/providers/PHProvider";

import { ChatProvider } from "../app/contexts/ChatContext";
import { SteelProvider } from "../app/contexts/SteelContext";

export function LayoutContent({ children }: { children: React.ReactNode }) {
  return (
    <PostHogProvider>
      <ChatProvider>
        <SettingsProvider>
          <SteelProvider>
            <Header />
            <div className="bg-[--gray-1] pt-14">{children}</div>
            <Toaster />
          </SteelProvider>
        </SettingsProvider>
      </ChatProvider>
    </PostHogProvider>
  );
}
