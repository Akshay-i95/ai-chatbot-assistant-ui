export const runtime = "edge";
export const maxDuration = 30;

export async function POST(req: Request) {
  try {
    const { messages } = await req.json();
    
    // Extract the latest user message
    const userMessage = messages[messages.length - 1];
    if (!userMessage || userMessage.role !== 'user') {
      return new Response('Invalid message format', { status: 400 });
    }

    // Extract text content from the message (handle both string and array formats)
    let messageContent: string;
    if (typeof userMessage.content === 'string') {
      messageContent = userMessage.content;
    } else if (Array.isArray(userMessage.content)) {
      // Handle OpenAI format with content array
      const textPart = userMessage.content.find((part: any) => part.type === 'text');
      messageContent = textPart?.text || '';
    } else {
      messageContent = String(userMessage.content);
    }

    if (!messageContent.trim()) {
      return new Response('Empty message content', { status: 400 });
    }

    // Get backend URL from environment variables
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || process.env.BACKEND_URL || 'https://ai-chatbot-assistant-ui-exgbfhbl4am4yrjopzgt8a.streamlit.app';
    
    // Streamlit backend uses a different API structure - direct chat API
    // Convert messages to the format expected by Streamlit backend
    const streamlitMessages = messages.map((msg: any) => {
      let content = '';
      if (typeof msg.content === 'string') {
        content = msg.content;
      } else if (Array.isArray(msg.content)) {
        const textPart = msg.content.find((part: any) => part.type === 'text');
        content = textPart?.text || '';
      }
      
      return {
        role: msg.role,
        content: content
      };
    });
    
    console.log(`Sending ${streamlitMessages.length} messages to Streamlit backend`);

    // Send message directly to Streamlit backend API
    const response = await fetch(`${backendUrl}/?api=chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        messages: streamlitMessages
      }),
    });

    if (!response.ok) {
      throw new Error(`Backend responded with status: ${response.status}`);
    }

    const data = await response.json();
    
    // Handle Streamlit backend response format
    let aiResponse, reasoning, sources, confidence, isFollowUp, followUpContext;
    
    if (data.error) {
      // Handle error response from Streamlit
      aiResponse = data.ai_message?.content || 'I apologize, but I encountered an error processing your request.';
      reasoning = data.ai_message?.reasoning || '';
      sources = [];
      confidence = 0;
      isFollowUp = false;
      followUpContext = null;
    } else {
      // Handle successful response from Streamlit
      aiResponse = data.ai_message.content;
      reasoning = data.ai_message.reasoning || '';
      
      const metadata = data.ai_message.metadata || {};
      sources = metadata.sources || [];
      confidence = metadata.confidence || 0;
      isFollowUp = metadata.is_follow_up || false;
      followUpContext = metadata.follow_up_context || null;
    }
    
    // Log reasoning data for debugging
    console.log(`🧠 Backend reasoning data:`, {
      direct_reasoning: reasoning ? reasoning.substring(0, 100) + '...' : 'NONE',
      final_reasoning: reasoning ? reasoning.substring(0, 100) + '...' : 'NONE',
      reasoning_length: reasoning?.length || 0,
      sources_count: sources.length,
      confidence: confidence
    });
    
    if (reasoning) {
      console.log(`🧠 Full reasoning content: ${reasoning}`);
    } else {
      console.log(`❌ No reasoning content found in backend response`);
    }

    // Create AI SDK compatible streaming response with structured content
    const encoder = new TextEncoder();
    
    const stream = new ReadableStream({
      async start(controller) {
        try {
          // Helper function to safely encode and send chunks
          const sendChunk = async (text: string, delay: number = 30) => {
            if (controller.desiredSize === null) return; // Controller is closed
            
            // Properly escape the text for JSON - handle all cases safely
            const escapedText = JSON.stringify(text).slice(1, -1); // Use JSON.stringify and remove outer quotes
            
            const chunk = `0:"${escapedText}"\n`;
            controller.enqueue(encoder.encode(chunk));
            
            if (delay > 0) {
              await new Promise(resolve => setTimeout(resolve, delay));
            }
          };
          
          // 1. Add follow-up indicator if this is a follow-up query
          if (isFollowUp && followUpContext) {
            await sendChunk('🔗 **Follow-up Response:**\n\n', 100);
            
            if (followUpContext.previous_topic) {
              await sendChunk(`*Building on our previous discussion about ${followUpContext.previous_topic.substring(0, 50)}...*\n\n`, 50);
            }
          }
          
          // 2. Add reasoning section first with ChatGPT-style collapsible dropdown
          if (reasoning?.trim()) {
            console.log('🧠 Adding reasoning to response, length:', reasoning.length, 'characters');
            
            // Create a ChatGPT-style collapsible reasoning section
            await sendChunk('\n\n---\n\n', 50);
            
            const reasoningHtml = `
<style>
  .reasoning-summary {
    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
    padding: 16px 20px;
    cursor: pointer;
    font-weight: 500;
    font-size: 15px;
    color: #1a1a1a;
    display: flex;
    align-items: center;
    gap: 12px;
    user-select: none;
    border: none;
    outline: none;
    transition: all 0.2s ease;
    position: relative;
  }
  .reasoning-summary:hover {
    background: linear-gradient(135deg, #f1f3f4 0%, #e0e3e6 100%);
  }
  .reasoning-chevron {
    color: #6b7280;
    transition: transform 0.2s ease;
    transform: rotate(0deg);
  }
  .reasoning-details[open] .reasoning-chevron {
    transform: rotate(180deg);
  }
</style>
<details class="reasoning-details" style="
  margin: 20px 0;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 12px;
  overflow: hidden;
  background: #ffffff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
">
  <summary class="reasoning-summary">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: #10a37f; flex-shrink: 0;">
      <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
    </svg>
    <span style="flex: 1;">Reasoning</span>
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" class="reasoning-chevron">
      <polyline points="6,9 12,15 18,9"/>
    </svg>
  </summary>
  <div style="
    padding: 24px;
    background: #ffffff;
    border-top: 1px solid rgba(0, 0, 0, 0.06);
    line-height: 1.6;
    color: #374151;
  ">
    <div style="
      background: #f9fafb;
      padding: 20px;
      border-radius: 8px;
      border: 1px solid rgba(0, 0, 0, 0.05);
      position: relative;
    ">
      <div style="
        position: absolute;
        top: 0;
        left: 0;
        width: 4px;
        height: 100%;
        background: linear-gradient(to bottom, #10a37f, #0d8f6b);
        border-radius: 2px 0 0 2px;
      "></div>
      <div style="
        font-size: 14px;
        line-height: 1.7;
        color: #1f2937;
        padding-left: 16px;
        white-space: pre-wrap;
      ">${reasoning.replace(/\n/g, '<br>')}</div>
    </div>
    <div style="
      margin-top: 16px;
      padding: 12px 16px;
      background: rgba(16, 163, 127, 0.05);
      border: 1px solid rgba(16, 163, 127, 0.2);
      border-radius: 8px;
      font-size: 13px;
      color: #0d8f6b;
      display: flex;
      align-items: center;
      gap: 8px;
    ">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <path d="m9,12 2,2 4,-4"/>
      </svg>
      <span>This reasoning was generated by our AI to explain the thought process behind the response.</span>
    </div>
  </div>
</details>

<style>
details[open] summary svg:last-child {
  transform: rotate(180deg) !important;
}
details summary::-webkit-details-marker {
  display: none;
}
details summary::marker {
  content: "";
}
</style>`;
            
            await sendChunk(reasoningHtml, 30);
            await sendChunk('\n\n---\n\n', 50);
          }
          
          // 3. Stream the main AI response (the actual answer)
          const words = aiResponse.split(' ');
          for (let i = 0; i < words.length; i++) {
            if (controller.desiredSize === null) break; // Controller is closed
            
            const word = words[i] + (i < words.length - 1 ? ' ' : '');
            await sendChunk(word, 20);
          }
          
          // 4. Add sources section last (supporting documents)
          if (sources.length > 0) {
            console.log('📁 Adding sources to response, count:', sources.length);
            
            await sendChunk('\n\n---\n\n', 50);
            await sendChunk('### 📁 Source Documents\n\n', 50);
            
            for (let i = 0; i < sources.length; i++) {
              const source = sources[i];
              
              // Better title extraction with fallbacks
              let title = 'Unknown Document';
              
              // Try to get title from various fields
              if (source.title && source.title !== source.filename) {
                title = source.title;
              } else if (source.document_title) {
                title = source.document_title;
              } else if (source.name) {
                title = source.name;
              } else if (source.filename) {
                // Clean up filename if it looks like a UUID
                if (source.filename.match(/^[a-f0-9\-\s]+$/i)) {
                  title = `Document ${i + 1}`;
                } else {
                  // Remove file extension and clean filename
                  title = source.filename.replace(/\.[^/.]+$/, '').replace(/[_-]/g, ' ');
                }
              } else {
                title = `Document ${i + 1}`;
              }
              
              const backendUrl = process.env.BACKEND_URL || 'http://localhost:5000';
              
              // Generate download URL if not provided
              let downloadUrl = source.download_url;
              if (!downloadUrl || !downloadUrl.startsWith('http')) {
                downloadUrl = `${backendUrl}/api/files/download/${encodeURIComponent(source.filename || '')}`;
              }
              
              // Add source as markdown with proper formatting
              await sendChunk(`**${i + 1}. ${title}**\n`, 20);
              
              if (source.excerpt) {
                const excerpt = source.excerpt.substring(0, 150) + (source.excerpt.length > 150 ? '...' : '');
                await sendChunk(`*${excerpt}*\n`, 10);
              } else if (source.department || source.sub_department) {
                const deptInfo = [source.department, source.sub_department].filter(Boolean).join(' › ');
                await sendChunk(`*Department: ${deptInfo}*\n`, 10);
              }
              
              await sendChunk(`[📄 Download PDF](${downloadUrl})\n\n`, 30);
            }
          }
          
          // Send finish signal only if controller is still open
          if (controller.desiredSize !== null) {
            const finishChunk = `d:{"finishReason":"stop","usage":{"promptTokens":0,"completionTokens":0}}\n`;
            controller.enqueue(encoder.encode(finishChunk));
            controller.close();
          }
          
        } catch (error) {
          console.error('Error in stream controller:', error);
          if (controller.desiredSize !== null) {
            controller.error(error);
          }
        }
      },
      
      cancel() {
        console.log('Stream cancelled by client');
      }
    });

    return new Response(stream, {
      headers: {
        'Content-Type': 'text/plain; charset=utf-8',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    });

  } catch (error) {
    console.error('Error in chat API:', error);
    
    // Return error using AI SDK format
    const encoder = new TextEncoder();
    const errorMessage = 'I apologize, but I encountered an error while processing your request. Please try again.';
    
    const errorStream = new ReadableStream({
      async start(controller) {
        try {
          // Safely escape error message
          const escapedError = errorMessage
            .replace(/\\/g, '\\\\')
            .replace(/"/g, '\\"')
            .replace(/\n/g, '\\n');
          
          const errorChunk = `0:"${escapedError}"\n`;
          controller.enqueue(encoder.encode(errorChunk));
          
          // Send completion
          const finishChunk = `d:{"finishReason":"error","usage":{"promptTokens":0,"completionTokens":0}}\n`;
          controller.enqueue(encoder.encode(finishChunk));
          
          controller.close();
        } catch (error) {
          console.error('Error in error stream controller:', error);
          if (controller.desiredSize !== null) {
            controller.error(error);
          }
        }
      }
    });

    return new Response(errorStream, {
      status: 200,
      headers: {
        'Content-Type': 'text/plain; charset=utf-8',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    });
  }
}
