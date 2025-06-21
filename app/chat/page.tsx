"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useInView } from "react-intersection-observer";
import { CheckIcon } from "@radix-ui/react-icons";
import { useChat } from "ai/react";
import { Plus } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";

import { MarkdownText } from "@/components/markdown";
import { Browser } from "@/components/ui/Browser";
import { Button } from "@/components/ui/button";
import { ChatInput } from "@/components/ui/ChatInput";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { ToolInvocations } from "@/components/ui/tool";

import { useToast } from "@/hooks/use-toast";

import { useChatContext } from "@/app/contexts/ChatContext";
import { useSettings } from "@/app/contexts/SettingsContext";
import { useSteelContext } from "@/app/contexts/SteelContext";
import { apiClient } from "@/utils/api-client";
import { createClient } from "@/utils/supabase/client";

const UserMessage = React.memo(({ content }: { content: string }) => {
  const hasLineBreaks = content.includes("\n");
  const longestLine = Math.max(...content.split("\n").map(line => line.length));
  const isLongMessage = longestLine > 60;

  return (
    <div className="flex w-full justify-end">
      <div
        className={`
          inline-flex w-fit max-w-[85%] p-3 font-geist
          ${isLongMessage || hasLineBreaks ? "rounded-3xl" : "rounded-full px-4"}
          shrink-0 bg-[--blue-9]
        `}
      >
        <div
          className={`
            w-full overflow-hidden whitespace-pre-wrap 
            break-words font-geist text-base
            font-normal leading-normal text-[--gray-12]
          `}
        >
          <MarkdownText content={content} />
        </div>
      </div>
    </div>
  );
});

UserMessage.displayName = "UserMessage";

/**
 * ChatScrollAnchor:
 * - Used with Intersection Observer to track visibility of the bottom of the chat.
 * - If isAtBottom and trackVisibility are both true, it automatically scrolls
 *   the chat area to bottom whenever the anchor is out of view (new messages).
 */
const ChatScrollAnchor = React.memo(
  ({
    trackVisibility,
    isAtBottom,
    scrollAreaRef,
  }: {
    trackVisibility: boolean;
    isAtBottom: boolean;
    scrollAreaRef: React.RefObject<HTMLDivElement>;
  }) => {
    const { ref, inView } = useInView({
      trackVisibility,
      delay: 100,
    });

    useEffect(() => {
      if (isAtBottom && trackVisibility && !inView && scrollAreaRef.current?.children[0]) {
        const messagesContainer = scrollAreaRef.current.children[0];
        messagesContainer.scrollTop =
          messagesContainer.scrollHeight - messagesContainer.clientHeight;
      }
    }, [inView, isAtBottom, trackVisibility, scrollAreaRef]);

    return <div ref={ref} className="h-px w-full" />;
  }
);

ChatScrollAnchor.displayName = "ChatScrollAnchor";

// Create a completely isolated input container near the top of the file, after other component definitions
const ChatInputContainer = React.memo(
  ({
    initialValue = "",
    onSend,
    disabled,
    isLoading,
    onStop,
  }: {
    initialValue?: string;
    onSend: (messageText: string) => void;
    disabled: boolean;
    isLoading: boolean;
    onStop: () => void;
  }) => {
    console.log("[RENDER] ChatInputContainer rendering");
    const [inputValue, setInputValue] = useState(initialValue);

    // Keep local input state synchronized with initial value
    useEffect(() => {
      if (initialValue !== inputValue) {
        setInputValue(initialValue);
      }
    }, [initialValue]);

    const handleChange = useCallback((value: string) => {
      setInputValue(value);
    }, []);

    const handleSubmit = useCallback(
      (e: React.FormEvent, messageText: string, attachments: File[]) => {
        e.preventDefault();

        // Only send message if there's actual content
        if (messageText && messageText.trim()) {
          console.info(
            "[INPUT] Submitting message:",
            messageText.substring(0, 30) + (messageText.length > 30 ? "..." : "")
          );
          onSend(messageText);
          // Clear input immediately after sending
          setInputValue("");
        } else {
          console.info("[INPUT] Ignoring empty message submission");
        }
      },
      [onSend]
    );

    return (
      <ChatInput
        value={inputValue}
        onChange={handleChange}
        onSubmit={handleSubmit}
        disabled={disabled}
        isLoading={isLoading}
        onStop={onStop}
      />
    );
  }
);

ChatInputContainer.displayName = "ChatInputContainer";

// Memoize the Browser component to prevent unnecessary re-renders
const MemoizedBrowser = React.memo(Browser);
MemoizedBrowser.displayName = "MemoizedBrowser";

// Define proper types for messages and tool invocations
interface ToolInvocation {
  toolCallId: string;
  toolName: string;
  args: Record<string, unknown>;
  state: "call" | "result" | "partial-call";
  result?: unknown;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  toolInvocations?: ToolInvocation[];
  experimental_attachments?: Array<{ name: string; [key: string]: unknown }>;
}

// Fix the linter errors in MemoizedMessageList by adding types
const MemoizedMessageList = React.memo(
  ({
    messages,
    isCreatingSession,
    hasShownConnection,
    currentSession,
    onImageClick,
    isPaused,
    handleResume,
  }: {
    messages: ChatMessage[];
    isCreatingSession: boolean;
    hasShownConnection: boolean;
    currentSession: { id: string; debugUrl?: string };
    onImageClick: (src: string) => void;
    isPaused: boolean;
    handleResume: () => void;
  }) => {
    console.log("[RENDER] MemoizedMessageList rendering");

    return (
      <>
        {messages.map((message, index) => {
          // Group resume messages together - only render the most recent one
          // with the same content if they appear consecutively
          if (
            message.content === "▶️ AI control has been resumed." &&
            index > 0 &&
            messages[index - 1].content === "▶️ AI control has been resumed."
          ) {
            return null;
          }

          return (
            <div key={message.id || index} className="flex w-full max-w-full flex-col gap-2">
              {/* Force message content to respect container width */}
              <div className="w-full max-w-full">
                {message.role === "user" ? (
                  <>
                    <UserMessage content={message.content} />
                    {index === 0 && isCreatingSession && (
                      <div className="mx-auto mt-2 w-[85%] animate-pulse rounded-md border border-[--blue-3] bg-[--blue-2] px-4 py-2 font-geist text-sm text-[--blue-11]">
                        Connecting to Steel Browser Session...
                      </div>
                    )}
                    {index === 0 &&
                      hasShownConnection &&
                      !isCreatingSession &&
                      currentSession?.id && (
                        <div className="mx-auto mt-2 flex w-[85%] items-center gap-2 rounded-md border border-[--green-3] bg-[--green-2] px-4 py-2 font-geist text-sm text-[--green-11]">
                          <CheckIcon className="size-4" />
                          Steel Browser Session connected
                        </div>
                      )}
                  </>
                ) : (
                  <div className="flex w-full max-w-full flex-col gap-4 break-words text-base text-[--gray-12]">
                    {(() => {
                      const isSpecialMessage =
                        (message.content &&
                          (message.content.includes("*Memory*:") ||
                            message.content.includes("*Next Goal*:") ||
                            message.content.includes("*Previous Goal*:"))) ||
                        (message.toolInvocations && message.toolInvocations.length > 0);
                      const hasToolInvocations =
                        message.toolInvocations && message.toolInvocations.length > 0;
                      const isSpecial = isSpecialMessage || hasToolInvocations;

                      // Check for pause message in content or tool calls
                      const pauseToolCall = message.toolInvocations?.find(
                        (tool: ToolInvocation) => tool.toolName === "pause_execution"
                      );
                      const isPauseToolCall = hasToolInvocations && !!pauseToolCall;
                      const isPauseContentMessage =
                        message.content?.includes("⏸️ Pausing execution") ||
                        message.content?.includes("⏸️ You have taken control");
                      const isPauseMessage = isPauseToolCall || isPauseContentMessage;

                      // Get the pause reason from either source
                      let pauseReason = "";
                      if (isPauseToolCall && pauseToolCall) {
                        // Clean up the reason - sometimes it includes the "⏸️" prefix which causes duplication
                        const rawReason =
                          typeof pauseToolCall.args.reason === "string"
                            ? pauseToolCall.args.reason
                            : "Unknown reason";
                        pauseReason = rawReason.replace(/^⏸️\s*/, "");
                      } else if (isPauseContentMessage && message.content) {
                        if (message.content.includes("⏸️ Pausing execution:")) {
                          const parts = message.content.split("⏸️ Pausing execution: ");
                          pauseReason = parts[1]?.trim() || "Unknown reason";
                        } else if (message.content.includes("⏸️ You have taken control")) {
                          pauseReason = "You have taken control of the browser";
                        }
                      }

                      // This is a critical check - if it's a pause message, we need to render it
                      if (isPauseMessage) {
                        // Check if this is the most recent pause message
                        const isLatestPauseMessage = !messages.some((m, i) => {
                          if (i <= index) return false; // Only check messages after this one

                          // Check if there's a newer pause message
                          return (
                            m.content?.includes("⏸️ Pausing execution") ||
                            m.toolInvocations?.some(
                              (tool: ToolInvocation) => tool.toolName === "pause_execution"
                            )
                          );
                        });

                        // Check if the user has sent a message after this pause
                        const userSentMessageAfterPause = messages.some((m, i) => {
                          // Consider both cases:
                          // 1. A message comes after this one in the messages array
                          // 2. The isPaused state is false (meaning we've already resumed)
                          return (i > index && m.role === "user") || !isPaused;
                        });

                        // Only show buttons if this is the latest pause, no user message after it, and isPaused is true
                        const showButtons =
                          isLatestPauseMessage && !userSentMessageAfterPause && isPaused;

                        // Extract reason from the current message
                        let displayReason = "";

                        if (pauseToolCall) {
                          displayReason =
                            typeof pauseToolCall.args.reason === "string"
                              ? pauseToolCall.args.reason
                              : "Awaiting your confirmation";
                        } else if (message.content) {
                          if (message.content.includes("⏸️ Pausing execution:")) {
                            const parts = message.content.split("⏸️ Pausing execution:");
                            displayReason = parts[1]?.trim() || "Awaiting your confirmation";
                          } else if (message.content.includes("⏸️ You have taken control")) {
                            displayReason = "You have taken control of the browser";
                          } else {
                            displayReason = message.content.replace("⏸️ ", "").trim();
                          }
                        }

                        if (!displayReason) {
                          displayReason = "Awaiting your confirmation";
                        }

                        console.info("💬 Rendering pause message:", {
                          index,
                          isLatestPauseMessage,
                          userSentMessageAfterPause,
                          showButtons,
                          globalIsPaused: isPaused,
                          pauseReason:
                            pauseReason ||
                            message.content ||
                            (pauseToolCall?.args.reason as string),
                        });

                        return (
                          <div
                            className={`flex w-full max-w-full flex-col gap-4 ${!showButtons ? "opacity-80" : ""}`}
                          >
                            <div className="flex flex-col gap-4">
                              <div className="font-normal text-[--gray-12]">
                                <MarkdownText content={displayReason} />
                                {!showButtons && (
                                  <div className="mt-2 text-sm text-[--gray-10] italic">
                                    {isPaused
                                      ? "(Confirmation no longer needed)"
                                      : "(Action has been taken)"}
                                  </div>
                                )}
                              </div>
                              {showButtons && (
                                <div className="flex gap-3">
                                  <Button
                                    onClick={() => {
                                      console.info("🖱️ Keep Going button clicked");
                                      handleResume();
                                    }}
                                    variant="outline"
                                    className="rounded-full bg-[--gray-3] px-6 py-3 text-base font-medium text-[--gray-11] transition-colors hover:bg-[--gray-4]"
                                  >
                                    Keep Going
                                  </Button>
                                </div>
                              )}
                            </div>
                          </div>
                        );
                      }

                      // Find consecutive special messages
                      let specialMessagesGroup = [];
                      if (isSpecial) {
                        let i = index;
                        while (i < messages.length) {
                          const nextMessage = messages[i];
                          const isNextSpecial =
                            (nextMessage.content &&
                              (nextMessage.content.includes("*Memory*:") ||
                                nextMessage.content.includes("*Next Goal*:") ||
                                nextMessage.content.includes("*Previous Goal*:"))) ||
                            (nextMessage.toolInvocations && nextMessage.toolInvocations.length > 0);

                          if (!isNextSpecial) break;
                          specialMessagesGroup.push(nextMessage);
                          i++;
                        }
                      }

                      // Skip if this message is part of a group but not the first one
                      if (isSpecial && index > 0) {
                        const prevMessage = messages[index - 1];
                        const isPrevSpecial =
                          (prevMessage.content &&
                            (prevMessage.content.includes("*Memory*:") ||
                              prevMessage.content.includes("*Next Goal*:") ||
                              prevMessage.content.includes("*Previous Goal*:"))) ||
                          (prevMessage.toolInvocations && prevMessage.toolInvocations.length > 0);
                        if (isPrevSpecial) return null;
                      }

                      return isSpecial ? (
                        <div className="flex w-full max-w-full flex-col gap-2 rounded-[1.25rem] border border-[--gray-3] bg-[--gray-1] p-2">
                          <div className="flex flex-col gap-2">
                            {specialMessagesGroup.map((groupMessage, groupIndex) => (
                              <React.Fragment key={groupMessage.id}>
                                {groupMessage.content && (
                                  <div className="w-full">
                                    <MarkdownText content={groupMessage.content} />
                                  </div>
                                )}
                                {groupMessage.toolInvocations &&
                                  groupMessage.toolInvocations.length > 0 && (
                                    <div className="flex w-full flex-col gap-2">
                                      {groupMessage.toolInvocations
                                        .filter(tool => {
                                          // Filter out pause_execution tools
                                          if (tool.toolName === "pause_execution") {
                                            return false;
                                          }

                                          // Make sure print_call tools have a message
                                          if (
                                            tool.toolName === "print_call" &&
                                            (!tool.args || !tool.args.message)
                                          ) {
                                            return false;
                                          }

                                          return true;
                                        })
                                        .map((tool: any, toolIndex: number) => (
                                          <div
                                            key={toolIndex}
                                            className="flex w-full items-center justify-between rounded-2xl border border-[--gray-3] bg-[--gray-2] p-3"
                                          >
                                            <ToolInvocations
                                              toolInvocations={[tool]}
                                              onImageClick={onImageClick}
                                            />
                                          </div>
                                        ))}
                                    </div>
                                  )}
                              </React.Fragment>
                            ))}
                          </div>
                        </div>
                      ) : message.content ? (
                        <div className="w-full max-w-full whitespace-pre-wrap break-words">
                          <MarkdownText content={message.content} />
                        </div>
                      ) : null;
                    })()}
                  </div>
                )}
              </div>
              {message.experimental_attachments?.map((attachment: any, idx: number) => (
                <div
                  key={idx}
                  className="
                    mt-1
                    inline-flex
                    h-8 items-center
                    gap-2
                    rounded-full
                    border
                    border-[--gray-3]
                    bg-[--gray-2]
                    px-2
                  "
                >
                  <span className="font-geist text-sm font-normal leading-[18px] text-[--gray-11]">
                    {attachment.name}
                  </span>
                </div>
              ))}
            </div>
          );
        })}
      </>
    );
  }
);

MemoizedMessageList.displayName = "MemoizedMessageList";

// Create a custom hook to isolate chat state
function useChatState({
  currentSession,
  initialMessage,
  chatBodyConfig,
  toast,
}: {
  currentSession: any;
  initialMessage: string | null;
  chatBodyConfig: any;
  toast: any;
}) {
  // Get chat functionality from useChat
  const chatState = useChat({
    api: "/api/chat",
    id: currentSession?.id || undefined,
    maxSteps: 10,
    initialMessages: initialMessage
      ? [{ id: "1", role: "user", content: initialMessage }]
      : undefined,
    body: chatBodyConfig,
    onFinish: message => {
      console.log("[CHAT] Chat finished message:", message.id);
    },
    onError: error => {
      console.error("[CHAT] Chat error:", error);
      toast({
        title: "Error",
        description: error?.message || "An unexpected error occurred",
        className: "text-[var(--gray-12)] border border-[var(--red-11)] bg-[var(--red-2)] text-sm",
      });
    },
    onToolCall: toolCallEvent => {
      console.log("[CHAT] Tool call received:", JSON.stringify(toolCallEvent, null, 2));
      // We'll implement more reliable message updates after understanding the structure
    },
  });

  // Use an enhanced version of handleSubmit that logs better debugging info
  const enhancedHandleSubmit = useCallback(
    (e: React.FormEvent) => {
      console.info("[CHAT] Enhanced handleSubmit called with session:", currentSession?.id);
      chatState.handleSubmit(e);
    },
    [chatState, currentSession?.id]
  );

  return {
    ...chatState,
    handleSubmit: enhancedHandleSubmit,
  };
}

// Create a memoized component that holds the entire chat UI
interface ChatPageContentProps {
  messages: any[];
  isLoading: boolean;
  input: string;
  handleInputChange: any;
  handleSubmit: any;
  handleStop: () => void;
  reload: () => void;
  isCreatingSession: boolean;
  hasShownConnection: boolean;
  currentSession: any;
  isExpired: boolean;
  handleNewChat: () => void;
  handleImageClick: (src: string) => void;
  setMessages: any;
  isAtBottom: boolean;
  scrollAreaRef: React.RefObject<HTMLDivElement>;
  handleScroll: () => void;
  removeIncompleteToolCalls: () => void;
  stop: () => void;
  handleSend: (e: React.FormEvent, messageText: string, attachments: File[]) => void;
  isPaused: boolean;
  resumeLoading: boolean;
  handleResume: () => void;
  testId: string | null;
  onSubmitReport: () => void;
  reportSubmitted: boolean;
}

const ChatPageContent = React.memo(
  ({
    messages,
    isLoading,
    input,
    handleInputChange,
    handleSubmit,
    handleStop,
    reload,
    isCreatingSession,
    hasShownConnection,
    currentSession,
    isExpired,
    handleNewChat,
    handleImageClick,
    setMessages,
    isAtBottom,
    scrollAreaRef,
    handleScroll,
    removeIncompleteToolCalls,
    stop,
    handleSend,
    isPaused,
    resumeLoading,
    handleResume,
    testId,
    onSubmitReport,
    reportSubmitted,
  }: ChatPageContentProps) => {
    console.log("[RENDER] ChatPageContent rendering");

    // Determine if we should show the loading indicator
    const showLoadingIndicator = isLoading || resumeLoading;

    // State for image overlay dialog
    const [selectedImage, setSelectedImage] = useState<string | null>(null);

    // Handle image click for dialog
    const handleLocalImageClick = (src: string) => {
      setSelectedImage(src);
      handleImageClick(src);
    };

    return (
      <>
        <div className="flex h-[calc(100vh-3.5rem)] flex-col-reverse md:flex-row">
          {/* Left (chat) - Fluid responsive width */}
          <div
            className="
            flex h-[40vh] 
            w-full flex-col border-t border-[--gray-3]
            md:h-full md:w-[clamp(280px,30vw,460px)]
            md:border-r md:border-t-0
          "
          >
            {testId && (
              <div className="bg-blue-500/10 border-b border-blue-500/20 px-4 py-2 text-sm text-blue-600">
                <div className="flex items-center justify-between">
                  <span>Running test: {testId}</span>
                  {reportSubmitted && (
                    <span className="text-green-600 flex items-center">
                      <CheckIcon className="mr-1 h-4 w-4" /> Results saved
                    </span>
                  )}
                </div>
              </div>
            )}
            
            <div className="flex-1 overflow-hidden" ref={scrollAreaRef} onScroll={handleScroll}>
              <div
                className="scrollbar-gutter-stable scrollbar-thin flex size-full flex-col gap-4 overflow-y-auto overflow-x-hidden
                  p-4
                  [&::-webkit-scrollbar-thumb]:rounded-full
                  [&::-webkit-scrollbar-thumb]:border-4
                  [&::-webkit-scrollbar-thumb]:bg-[--gray-3]
                  [&::-webkit-scrollbar-thumb]:transition-colors
                  [&::-webkit-scrollbar-thumb]:hover:bg-[--gray-3]
                  [&::-webkit-scrollbar-track]:rounded-full
                  [&::-webkit-scrollbar-track]:bg-[--gray-1]
                  [&::-webkit-scrollbar]:w-1.5"
              >
                {/* Messages */}
                <MemoizedMessageList
                  messages={messages}
                  isCreatingSession={isCreatingSession}
                  hasShownConnection={hasShownConnection}
                  currentSession={currentSession}
                  onImageClick={handleLocalImageClick}
                  isPaused={isPaused}
                  handleResume={handleResume}
                />
                {showLoadingIndicator && (
                  <div className="flex items-center gap-2">
                    <div className="size-4 animate-spin rounded-full border-2 border-[--gray-12] border-t-transparent" />
                    {resumeLoading && (
                      <span className="text-sm text-[--gray-10]">
                        Waiting for agent to continue...
                      </span>
                    )}
                  </div>
                )}

                {/* Simplified scroll anchor */}
                <ChatScrollAnchor
                  scrollAreaRef={scrollAreaRef}
                  isAtBottom={isAtBottom}
                  trackVisibility={showLoadingIndicator}
                />
              </div>
            </div>

            {/* Chat input or Expired State */}
            <div className="border-t border-[--gray-3]" />
            <div className="min-h-44 flex-none p-4 drop-shadow-md">
              {isExpired ? (
                <div className="flex flex-col items-center gap-4">
                  <p className="text-sm font-medium text-[--gray-11]">
                    Your browser session has expired
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8 rounded-full border-[--gray-3] bg-[--gray-1] text-[--gray-11]"
                    onClick={handleNewChat}
                  >
                    <Plus className="size-4" />
                    <span className="px-1 font-geist">New Chat</span>
                  </Button>
                </div>
              ) : (
                <ChatInputContainer
                  initialValue={input}
                  onSend={messageText => {
                    const fakeEvent = { preventDefault: () => {} } as React.FormEvent;
                    handleSend(fakeEvent, messageText, []);
                  }}
                  disabled={showLoadingIndicator}
                  isLoading={showLoadingIndicator}
                  onStop={handleStop}
                />
              )}
            </div>
          </div>

          {/* Right (browser) - Keep more prominent */}
          <div
            className="
              h-[60vh] 
              flex-1 border-b
            h-[60vh] 
            flex-1 border-b
            border-[--gray-3] p-4 md:h-full 
            md:border-b-0
          "
          >
            <TimerDisplay isPaused={isPaused} />
          </div>
        </div>

        {/* Modal for expanded image */}
        <Dialog
          open={selectedImage !== null}
          onOpenChange={open => !open && setSelectedImage(null)}
        >
          <DialogContent className="max-w-[90vw] border border-[#282828] bg-[--gray-1] p-0">
            <div className="flex items-center justify-between border-b border-[#282828] px-4 py-2">
              <DialogTitle className="text-base font-medium text-[--gray-12]">
                Page preview sent to model
              </DialogTitle>
            </div>
            {selectedImage && (
              <div className="p flex items-center justify-center" style={{ height: "80vh" }}>
                <img
                  src={selectedImage}
                  alt="Preview"
                  className="max-h-full max-w-full object-contain"
                />
              </div>
            )}
          </DialogContent>
        </Dialog>
      </>
    );
  }
);

ChatPageContent.displayName = "ChatPageContent";

// Update the TimerDisplay component to be completely isolated
const TimerDisplay = React.memo(({ isPaused }: { isPaused: boolean }) => {
  console.log("[RENDER] TimerDisplay rendering");

  // No state, no store access here - completely isolated
  return <MemoizedBrowser isPaused={isPaused} />;
});

TimerDisplay.displayName = "TimerDisplay";

export default function ChatPage() {
  console.log("[RENDER] ChatPage is rendering");
  const { currentSettings, updateSettings } = useSettings();
  const { currentSession, createSession, isCreatingSession, isExpired } = useSteelContext();
  console.log("[DEBUG] ChatPage rendering");
  const { initialMessage, setInitialMessage } = useChatContext();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [hasShownConnection, setHasShownConnection] = useState(false);
  const router = useRouter();
  const searchParams = useSearchParams();
  const testId = searchParams.get('testId');
  const [chatResults, setChatResults] = useState<any[]>([]);
  const [reportSubmitted, setReportSubmitted] = useState(false);
  const sessionStartTime = useRef(new Date());
  const { toast } = useToast();
  const [selectedImage, setSelectedImage] = useState<string | null>(null);

  // Add API key modal state and handlers
  const [showApiKeyModal, setShowApiKeyModal] = useState(false);
  const pendingMessageRef = useRef<string>("");

  // Track whether user is at the bottom
  const [isAtBottom, setIsAtBottom] = useState<boolean>(false);
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  // After defining checkApiKey
  const [isPaused, setIsPaused] = useState(false);
  const [pauseReason, setPauseReason] = useState<string>("");
  const [resumeLoading, setResumeLoading] = useState(false);

  // Add a ref to track if a resume request is in progress
  const resumeRequestInProgress = useRef(false);

  // Add a ref for tracking the last resume timestamp
  const lastResumeTimestamp = useRef(0);

  // Add a ref to track processed messages for pause detection
  const processedPauseMessagesRef = useRef<Set<string>>(new Set());
  const lastResumeMessageIdRef = useRef<string | null>(null);

  // Effect to fetch and store user ID when component mounts
  useEffect(() => {
    const fetchAndStoreUserId = async () => {
      try {
        const supabase = createClient();
        const { data: { user } } = await supabase.auth.getUser();
        
        if (user?.id) {
          localStorage.setItem('user_id', user.id);
          console.info("👤 User ID stored in localStorage:", user.id);
        }
      } catch (error) {
        console.error("Error fetching user ID:", error);
      }
    };
    
    fetchAndStoreUserId();
  }, []);

  // Utility functions that need to be defined before they're used
  const checkApiKey = useCallback(() => {
    return true;
  }, []);

  // Helper function to check if a value is a setting config object
  const isSettingConfig = useCallback((value: any): boolean => {
    return value && typeof value === "object" && "type" in value && "default" in value;
  }, []);

  // Memoize chatBody config
  const chatBodyConfig = useMemo(
    () => {
      // Get the user ID from localStorage if available
      const userId = typeof window !== 'undefined' ? localStorage.getItem('user_id') : null;
      
      // Clean testId to ensure it's a valid UUID string format
      let cleanTestId: string | undefined = undefined;
      
      if (testId) {
        cleanTestId = testId.replace(/[^a-zA-Z0-9-]/g, '');
        
        // Make sure it's in the standard UUID format xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        // If it doesn't have hyphens but is 32 characters, format it properly
        if (cleanTestId.length === 32 && !cleanTestId.includes('-')) {
          cleanTestId = [
            cleanTestId.substring(0, 8),
            cleanTestId.substring(8, 12),
            cleanTestId.substring(12, 16),
            cleanTestId.substring(16, 20),
            cleanTestId.substring(20)
          ].join('-');
        }
      }
      
      return {
        session_id: currentSession?.id,
        agent_type: currentSettings?.selectedAgent,
        provider: currentSettings?.selectedProvider,
        api_key: currentSettings?.providerApiKeys?.[currentSettings?.selectedProvider || ""] || "",
        model_settings: {
          model_choice: currentSettings?.selectedModel,
          max_tokens: Number(currentSettings?.modelSettings.max_tokens),
          temperature: Number(currentSettings?.modelSettings.temperature),
          top_p: currentSettings?.modelSettings.top_p
            ? Number(currentSettings?.modelSettings.top_p)
            : undefined,
          top_k: currentSettings?.modelSettings.top_k
            ? Number(currentSettings?.modelSettings.top_k)
            : undefined,
          frequency_penalty: currentSettings?.modelSettings.frequency_penalty
            ? Number(currentSettings?.modelSettings.frequency_penalty)
            : undefined,
          presence_penalty: currentSettings?.modelSettings.presence_penalty
            ? Number(currentSettings?.modelSettings.presence_penalty)
            : undefined,
        },
        agent_settings: {
          ...Object.fromEntries(
            Object.entries(currentSettings?.agentSettings ?? {})
              .filter(([_, value]) => value !== undefined && !isSettingConfig(value))
              .map(([key, value]) => [key, typeof value === "string" ? value : Number(value)])
          ),
          // Add test_id and user_id as explicit fields
          test_id: cleanTestId || undefined,
          user_id: userId || undefined
        },
      };
    },
    [currentSession?.id, currentSettings, isSettingConfig, testId]
  );

  // Use the custom hook instead of directly using useChat
  const { messages, handleSubmit, isLoading, input, handleInputChange, setMessages, reload, stop } =
    useChatState({
      currentSession,
      initialMessage,
      chatBodyConfig,
      toast,
    });

  // Near the beginning of the ChatPage function
  const handleApiKeySubmit = useCallback(
    (key: string) => {
      const provider = currentSettings?.selectedProvider;
      if (!provider) return;

      const currentKeys = currentSettings?.providerApiKeys || {};
      updateSettings({
        ...currentSettings!,
        providerApiKeys: {
          ...currentKeys,
          [provider]: key,
        },
      });
      setShowApiKeyModal(false);

      if (pendingMessageRef.current) {
        setInitialMessage(pendingMessageRef.current);
        pendingMessageRef.current = "";
      }
    },
    [currentSettings, updateSettings, setInitialMessage]
  );

  const handleScroll = useCallback(() => {
    if (!scrollAreaRef.current) return;

    const { scrollTop, scrollHeight, clientHeight } = scrollAreaRef.current.children[0];
    const atBottom = scrollHeight - clientHeight <= scrollTop + 1;

    if (atBottom !== isAtBottom) {
      setIsAtBottom(atBottom);
    }
  }, [isAtBottom]);

  const handleImageClick = useCallback((imageSrc: string) => {
    setSelectedImage(imageSrc);
  }, []);

  // Keep the regular refreshMessages function for cases where we don't need duplicate checking
  const refreshMessages = useCallback(async () => {
    if (!currentSession?.id) return;

    try {
      console.info("🔄 Refreshing messages for session:", currentSession.id);

      // Use the reload function to fetch the latest messages
      await reload();

      // Basic deduplication of resume messages
      setMessages(prev => {
        // Find and handle consecutive resume messages
        let lastResumeIndex = -1;
        return prev.filter((message, index) => {
          const isResumeMessage =
            message.role === "assistant" && message.content === "▶️ AI control has been resumed.";

          if (isResumeMessage) {
            if (lastResumeIndex !== -1 && index === lastResumeIndex + 1) {
              // Skip consecutive resume messages
              return false;
            }
            lastResumeIndex = index;
          }

          return true;
        });
      });
    } catch (error) {
      console.error("❌ Error refreshing messages:", error);
    }
  }, [currentSession?.id, reload, setMessages]);

  // Enhanced handleSend with more logging
  async function handleSend(e: React.FormEvent, messageText: string, attachments: File[]) {
    console.info("📤 Handling message send:", {
      messageText,
      hasAttachments: attachments.length > 0,
      attachmentsCount: attachments.length,
      isFirstMessage: messages.length === 0,
      isSubmitting,
      hasApiKey: checkApiKey(),
      isPaused,
    });

    e.preventDefault();

    if (!checkApiKey()) {
      pendingMessageRef.current = messageText;
      setShowApiKeyModal(true);
      return;
    }

    setIsSubmitting(true);

    // If we're paused, we need to resume first
    if (isPaused) {
      console.info("⏸️ Message sent while paused, resuming first");

      // Save the message for later
      const savedMessage = messageText;

      // Clear the input immediately to prevent reappearing
      handleInputChange({ target: { value: "" } } as any);

      // Make a stable copy of the current messages for reference
      const currentMessages = [...messages];

      // Check if there are any pending pause messages that need to be displayed
      const hasPendingPauseMessages = currentMessages.some(
        m =>
          (m.role === "assistant" &&
            (m.content?.includes("⏸️") || m.content?.includes("CONFIRMATION REQUIRED:"))) ||
          m.toolInvocations?.some(tool => tool.toolName === "pause_execution")
      );

      if (hasPendingPauseMessages) {
        console.info("🔄 Found pending pause messages, ensuring they're displayed");
        // Force a UI update with the existing messages to make pause messages visible
        setMessages([...currentMessages]);
        // Give UI time to update
        await new Promise(resolve => setTimeout(resolve, 150));
      }

      // Resume the agent, which will also add a resume message
      await handleResume();

      // Add a delay to ensure the resume has been processed by the backend
      await new Promise(resolve => setTimeout(resolve, 800));

      // Turn off resume loading indicator since we'll now use the regular loading state
      setResumeLoading(false);

      try {
        // Get current messages after resume to maintain correct order
        const messagesAfterResume = [...messages];

        // Log messages for debugging
        console.info(
          "🔍 Messages after resume:",
          messagesAfterResume.map(m => ({
            role: m.role,
            content: m.content.substring(0, 30) + (m.content.length > 30 ? "..." : ""),
            id: m.id,
          }))
        );

        // Create a unique ID for this user message to help with debugging and deduplication
        const userMessageId = `user-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;

        // Add the user message to UI with proper type assertion and unique ID
        const userMessage = {
          id: userMessageId,
          role: "user" as const, // Use const assertion to fix the type error
          content: savedMessage,
        };

        console.info("📝 Adding user message with ID:", userMessageId);

        // Update the UI in one deterministic operation
        setMessages([...messagesAfterResume, userMessage]);

        // Now submit directly to the API if we have a session
        if (currentSession?.id) {
          console.info("📤 Submitting message to API after resume:", savedMessage);

          // Create a copy of messages that ensures the user message has the correct role
          const messagesToSend = [
            ...messagesAfterResume,
            {
              id: userMessageId,
              role: "user",
              content: savedMessage,
            },
          ];

          // Direct API call to send the message
          const response = await fetch(
            `/api/sessions/${currentSession.id}/resume`,
            {
              method: "POST",
            }
          );

          if (!response.ok) {
            throw new Error(`Failed to send message: ${response.statusText}`);
          }

          // Refresh messages after a longer delay to get the latest responses
          // This should allow enough time for the backend to process the message
          setTimeout(() => {
            console.info("🔄 Refreshing messages after resume + user message");
            // Use a custom refresh function that prevents duplicate user messages
            refreshMessagesWithDuplicateCheck(savedMessage);
          }, 1000); // Increase the delay to ensure proper message ordering
        }
      } catch (error) {
        console.error("Error sending message:", error);
        toast({
          title: "Error",
          description: "Failed to send your message",
          className: "border border-[--red-6] bg-[--red-3] text-[--red-11]",
        });
      }

      return;
    }

    // Normal flow when not paused
    // If we already have a session, use it regardless of message count
    if (currentSession?.id) {
      console.info("📤 Submitting message to existing chat session:", {
        messageText,
        sessionId: currentSession?.id,
        existingMessages: messages.length,
        wasPaused: isPaused,
      });

      // Ensure the input is cleared immediately to prevent flickering
      handleInputChange({ target: { value: "" } } as any);

      // Create a unique ID for this user message for better visibility in UI
      const userMessageId = `user-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;

      // Add the user message to UI first to ensure immediate feedback
      const userMessage = {
        id: userMessageId,
        role: "user" as const,
        content: messageText,
      };

      // Update messages array to include the new user message
      setMessages(prev => [...prev, userMessage]);

      // Submit message directly - this is the right path for 2nd turn messages
      handleSubmit(e);

      // Set a timeout to refresh messages in case the message doesn't appear
      setTimeout(() => {
        console.info("🔄 Scheduled refresh to ensure message appears");
        refreshMessagesWithDuplicateCheck(messageText);
      }, 1500);

      return;
    }

    // No existing session - this is a new conversation
    if (messages.length === 0) {
      console.info("📝 Setting initial message with context:", {
        messageText,
        hasAttachments: attachments.length > 0,
        attachmentsCount: attachments.length,
      });
      setInitialMessage(messageText);
      handleInputChange({ target: { value: "" } } as any);

      // Create a new session if needed
      if (!currentSession?.id) {
        console.info("🔄 Creating new session for initial message");
        await createSession();
        console.info("✅ New session created");
      }
    } else {
      // This case shouldn't normally happen (messages exist but no session)
      // but we'll handle it just in case
      console.info("📤 Submitting message to chat with no active session:", {
        messageText,
        existingMessages: messages.length,
      });
      handleSubmit(e);
    }
  }

  // Modify the useEffect that handles session creation
  useEffect(() => {
    const isNewSession = currentSession?.id && !hasShownConnection;
    if (isNewSession) {
      reload();
      setIsSubmitting(false);
      setInitialMessage(null);
      setHasShownConnection(true);
    }
  }, [currentSession?.id, hasShownConnection, reload, setInitialMessage]);

  // Enhanced removeIncompleteToolCalls with more detailed logging
  const removeIncompleteToolCalls = useCallback(() => {
    setMessages(prev => {
      const updatedMessages = prev
        .map(msg => {
          if (msg.role === "assistant" && Array.isArray(msg.toolInvocations)) {
            const filteredToolInvocations = msg.toolInvocations.filter(
              invocation => invocation.state === "result"
            );
            return {
              ...msg,
              toolInvocations: filteredToolInvocations,
            };
          }
          return msg;
        })
        .filter(msg => {
          if (
            msg.role === "assistant" &&
            !msg.content?.trim() &&
            (!msg.toolInvocations || msg.toolInvocations.length === 0)
          ) {
            return false;
          }
          return true;
        });

      return updatedMessages;
    });
  }, [setMessages]);

  const handleStop = useCallback(() => {
    stop();
    removeIncompleteToolCalls();
  }, [stop, removeIncompleteToolCalls]);

  // Reuse the same handler from NavBar for consistency
  const handleNewChat = useCallback(() => {
    router.push("/");
  }, [router]);

  // Effect for scrolling to bottom when isLoading changes
  useEffect(() => {
    if (isLoading && scrollAreaRef.current?.children[0]) {
      const messagesContainer = scrollAreaRef.current.children[0];
      messagesContainer.scrollTop = messagesContainer.scrollHeight - messagesContainer.clientHeight;
      setIsAtBottom(true);
    }
  }, [isLoading]);

  // Effect to handle initial message on mount
  useEffect(() => {
    async function handleInitialMessage() {
      if (initialMessage && !currentSession?.id && !isSubmitting) {
        setIsSubmitting(true);
        // Create new session
        await createSession();
      }
    }

    handleInitialMessage();
  }, [initialMessage, currentSession?.id, isSubmitting, createSession]);

  // Add effect to handle session expiration
  useEffect(() => {
    if (isExpired) {
      stop();
      removeIncompleteToolCalls();
    }
  }, [isExpired, stop, removeIncompleteToolCalls]);

  // Restore the watch for pause messages effect
  useEffect(() => {
    if (messages.length > 0) {
      const lastMessage = messages[messages.length - 1];

      // Skip if we've already processed this message
      if (lastMessage.id && processedPauseMessagesRef.current.has(lastMessage.id)) {
        return;
      }

      // Skip pause detection if we've recently resumed
      if (lastResumeMessageIdRef.current) {
        const resumeIndex = messages.findIndex(m => m.id === lastResumeMessageIdRef.current);
        const lastMessageIndex = messages.length - 1;

        // If the last resume message is after or the same as this message, skip
        if (resumeIndex >= 0 && resumeIndex >= lastMessageIndex - 1) {
          return;
        }
      }

      console.info("🔍 Checking message for pause:", {
        id: lastMessage.id,
        content: lastMessage.content?.substring(0, 30),
        role: lastMessage.role,
        isPausedState: isPaused,
        currentReason: pauseReason,
        messagesLength: messages.length,
        alreadyProcessed: lastMessage.id
          ? processedPauseMessagesRef.current.has(lastMessage.id)
          : false,
      });

      // Log all tool calls for debugging
      if (lastMessage.toolInvocations?.length) {
        console.info(
          "🛠️ All tool calls in last message:",
          lastMessage.toolInvocations.map(tool => ({
            toolName: tool.toolName,
            args: tool.args,
            state: tool.state,
          }))
        );
      }

      // Check if this is a pause message
      if (lastMessage.role === "assistant") {
        // Check for pause tool call
        let foundPause = false;
        let pauseReasonText = "";

        if (lastMessage.toolInvocations?.length) {
          const pauseToolCall = lastMessage.toolInvocations.find(
            tool => tool.toolName === "pause_execution"
          );

          if (pauseToolCall) {
            foundPause = true;
            // If reason starts with emoji, keep it (improved extraction)
            pauseReasonText =
              typeof pauseToolCall.args.reason === "string"
                ? pauseToolCall.args.reason
                : "Unknown reason";

            console.info("⏸️ Found pause tool call:", {
              toolCall: pauseToolCall,
              extractedReason: pauseReasonText,
            });
          }
        }
        // Also check for pause message in content
        else if (lastMessage.content && lastMessage.content.includes("⏸️ Pausing execution")) {
          foundPause = true;
          if (lastMessage.content.includes("⏸️ Pausing execution:")) {
            const parts = lastMessage.content.split("⏸️ Pausing execution:");
            pauseReasonText = parts[1]?.trim() || "Unknown reason";
          } else {
            pauseReasonText = lastMessage.content.trim();
          }
          console.info("⏸️ Found pause message in content:", {
            extractedReason: pauseReasonText,
          });
        } else if (lastMessage.content && lastMessage.content.includes("CONFIRMATION REQUIRED:")) {
          // Also check for confirmation required messages
          foundPause = true;
          pauseReasonText = lastMessage.content;
          console.info("⏸️ Found confirmation required message:", {
            content: lastMessage.content,
          });
        } else if (
          lastMessage.content &&
          lastMessage.content.includes("⏸️ You have taken control")
        ) {
          foundPause = true;
          pauseReasonText = "You have taken control of the browser";
          console.info("⏸️ Found manual pause message:", {
            content: lastMessage.content,
          });
        }

        if (foundPause) {
          // Mark this message as processed
          if (lastMessage.id) {
            processedPauseMessagesRef.current.add(lastMessage.id);
          }

          setIsPaused(true);
          setPauseReason(pauseReasonText);

          // Stop loading state when paused
          if (isLoading) {
            stop();
            removeIncompleteToolCalls();
          }

          // Don't add an extra message - use the existing tool call message instead
          console.info("⏸️ Using existing pause message from tool call");
        }
        // Check if this is a resume message
        else if (lastMessage.content === "▶️ AI control has been resumed.") {
          // Mark as processed and remember as the last resume message
          if (lastMessage.id) {
            processedPauseMessagesRef.current.add(lastMessage.id);
            lastResumeMessageIdRef.current = lastMessage.id;
          }

          // Reset pause state
          setIsPaused(false);
          setPauseReason("");
          console.info("▶️ Resume message detected, reset pause state");
        }
      }
    }
  }, [messages, isLoading, stop, removeIncompleteToolCalls]);

  // Restore the browser paused effect
  useEffect(() => {
    const handleBrowserPaused = (event: CustomEvent) => {
      console.info("🖐️ Browser was manually paused by user:", event.detail);
      setIsPaused(true);
      setPauseReason("You have taken control of the browser");

      // Make sure loading state is cleared if active
      if (isLoading) {
        stop();
        removeIncompleteToolCalls();
      }

      // Add a message to the chat to indicate manual pause
      setMessages(messages => [
        ...messages,
        {
          id: `manual-pause-${Date.now()}`,
          role: "assistant",
          content: "⏸️ You have taken control of the browser.",
        },
      ]);
    };

    // Add browser-paused event listener
    window.addEventListener("browser-paused", handleBrowserPaused as EventListener);

    return () => {
      window.removeEventListener("browser-paused", handleBrowserPaused as EventListener);
    };
  }, [isLoading, stop, removeIncompleteToolCalls, setMessages]);

  // The specialized version with duplicate checking
  const refreshMessagesWithDuplicateCheck = useCallback(
    async (userMessage?: string) => {
      if (!currentSession?.id) return;

      try {
        console.info("🔄 Refreshing messages with duplicate check:", currentSession.id);
        console.info("📊 Current message count before refresh:", messages.length);

        if (userMessage) {
          console.info(
            "🔍 Looking for message:",
            userMessage.substring(0, 30) + (userMessage.length > 30 ? "..." : "")
          );
          const hasUserMessage = messages.some(m => m.content === userMessage && m.role === "user");
          console.info("✓ User message already present:", hasUserMessage);
        }

        // Use the reload function to fetch the latest messages
        await reload();
        console.info("📊 Messages loaded after reload:", messages.length);

        // Clean up and deduplicate messages
        setMessages(prev => {
          // Make a copy of the messages for processing
          let messages = [...prev];

          // Log current message state for debugging
          console.info(
            "🔍 Messages before cleanup:",
            messages.map(m => ({
              role: m.role,
              content: m.content.substring(0, 30) + (m.content.length > 30 ? "..." : ""),
              id: m.id,
            }))
          );

          // 1. Handle duplicate resume messages
          let resumeIndices: number[] = [];
          messages.forEach((m, i) => {
            if (m.role === "assistant" && m.content === "▶️ AI control has been resumed.") {
              resumeIndices.push(i);
            }
          });

          // Keep only the first resume message in each consecutive group
          if (resumeIndices.length > 1) {
            console.info(`🔄 Found ${resumeIndices.length} resume messages, deduplicating...`);
            let lastIndex = -2;
            const indicesToRemove: number[] = [];

            for (const idx of resumeIndices) {
              if (idx === lastIndex + 1) {
                // This is a consecutive resume message, mark for removal
                indicesToRemove.push(idx);
              }
              lastIndex = idx;
            }

            // Remove marked messages
            messages = messages.filter((_, i) => !indicesToRemove.includes(i));
          }

          // 2. Prevent duplicate user messages and fix any messages with the wrong role
          if (userMessage) {
            // Find all messages with this content regardless of role
            const messagesWithSameContent = messages.filter(m => m.content === userMessage);

            console.info(
              `🔍 Found ${messagesWithSameContent.length} messages with content "${userMessage.substring(0, 30)}..."`
            );

            if (messagesWithSameContent.length > 0) {
              // Check if any of them have the wrong role (assistant instead of user)
              const wrongRoleMessages = messagesWithSameContent.filter(m => m.role === "assistant");

              if (wrongRoleMessages.length > 0) {
                console.info(
                  `⚠️ Found ${wrongRoleMessages.length} messages with wrong role (assistant instead of user)`
                );

                // Fix roles: ensure the latest message with this content has role "user"
                let foundUserMessage = false;

                // First pass: check if we already have a proper user message
                for (const m of messagesWithSameContent) {
                  if (m.role === "user") {
                    foundUserMessage = true;
                    break;
                  }
                }

                // Second pass: if no user message exists, convert the latest one
                if (!foundUserMessage && wrongRoleMessages.length > 0) {
                  const latestWrongMessage = wrongRoleMessages[wrongRoleMessages.length - 1];
                  const index = messages.findIndex(m => m.id === latestWrongMessage.id);

                  if (index !== -1) {
                    console.info(
                      `🔧 Converting message at index ${index} from assistant to user role`
                    );
                    messages[index] = {
                      ...messages[index],
                      role: "user",
                      id: `user-${Date.now()}-fixed`,
                    };
                  }
                }
              }

              // Now handle duplicates - keep only one user message with this content
              let foundUserMessage = false;
              messages = messages.filter(m => {
                if (m.content === userMessage) {
                  if (m.role === "user") {
                    if (!foundUserMessage) {
                      foundUserMessage = true;
                      return true;
                    }
                    return false; // Remove duplicate user messages
                  }
                }
                return true;
              });
            } else {
              // If no messages with this content exist yet, we might need to add it
              console.info(
                `ℹ️ No messages found with content "${userMessage.substring(0, 30)}..."`
              );
            }
          }

          // Log final state after cleanup
          console.info(
            "🔍 Messages after cleanup:",
            messages.map(m => ({
              role: m.role,
              content: m.content.substring(0, 30) + (m.content.length > 30 ? "..." : ""),
              id: m.id,
            }))
          );

          return messages;
        });
      } catch (error) {
        console.error("❌ Error refreshing messages:", error);
      }
    },
    [currentSession?.id, reload, setMessages]
  );

  // Update the handleResume function to clear processed messages on resume
  const handleResume = useCallback(
    async (fromEvent = false) => {
      if (!currentSession?.id) {
        return;
      }

      // Prevent duplicate resume calls
      const now = Date.now();
      const timeSinceLastResume = now - lastResumeTimestamp.current;

      // If less than 3 seconds since last resume, ignore this request
      if (timeSinceLastResume < 3000) {
        console.warn(
          `🔒 Ignoring duplicate resume request (${timeSinceLastResume}ms since last resume)`
        );
        return;
      }

      // Check if a resume request is already in progress
      if (resumeRequestInProgress.current || resumeLoading) {
        console.warn("🔒 Resume request already in progress, ignoring duplicate request");
        return;
      }

      try {
        // Update the last resume timestamp
        lastResumeTimestamp.current = now;

        // Set the lock and update UI state
        resumeRequestInProgress.current = true;
        setResumeLoading(true);

        // Update UI state to show we're not paused - do this first for consistency
        setIsPaused(false);
        setPauseReason("");

        console.info("▶️ Resuming session:", currentSession.id);

        // Get a stable copy of current messages before adding resume message
        const currentMessages = [...messages];

        // Check if the last message is already a resume message
        const lastMessage =
          currentMessages.length > 0 ? currentMessages[currentMessages.length - 1] : null;
        const isLastMessageResume =
          lastMessage && lastMessage.content === "▶️ AI control has been resumed.";

        // Only add a resume message if the last message isn't already one
        if (!isLastMessageResume) {
          const resumeMessage = {
            id: `resume-${Date.now()}`,
            role: "assistant" as const, // Use const assertion to fix the type error
            content: "▶️ AI control has been resumed.",
          };

          // Remember the resume message ID to prevent re-processing pause messages
          lastResumeMessageIdRef.current = resumeMessage.id;

          // Update messages in one operation to avoid flicker
          setMessages([...currentMessages, resumeMessage]);
        }

        // If this resume call was triggered directly, notify the browser component
        if (!fromEvent) {
          console.info("🔄 Dispatching browser-resumed event from direct button click");
          window.dispatchEvent(
            new CustomEvent("browser-resumed", {
              detail: { sessionId: currentSession.id },
            })
          );
        }

        // Make API call to resume
        console.info("🔄 Sending resume request for session:", currentSession.id);
        const response = await fetch(
          `/api/sessions/${currentSession.id}/resume`,
          {
            method: "POST",
          }
        );

        if (!response.ok) {
          const errorText = await response.text();
          console.error("❌ Resume API call failed:", {
            status: response.status,
            statusText: response.statusText,
            errorText,
          });
          throw new Error("Failed to resume execution");
        }

        // Success notification
        toast({
          title: "Resumed",
          description: "Execution resumed",
          className: "border border-[--green-6] bg-[--green-3] text-[--green-11]",
        });

        // Add a delayed refresh to get updated messages
        setTimeout(() => {
          refreshMessages();

          // Release the lock after refresh is triggered
          setTimeout(() => {
            resumeRequestInProgress.current = false;
            // Always turn off resumeLoading after a successful resume
            setResumeLoading(false);
          }, 500);
        }, 1500);
      } catch (error) {
        console.error("❌ Error resuming execution:", error);

        // Reset state on error
        setIsPaused(true);
        setPauseReason("Failed to resume. Try again.");
        setResumeLoading(false);
        resumeRequestInProgress.current = false;

        toast({
          title: "Error",
          description: "Failed to resume execution",
          className: "border border-[--red-6] bg-[--red-3] text-[--red-11]",
        });
      }
    },
    [currentSession?.id, messages, toast, resumeLoading, setMessages, refreshMessages]
  );

  // Add browser-resumed event listener after handleResume is defined
  useEffect(() => {
    const handleBrowserResumed = (event: CustomEvent) => {
      console.info("🖐️ Browser was manually resumed by user:", event.detail);

      // Call the handleResume function with fromEvent=true to indicate this came from Browser
      handleResume(true);
    };

    // Add browser-resumed event listener
    window.addEventListener("browser-resumed", handleBrowserResumed as EventListener);

    return () => {
      window.removeEventListener("browser-resumed", handleBrowserResumed as EventListener);
    };
  }, [handleResume]);

  // Add effect to turn off resumeLoading when agent responds
  useEffect(() => {
    // If we were showing loading (isLoading=true) and then loading stops (isLoading=false)
    // and resumeLoading is still true, it means we should turn off resumeLoading
    if (!isLoading && resumeLoading) {
      console.info("🔄 Agent has responded, turning off resumeLoading");

      // Brief delay to make sure any UI updates from the response are rendered first
      setTimeout(() => {
        resumeRequestInProgress.current = false;
        setResumeLoading(false);
      }, 300);
    }
  }, [isLoading, resumeLoading]);

  // Add safety check to ensure messages have correct roles
  useEffect(() => {
    // Skip empty messages array
    if (!messages.length) return;

    // Check if any recent user messages were incorrectly relayed as assistant messages
    const lastFewMessages = messages.slice(-5); // Check only the last 5 messages

    let needsFix = false;
    const knownUserTexts = new Map<string, number>(); // Track known user messages by content

    // First pass: identify user messages
    lastFewMessages.forEach((message, index) => {
      if (message.role === "user") {
        knownUserTexts.set(message.content, index);
      }
    });

    // Second pass: check if any assistant messages contain exact user message content
    lastFewMessages.forEach((message, index) => {
      if (
        message.role === "assistant" &&
        knownUserTexts.has(message.content) &&
        // Don't flag resume messages
        message.content !== "▶️ AI control has been resumed." &&
        !message.content.startsWith("⏸️") &&
        !message.content.includes("CONFIRMATION REQUIRED:")
      ) {
        needsFix = true;
        console.warn(
          `⚠️ Found likely user message with incorrect role (assistant): "${message.content.substring(0, 30)}..."`
        );
      }
    });

    // If issues found, run the message sanitizer
    if (needsFix) {
      console.info("🔧 Fixing message roles");
      setMessages(prev => {
        return prev.map(message => {
          // If this is an assistant message but matches a known user message content
          if (
            message.role === "assistant" &&
            knownUserTexts.has(message.content) &&
            message.content !== "▶️ AI control has been resumed." &&
            !message.content.startsWith("⏸️") &&
            !message.content.includes("CONFIRMATION REQUIRED:")
          ) {
            // Fix its role
            return {
              ...message,
              role: "user" as const,
              id: `user-${Date.now()}-fixed-${Math.random().toString(36).substring(2, 7)}`,
            };
          }
          return message;
        });
      });
    }
  }, [messages]);

  // Helper function to extract performance report from messages
  const extractPerformanceReport = (messages: any[]) => {
    console.log("🔍 Searching for performance report in", messages.length, "messages");

    let performanceReport: string | null = null;

    // Prioritize finding the specific HTML report structure
    for (const msg of messages.slice().reverse()) { // Check recent messages first
      if (msg.role === 'assistant' && typeof msg.content === 'string') {
        // Look for the distinct HTML wrapper used in display_performance_report/force_display_report
        if (msg.content.includes('<div class="report-container">') || // Check for class used in force_display_report
            msg.content.includes('🚀 PERFORMANCE REPORT 🚀') || // Check for title used in display_performance_report
            msg.content.includes('<div style="padding:20px; background:#f5f5f5;') // Check for inline style
           ) {
          console.log("✅ Found HTML performance report in message content (Priority 1)");
          performanceReport = msg.content;
          break; // Found the best version
        }
      }
    }

    // If HTML report not found, fall back to text markers and tool results
    if (!performanceReport) {
      console.log("ℹ️ HTML report not found, checking text markers and tool results...");
      for (const msg of messages.slice().reverse()) { // Check recent messages first
        // Check content of messages for text markers
        if (!performanceReport && msg.content && typeof msg.content === 'string') {
           if (msg.content.includes('==== FULL PERFORMANCE REPORT ====') ||
               msg.content.includes('📊 Page Performance Metrics') ||
               msg.content.includes('⏱️ Timing Metrics') ||
               msg.content.includes('PERFORMANCE METRICS REPORT')) {
            console.log("✅ Found text-based performance report in message content (Priority 2)");
            performanceReport = msg.content;
            // Don't break yet, check tools in case they have a more complete version
          }
        }

        // Check for tool invocations with performance data
        if (msg.toolInvocations && Array.isArray(msg.toolInvocations)) {
          for (const tool of msg.toolInvocations) {
            if (['get_session_summary', 'generate_performance_report', 'show_performance_metrics',
                 'display_performance_report', 'get_latest_report', 'show_complete_performance_report', 'done'].includes(tool.toolName)) {

              // Check tool result (most likely place)
              if (tool.result && typeof tool.result === 'string' &&
                  (tool.result.includes('📊') || tool.result.includes('Performance') || tool.result.includes('Metrics') || tool.result.includes('🚀'))) {
                console.log(`✅ Found report in tool.result for ${tool.toolName} (Priority 3)`);
                performanceReport = tool.result; // Overwrite text version if tool result is found
                break; // Found a good candidate from tools
              }
              // Less likely: Check tool args (e.g., the 'done' tool might have it in args)
              else if (tool.toolName === 'done' && tool.args && typeof tool.args.text === 'string' &&
                       (tool.args.text.includes('📊') || tool.args.text.includes('Performance') || tool.args.text.includes('Metrics') || tool.args.text.includes('🚀'))) {
                 console.log(`✅ Found report in tool.args.text for 'done' tool (Priority 4)`);
                 performanceReport = tool.args.text;
                 break;
              }
            }
          }
          if (performanceReport && (performanceReport.includes('📊') || performanceReport.includes('🚀'))) break; // Break outer loop if report found in tools
        }
      }
    }

    // Final check: If still nothing, look for any message containing the performance emoji as a last resort
    if (!performanceReport) {
        console.log("ℹ️ No specific report found yet, doing a final check for '📊' emoji...");
        for (const msg of messages.slice().reverse()) {
            if (msg.role === 'assistant' && typeof msg.content === 'string' && msg.content.includes('📊')) {
                console.log("⚠️ Found message with '📊' emoji, using as fallback report (Priority 5)");
                performanceReport = msg.content;
                break;
            }
        }
    }

    if (performanceReport) {
      console.log("📊 Final extracted performance report preview:",
                   performanceReport.substring(0, 150) + (performanceReport.length > 150 ? "..." : ""));
    } else {
      console.warn("⚠️ Could not find any performance report in messages.");
    }

    return performanceReport;
  };

  // Function to submit report to backend
  const submitReport = useCallback(async () => {
    if (!testId || reportSubmitted) {
      console.log("🚫 Report submission skipped (no testId or already submitted).");
      return;
    }
    
    try {
      console.info("📊 Attempting to submit report for test:", testId);
      
      // First, ensure we have the latest messages from the chat
      console.log("Refreshing messages to ensure we have the latest data");
      try {
        await refreshMessages();
      } catch (refreshError) {
        console.warn("Failed to refresh messages, continuing with current messages:", refreshError);
      }
      
      // Get current user
      const supabase = createClient();
      const { data: { user } } = await supabase.auth.getUser();
      
      if (!user) {
        console.error("No user found when trying to submit report");
        toast({
          title: "Authentication Required",
          description: "Please sign in to submit test results",
          className: "border border-[--yellow-6] bg-[--yellow-3] text-[--yellow-11]",
        });
        return;
      }

      // Verify that the test belongs to the authenticated user
      const { data: testData, error: testError } = await supabase
        .from("tests")
        .select("id")
        .eq("id", testId)
        .eq("user_id", user.id)
        .single();
      
      if (testError || !testData) {
        console.error("Test verification error:", testError);
        toast({
          title: "Permission Error",
          description: "This test does not belong to your account",
          className: "border border-[--red-6] bg-[--red-3] text-[--red-11]",
        });
        return;
      }
      
      console.info("✅ Test verification successful for user:", user.id);

      // Extract performance report using our enhanced function
      const performanceReport = extractPerformanceReport(messages);
      
      // Format and clean messages
      const formatMessages = (messages: any[]) => {
        return messages
          .filter(msg => {
            // Skip messages with empty content
            if (!msg.content || !msg.content.trim()) return false;
            
            // Skip special system messages that shouldn't be in the report
            const isSystemMessage = 
              msg.role === 'assistant' && 
              (msg.content.includes('▶️ AI control has been resumed') || 
               msg.content.includes('⏸️ Pausing execution'));
               
            return !isSystemMessage;
          })
          .map(msg => ({
            role: msg.role,
            content: msg.content.trim(),
            timestamp: new Date().toISOString()
          }));
      };
      
      // Format and clean messages
      const formattedResults = formatMessages(messages);
      
      // Add the extracted report to the results with clear markers
      if (performanceReport) {
        formattedResults.push({
          role: "system",
          content: `[PERFORMANCE_REPORT_START]\n${performanceReport}\n[PERFORMANCE_REPORT_END]`,
          timestamp: new Date().toISOString()
        });
        console.log("✅ Successfully added performance report to results payload.");
        console.log("📊 Report Preview (first 200 chars):", performanceReport.substring(0, 200));
      } else {
        // If no performance report was found, check if there's a message with performance-related content
        console.warn("⚠️ No performance report found in messages, looking for fallback content...");
        const possibleReport = messages.find(msg => 
          msg.content && 
          typeof msg.content === 'string' && 
          (msg.content.includes('Performance') || 
           msg.content.includes('Metrics') || 
           msg.content.includes('⏱️') || 
           msg.content.includes('📊'))
        );
        
        if (possibleReport) {
          console.log("🔍 No explicit performance report found, but found message with performance content");
          formattedResults.push({
            role: "system",
            content: "[POSSIBLE_PERFORMANCE_REPORT]\n" + possibleReport.content,
            timestamp: new Date().toISOString()
          });
        } else {
          console.warn("⚠️ No performance report or related content found for inclusion.");
          // Add a basic fallback placeholder
          formattedResults.push({
            role: "system",
            content: "[PERFORMANCE_REPORT_MISSING]\nNo performance report was generated during this test session.",
            timestamp: new Date().toISOString()
          });
        }
      }
      
      // Don't submit if there are no results
      if (formattedResults.length === 0) {
        console.warn("No valid results to submit");
        toast({
          title: "Cannot Submit Report",
          description: "No valid messages found to include in report",
          className: "border border-[--yellow-6] bg-[--yellow-3] text-[--yellow-11]",
        });
        return;
      }
      
      setChatResults(formattedResults);
      
      // Calculate session duration in seconds
      const now = new Date();
      const durationInSeconds = Math.floor((now.getTime() - sessionStartTime.current.getTime()) / 1000);

      // Format test ID as a proper UUID
      let formattedTestId = testId;
      
      // Remove any non-UUID characters
      formattedTestId = formattedTestId.replace(/[^a-zA-Z0-9-]/g, '');
      
      // If it's a UUID without dashes but with the right length, format it correctly
      if (formattedTestId.length === 32 && !formattedTestId.includes('-')) {
        formattedTestId = `${formattedTestId.slice(0, 8)}-${formattedTestId.slice(8, 12)}-${formattedTestId.slice(12, 16)}-${formattedTestId.slice(16, 20)}-${formattedTestId.slice(20)}`;
      }
      
      console.log("Using formatted test ID for report:", formattedTestId);
      
      console.log("📦 Preparing to save report data:", {
        test_id: formattedTestId,
        results_count: formattedResults.length,
        includes_report: !!performanceReport,
        duration: durationInSeconds
      });

      // Format the request in the expected structure
      const reportData = {
        test_id: formattedTestId,
        results: formattedResults,
        completed_at: now.toISOString(),
        duration: durationInSeconds,
        user_id: user.id  // Explicitly set user_id
      };
      
      console.log("Report data ready, contains", formattedResults.length, "messages");

      // Save the report directly to Supabase instead of using the API client
      const { data, error } = await supabase
        .from("reports")
        .insert([reportData])
        .select();
        
      if (error) {
        console.error("Error saving report to Supabase:", error);
        throw new Error(`Failed to save report: ${error.message}`);
      }
      
      console.log("✅ Report saved successfully via Supabase:", data);
      setReportSubmitted(true);
      
      toast({
        title: "Report Submitted",
        description: "Test results have been saved successfully",
        className: "border border-[--green-6] bg-[--green-3] text-[--green-11]",
      });
      
    } catch (error: any) {
      console.error("❌ Error during report submission process:", error);
      
      // Try to extract more specific error information
      let errorMessage = "Failed to submit report results";
      
      if (error?.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      } else if (error?.message) {
        errorMessage = error.message;
      }
      
      toast({
        title: "Error",
        description: errorMessage,
        className: "border border-[--red-6] bg-[--red-3] text-[--red-11]",
      });
    }
  }, [testId, reportSubmitted, messages, toast, refreshMessages]);

  // Effect to save report when chat is considered complete
  useEffect(() => {
    // Check if chat has meaningful content and if we haven't submitted a report yet
    if (
      testId && 
      !reportSubmitted && 
      !isLoading && 
      messages.length > 1 && // At least a user message and a response
      !isPaused // Not currently paused
    ) {
      // Check if the last message indicates completion or contains a report
      const lastMessage = messages[messages.length - 1];
      const isLikelyComplete = lastMessage?.role === 'assistant' &&
                               (lastMessage.content?.includes('✅') || // Task completed message
                                lastMessage.content?.includes('PERFORMANCE REPORT') || // Contains report
                                lastMessage.content?.includes('📊')); // Contains report emoji

      if (isLikelyComplete) {
          console.log("✅ Chat appears complete, scheduling report submission...");
          // Submit report after a slightly longer delay
          const timer = setTimeout(() => {
            // Double-check conditions before submitting
            if (testId && !reportSubmitted && !isLoading && !isPaused) {
                 console.log("⏱️ Submitting report after delay.");
                 submitReport();
            } else {
                 console.log("🚫 Report submission cancelled (state changed during delay).");
            }
          }, 7000); // 7 second delay after chat appears complete

          return () => clearTimeout(timer);
      } else {
          console.log("⏳ Chat not yet considered complete for automatic report submission.");
      }
    }
  }, [testId, reportSubmitted, isLoading, messages, isPaused, submitReport]);

  // Before returning ChatPageContent, add a button to manually submit report if needed
  const chatPageContentProps = {
    messages,
    isLoading,
    input,
    handleInputChange,
    handleSubmit,
    handleStop,
    reload,
    isCreatingSession,
    hasShownConnection,
    currentSession,
    isExpired,
    handleNewChat,
    handleImageClick,
    setMessages,
    isAtBottom,
    scrollAreaRef,
    handleScroll,
    removeIncompleteToolCalls,
    stop,
    handleSend,
    isPaused,
    resumeLoading,
    handleResume,
    testId,
    onSubmitReport: submitReport,
    reportSubmitted,
  };

  return (
    <>
      <ChatPageContent {...chatPageContentProps} />
      {testId && !reportSubmitted && !isLoading && messages.length > 1 && (
        <div className="fixed bottom-4 right-4 z-50">
          <Button 
            onClick={submitReport}
            className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white shadow-lg"
            title="Manually save the test results including the performance report"
          >
            Save Test Results
          </Button>
        </div>
      )}
    </>
  );
}
