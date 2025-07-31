import {
  ActionBarPrimitive,
  BranchPickerPrimitive,
  ComposerPrimitive,
  MessagePrimitive,
  ThreadPrimitive,
} from "@assistant-ui/react";
import type { FC } from "react";
import {
  ArrowDownIcon,
  CheckIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  CopyIcon,
  PencilIcon,
  RefreshCwIcon,
  SendHorizontalIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useState, useEffect } from "react";

import { Button } from "@/components/ui/button";
import { MarkdownText } from "@/components/assistant-ui/markdown-text";
import { TooltipIconButton } from "@/components/assistant-ui/tooltip-icon-button";
import { ToolFallback } from "./tool-fallback";

// Add ChatGPT-style reasoning section styles
const thinkingStyles = `
  .reasoning-section {
    border: 1px solid #e5e5e5;
    border-radius: 6px;
    margin: 12px 0;
    overflow: hidden;
    background: #f7f7f7;
  }
  
  .reasoning-details {
    margin: 0;
  }
  
  .reasoning-details[open] {
    background: #ffffff;
  }
  
  .reasoning-summary {
    padding: 8px 12px;
    cursor: pointer;
    list-style: none;
    font-size: 13px;
    font-weight: 500;
    color: #374151;
    background: #f7f7f7;
    border: none;
    display: flex;
    align-items: center;
    gap: 6px;
    user-select: none;
    transition: background-color 0.15s ease;
  }
  
  .reasoning-summary:hover {
    background: #f0f0f0;
  }
  
  .reasoning-details[open] .reasoning-summary {
    background: #ffffff;
    border-bottom: 1px solid #e5e5e5;
  }
  
  .reasoning-summary::-webkit-details-marker {
    display: none;
  }
  
  .reasoning-content {
    padding: 8px 12px;
    font-size: 13px;
    line-height: 1.4;
    color: #374151;
    background: #ffffff;
    white-space: pre-wrap;
    margin: 0;
  }
  
  /* ChatGPT-style message container */
  .chatgpt-message {
    max-width: none !important;
    background: transparent !important;
    padding: 0 !important;
    margin: 0 !important;
    border-radius: 0 !important;
  }
  
  .chatgpt-response {
    font-size: 15px;
    line-height: 1.6;
    color: #374151;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  }
`;

// Function to clean response content
const cleanResponseContent = (content: string): string => {
  if (!content || typeof content !== 'string') return content;
  
  // Remove various source and reference patterns
  const patterns = [
    // Sources sections
    /\*\*📚\s*Sources?\s*&?\s*References?:?\*\*[\s\S]*?(?=\n\n|\n$|$)/gi,
    /\*\*Sources?\s*&?\s*References?:?\*\*[\s\S]*?(?=\n\n|\n$|$)/gi,
    /\*\*References?:?\*\*[\s\S]*?(?=\n\n|\n$|$)/gi,
    /\*\*Sources?:?\*\*[\s\S]*?(?=\n\n|\n$|$)/gi,
    
    // Document/chunk info
    /\*\*Chunks?\s*Retrieved:?\*\*[\s\S]*?(?=\n\n|\n$|$)/gi,
    /\*\*Document\s*Sources?:?\*\*[\s\S]*?(?=\n\n|\n$|$)/gi,
    /\*\*Retrieved\s*Documents?:?\*\*[\s\S]*?(?=\n\n|\n$|$)/gi,
    
    // Similarity scores
    /\*\*Similarity\s*Scores?:?\*\*[\s\S]*?(?=\n\n|\n$|$)/gi,
    /\(Score:?\s*[\d.]+\)/gi,
    /Score:?\s*[\d.]+/gi,
    
    // Technical metadata
    /\*\*Retrieval\s*Info:?\*\*[\s\S]*?(?=\n\n|\n$|$)/gi,
    /\*\*Source\s*Documents?:?\*\*[\s\S]*?(?=\n\n|\n$|$)/gi,
    
    // Any remaining bullet points with technical info
    /^[\s]*[-•*]\s*.*(?:score|chunk|document|retrieval).*$/gmi,
    
    // Clean up extra whitespace
    /\n\s*\n\s*\n+/g
  ];
  
  let cleaned = content;
  patterns.forEach(pattern => {
    cleaned = cleaned.replace(pattern, '');
  });
  
  // Final cleanup
  return cleaned
    .replace(/\n\s*\n\s*\n+/g, '\n\n') // Multiple newlines to double
    .replace(/^\s+|\s+$/g, '') // Trim start/end
    .trim();
};

// Clean content wrapper component
const CleanMessageContent: FC = () => {
  const [cleanedContent, setCleanedContent] = useState<string>('');
  
  useEffect(() => {
    // Use MutationObserver to watch for content changes
    const observer = new MutationObserver(() => {
      const messageElements = document.querySelectorAll('[data-message-content="true"]');
      messageElements.forEach((element) => {
        const originalText = element.textContent || '';
        const cleaned = cleanResponseContent(originalText);
        if (cleaned !== originalText && element.innerHTML) {
          element.innerHTML = element.innerHTML.replace(originalText, cleaned);
        }
      });
    });
    
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      characterData: true
    });
    
    return () => observer.disconnect();
  }, []);

  return (
    <MessagePrimitive.Content
      components={{ Text: MarkdownText, tools: { Fallback: ToolFallback } }}
    />
  );
};

export const Thread: FC = () => {
  // Inject thinking animation styles
  useEffect(() => {
    const styleId = 'thinking-styles';
    if (!document.getElementById(styleId)) {
      const style = document.createElement('style');
      style.id = styleId;
      style.textContent = thinkingStyles;
      document.head.appendChild(style);
    }
  }, []);

  return (
    <ThreadPrimitive.Root className="bg-background box-border flex h-[calc(100vh-4rem)] flex-col overflow-hidden">
      <ThreadPrimitive.Viewport className="flex h-full flex-col items-center overflow-y-auto scroll-smooth bg-inherit px-4 pt-8">
        <ThreadWelcome />

        <ThreadPrimitive.Messages
          components={{
            UserMessage: UserMessage,
            EditComposer: EditComposer,
            AssistantMessage: AssistantMessage,
          }}
        />

        <ThreadPrimitive.If empty={false}>
          <div className="min-h-8 flex-grow" />
        </ThreadPrimitive.If>

        <div className="sticky bottom-0 mt-3 flex w-full max-w-4xl flex-col items-center justify-end rounded-t-lg bg-inherit pb-4">
          <ThreadScrollToBottom />
          <Composer />
        </div>
      </ThreadPrimitive.Viewport>
    </ThreadPrimitive.Root>
  );
};

const ThreadScrollToBottom: FC = () => {
  return (
    <ThreadPrimitive.ScrollToBottom asChild>
      <TooltipIconButton
        tooltip="Scroll to bottom"
        variant="outline"
        className="absolute -top-8 rounded-full disabled:invisible"
      >
        <ArrowDownIcon />
      </TooltipIconButton>
    </ThreadPrimitive.ScrollToBottom>
  );
};

const ThreadWelcome: FC = () => {
  return (
    <ThreadPrimitive.Empty>
      <div className="flex w-full max-w-4xl flex-grow flex-col">
        <div className="flex w-full flex-grow flex-col items-center justify-center">
          <p className="mt-4 font-medium">How can I help you today?</p>
        </div>
        <ThreadWelcomeSuggestions />
      </div>
    </ThreadPrimitive.Empty>
  );
};

const ThreadWelcomeSuggestions: FC = () => {
  return (
    <div className="mt-3 flex w-full items-stretch justify-center gap-4">
      <ThreadPrimitive.Suggestion
        className="hover:bg-muted/80 flex max-w-sm grow basis-0 flex-col items-center justify-center rounded-lg border p-3 transition-colors ease-in"
        prompt="What are the key assessment strategies in modern education?"
        method="replace"
        autoSend
      >
        <span className="line-clamp-2 text-ellipsis text-sm font-semibold">
          What are the key assessment strategies in modern education?
        </span>
      </ThreadPrimitive.Suggestion>
      <ThreadPrimitive.Suggestion
        className="hover:bg-muted/80 flex max-w-sm grow basis-0 flex-col items-center justify-center rounded-lg border p-3 transition-colors ease-in"
        prompt="How can teachers implement formative assessment effectively?"
        method="replace"
        autoSend
      >
        <span className="line-clamp-2 text-ellipsis text-sm font-semibold">
          How can teachers implement formative assessment effectively?
        </span>
      </ThreadPrimitive.Suggestion>
    </div>
  );
};

const Composer: FC = () => {
  return (
    <ComposerPrimitive.Root className="focus-within:border-ring/20 flex w-full flex-wrap items-end rounded-lg border bg-inherit px-2.5 shadow-sm transition-colors ease-in">
      <ComposerPrimitive.Input
        rows={1}
        autoFocus
        placeholder="Write a message..."
        className="placeholder:text-muted-foreground max-h-40 flex-grow resize-none border-none bg-transparent px-2 py-4 text-sm outline-none focus:ring-0 disabled:cursor-not-allowed"
      />
      <ComposerAction />
    </ComposerPrimitive.Root>
  );
};

const ComposerAction: FC = () => {
  return (
    <>
      <ThreadPrimitive.If running={false}>
        <ComposerPrimitive.Send asChild>
          <TooltipIconButton
            tooltip="Send"
            variant="default"
            className="my-2.5 size-8 p-2 transition-opacity ease-in"
          >
            <SendHorizontalIcon />
          </TooltipIconButton>
        </ComposerPrimitive.Send>
      </ThreadPrimitive.If>
      <ThreadPrimitive.If running>
        <ComposerPrimitive.Cancel asChild>
          <TooltipIconButton
            tooltip="Cancel"
            variant="default"
            className="my-2.5 size-8 p-2 transition-opacity ease-in"
          >
            <CircleStopIcon />
          </TooltipIconButton>
        </ComposerPrimitive.Cancel>
      </ThreadPrimitive.If>
    </>
  );
};

const UserMessage: FC = () => {
  return (
    <MessagePrimitive.Root className="grid auto-rows-auto grid-cols-[auto_minmax(200px,1fr)] gap-y-2 w-full max-w-4xl py-4">
      <UserActionBar />
      
      <div className="bg-muted text-foreground max-w-[60%] break-words rounded-3xl px-5 py-2.5 col-start-2 row-start-2 justify-self-end mr-4">
        <MessagePrimitive.Content />
      </div>

      <BranchPicker className="col-span-full col-start-2 row-start-3 -ml-1 justify-end mr-4" />
    </MessagePrimitive.Root>
  );
};

const UserActionBar: FC = () => {
  return (
    <ActionBarPrimitive.Root
      hideWhenRunning
      autohide="not-last"
      className="flex flex-col items-end col-start-2 row-start-2 mr-1 mt-2.5"
    >
      <ActionBarPrimitive.Edit asChild>
        <TooltipIconButton tooltip="Edit">
          <PencilIcon />
        </TooltipIconButton>
      </ActionBarPrimitive.Edit>
    </ActionBarPrimitive.Root>
  );
};

const EditComposer: FC = () => {
  return (
    <ComposerPrimitive.Root className="bg-muted my-4 flex w-full max-w-4xl flex-col gap-2 rounded-xl">
      <ComposerPrimitive.Input className="text-foreground flex h-8 w-full resize-none bg-transparent p-4 pb-0 outline-none" />

      <div className="mx-3 mb-3 flex items-center justify-center gap-2 self-end">
        <ComposerPrimitive.Cancel asChild>
          <Button variant="ghost">Cancel</Button>
        </ComposerPrimitive.Cancel>
        <ComposerPrimitive.Send asChild>
          <Button>Send</Button>
        </ComposerPrimitive.Send>
      </div>
    </ComposerPrimitive.Root>
  );
};

const LoadingDots: FC = () => {
  return (
    <div className="flex space-x-1 items-center">
      <div className="w-1 h-1 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0s', animationDuration: '1.4s' }}></div>
      <div className="w-1 h-1 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s', animationDuration: '1.4s' }}></div>
      <div className="w-1 h-1 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s', animationDuration: '1.4s' }}></div>
    </div>
  );
};

const ThinkingSection: FC<{ isOpen: boolean; onToggle: () => void; content?: string }> = ({ 
  isOpen, 
  onToggle, 
  content = "Analyzing your question and searching through relevant educational resources..."
}) => {
  return (
    <div className="mb-3">
      <button
        onClick={onToggle}
        className="flex items-center gap-2 text-xs text-gray-500 hover:text-gray-700 transition-colors mb-2"
      >
        <span>Thinking</span>
        <LoadingDots />
      </button>
      
      {isOpen && (
        <div className="text-xs text-gray-600 bg-gray-50/30 rounded-lg p-3 mb-3 animate-in slide-in-from-top-1 duration-200">
          {content}
        </div>
      )}
    </div>
  );
};

const AssistantMessage: FC = () => {
  const [isThinkingOpen, setIsThinkingOpen] = useState(false);
  
  return (
    <MessagePrimitive.Root className="grid grid-cols-[minmax(200px,1fr)_auto] grid-rows-[auto_1fr] relative w-full max-w-4xl py-4">
      
      <div className="text-foreground max-w-[80%] break-words leading-7 col-start-1 row-start-1 my-1.5 justify-self-start ml-4">
        {/* Thinking Section */}
        <ThreadPrimitive.If running>
          <ThinkingSection 
            isOpen={isThinkingOpen} 
            onToggle={() => setIsThinkingOpen(!isThinkingOpen)}
          />
        </ThreadPrimitive.If>
        
        {/* Response Content */}
        <div className="bg-inherit rounded-2xl px-0 py-0 animate-in slide-in-from-bottom-2 duration-300">
          <CleanMessageContent />
        </div>
      </div>

      <AssistantActionBar />

      <BranchPicker className="col-start-1 row-start-2 -mr-2 ml-2 justify-start" />
    </MessagePrimitive.Root>
  );
};

const AssistantActionBar: FC = () => {
  return (
    <ActionBarPrimitive.Root
      hideWhenRunning
      autohide="not-last"
      autohideFloat="single-branch"
      className="text-muted-foreground flex gap-1 col-start-1 row-start-2 ml-4 data-[floating]:bg-background data-[floating]:absolute data-[floating]:rounded-md data-[floating]:border data-[floating]:p-1 data-[floating]:shadow-sm"
    >
      <ActionBarPrimitive.Copy asChild>
        <TooltipIconButton tooltip="Copy">
          <MessagePrimitive.If copied>
            <CheckIcon />
          </MessagePrimitive.If>
          <MessagePrimitive.If copied={false}>
            <CopyIcon />
          </MessagePrimitive.If>
        </TooltipIconButton>
      </ActionBarPrimitive.Copy>
      <ActionBarPrimitive.Reload asChild>
        <TooltipIconButton tooltip="Refresh">
          <RefreshCwIcon />
        </TooltipIconButton>
      </ActionBarPrimitive.Reload>
    </ActionBarPrimitive.Root>
  );
};

const BranchPicker: FC<BranchPickerPrimitive.Root.Props> = ({
  className,
  ...rest
}) => {
  return (
    <BranchPickerPrimitive.Root
      hideWhenSingleBranch
      className={cn(
        "text-muted-foreground inline-flex items-center text-xs",
        className
      )}
      {...rest}
    >
      <BranchPickerPrimitive.Previous asChild>
        <TooltipIconButton tooltip="Previous">
          <ChevronLeftIcon />
        </TooltipIconButton>
      </BranchPickerPrimitive.Previous>
      <span className="font-medium">
        <BranchPickerPrimitive.Number /> / <BranchPickerPrimitive.Count />
      </span>
      <BranchPickerPrimitive.Next asChild>
        <TooltipIconButton tooltip="Next">
          <ChevronRightIcon />
        </TooltipIconButton>
      </BranchPickerPrimitive.Next>
    </BranchPickerPrimitive.Root>
  );
};

const CircleStopIcon = () => {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 16 16"
      fill="currentColor"
      width="16"
      height="16"
    >
      <rect width="10" height="10" x="3" y="3" rx="2" />
    </svg>
  );
};
