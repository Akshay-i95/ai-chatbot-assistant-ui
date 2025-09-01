"use client";

import { AssistantRuntimeProvider, AssistantCloud } from "@assistant-ui/react";
import { useAISDKRuntime } from "@assistant-ui/react-ai-sdk";
import { useChat } from "@ai-sdk/react";
import { Thread } from "@/components/assistant-ui/thread";
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/app-sidebar";
import { Separator } from "@/components/ui/separator";
import { Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator } from "@/components/ui/breadcrumb";
import { useEffect, useMemo } from "react";

// Configure backend URL - ensure it's properly defined
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5000';

export const Assistant = () => {
  // Set up the useChat hook from AI SDK
  const chat = useChat();

  // Use the AI SDK runtime adapter
  const runtime = useAISDKRuntime(chat);

  // Debug backend connections
  useEffect(() => {
    console.log("Environment Setup:", {
      backendUrl: BACKEND_URL,
    });
    
    // Add backend URL to window for components to access
    window.BACKEND_URL = BACKEND_URL;
  }, []);

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <SidebarProvider>
        <AppSidebar />
        <SidebarInset className="h-screen overflow-hidden">
          <header className="flex h-16 shrink-0 items-center gap-2 border-b px-4">
            <SidebarTrigger />
            <Separator orientation="vertical" className="mr-2 h-4" />
            <div className="flex items-center gap-2">
              <div className="px-3 py-1 bg-black text-white rounded-full text-sm font-medium shadow-md">
                Edify AI Assistant
              </div>
            </div>
          </header>
          <Thread />
        </SidebarInset>
      </SidebarProvider>
    </AssistantRuntimeProvider>
  );
};

// Add type declaration for window object
declare global {
  interface Window {
    BACKEND_URL?: string;
  }
}
