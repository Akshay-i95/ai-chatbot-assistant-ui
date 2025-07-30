"use client";

import { AssistantRuntimeProvider, AssistantCloud } from "@assistant-ui/react";
import { useChatRuntime } from "@assistant-ui/react-ai-sdk";
import { Thread } from "@/components/assistant-ui/thread";
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/app-sidebar";
import { Separator } from "@/components/ui/separator";
import { Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator } from "@/components/ui/breadcrumb";
import { useEffect, useMemo } from "react";

export const Assistant = () => {
  // Configure the cloud service
  const cloud = useMemo(() => {
    if (
      process.env.NEXT_PUBLIC_ASSISTANT_BASE_URL && 
      process.env.NEXT_PUBLIC_ASSISTANT_API_KEY && 
      process.env.NEXT_PUBLIC_ASSISTANT_WORKSPACE_ID
    ) {
      return new AssistantCloud({
        baseUrl: process.env.NEXT_PUBLIC_ASSISTANT_BASE_URL,
        apiKey: process.env.NEXT_PUBLIC_ASSISTANT_API_KEY,
        workspaceId: process.env.NEXT_PUBLIC_ASSISTANT_WORKSPACE_ID,
        userId: "default-user", // Use a default user ID
      });
    }
    return undefined;
  }, []);

  const runtime = useChatRuntime({
    api: "/api/chat",
    cloud: cloud,
  });

  // Debug cloud connection
  useEffect(() => {
    console.log("Cloud Config:", {
      baseUrl: process.env.NEXT_PUBLIC_ASSISTANT_BASE_URL,
      hasApiKey: !!process.env.NEXT_PUBLIC_ASSISTANT_API_KEY,
      workspaceId: process.env.NEXT_PUBLIC_ASSISTANT_WORKSPACE_ID,
      cloudConfigured: !!cloud,
    });
  }, [cloud]);

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
