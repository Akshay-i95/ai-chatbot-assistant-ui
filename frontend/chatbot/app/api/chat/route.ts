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

    // Get or create a session (for now we'll use a default session)
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:5000';
    
    // First, try to get existing sessions to use the latest one, or create a new one
    let sessionId;
    try {
      const sessionsResponse = await fetch(`${backendUrl}/api/chat/sessions`);
      if (sessionsResponse.ok) {
        const sessions = await sessionsResponse.json();
        sessionId = sessions.length > 0 ? sessions[0].id : null;
      }
    } catch (error) {
      console.log('Could not fetch existing sessions, will create new one');
    }

    // Create new session if none exists
    if (!sessionId) {
      const createSessionResponse = await fetch(`${backendUrl}/api/chat/sessions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: 'Chat Session'
        }),
      });
      
      if (createSessionResponse.ok) {
        const session = await createSessionResponse.json();
        sessionId = session.id;
      } else {
        throw new Error('Failed to create session');
      }
    }

    // Send message to backend
    const response = await fetch(`${backendUrl}/api/chat/sessions/${sessionId}/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        content: messageContent
      }),
    });

    if (!response.ok) {
      throw new Error(`Backend responded with status: ${response.status}`);
    }

    const data = await response.json();
    const aiResponse = data.ai_message.content;
    const metadata = data.ai_message.metadata || {};
    const reasoning = metadata.reasoning || '';
    const sources = metadata.sources || [];
    const confidence = metadata.confidence || 0;
    const isFollowUp = metadata.is_follow_up || false;
    const followUpContext = metadata.follow_up_context || null;

    // Create AI SDK compatible streaming response with structured content
    const encoder = new TextEncoder();
    
    const stream = new ReadableStream({
      async start(controller) {
        try {
          // Helper function to safely encode and send chunks
          const sendChunk = async (text: string, delay: number = 50) => {
            if (controller.desiredSize === null) return; // Controller is closed
            
            // Properly escape the text for JSON
            const escapedText = text
              .replace(/\\/g, '\\\\')  // Escape backslashes first
              .replace(/"/g, '\\"')    // Escape quotes
              .replace(/\n/g, '\\n')   // Escape newlines
              .replace(/\r/g, '\\r')   // Escape carriage returns
              .replace(/\t/g, '\\t');  // Escape tabs
            
            const chunk = `0:"${escapedText}"\n`;
            controller.enqueue(encoder.encode(chunk));
            
            if (delay > 0) {
              await new Promise(resolve => setTimeout(resolve, delay));
            }
          };
          
          // 1. Add follow-up indicator if this is a follow-up query
          if (isFollowUp && followUpContext) {
            await sendChunk('🔗 **Follow-up Response:**\n\n', 100);
            await sendChunk('<details>\n<summary>Conversation Context</summary>\n\n', 50);
            
            if (followUpContext.detected_phrases?.length > 0) {
              await sendChunk(`*Detected follow-up phrases: ${followUpContext.detected_phrases.join(', ')}*\n\n`, 50);
            }
            
            if (followUpContext.previous_topic) {
              await sendChunk(`*Previous topic: ${followUpContext.previous_topic.substring(0, 100)}...*\n\n`, 50);
            }
            
            await sendChunk('</details>\n\n', 100);
          }
          
          // 2. Stream reasoning if available
          if (reasoning.trim()) {
            await sendChunk('🤔 **Reasoning:**\n\n', 100);
            await sendChunk('<details>\n<summary>View AI Reasoning Process</summary>\n\n', 50);
            
            // Stream reasoning in smaller chunks to avoid JSON issues
            const reasoningChunks = reasoning.split('. ');
            for (let i = 0; i < reasoningChunks.length; i++) {
              const chunk = reasoningChunks[i] + (i < reasoningChunks.length - 1 ? '. ' : '');
              await sendChunk(chunk, 80);
            }
            
            await sendChunk('\n\n</details>\n\n---\n\n', 100);
          }
          
          // 3. Stream the main AI response
          await sendChunk('💬 **Response:**\n\n', 100);
          
          // Stream main response word by word
          const words = aiResponse.split(' ');
          for (let i = 0; i < words.length; i++) {
            if (controller.desiredSize === null) break; // Controller is closed
            
            const word = words[i] + (i < words.length - 1 ? ' ' : '');
            await sendChunk(word, 80);
          }
          
          // 4. Add sources section if available
          if (sources.length > 0) {
            await sendChunk('\n\n---\n\n📚 **Sources & References:**\n\n', 100);
            await sendChunk('<details>\n<summary>View Source Documents</summary>\n\n', 50);
            
            for (let i = 0; i < sources.length; i++) {
              const source = sources[i];
              await sendChunk(`**Source ${i + 1}:**\n`, 30);
              await sendChunk(`- **Document:** ${source.filename || 'Unknown'}\n`, 30);
              await sendChunk(`- **Relevance Score:** ${(source.relevance_score || 0).toFixed(3)}\n`, 30);
              
              if (source.total_pages) {
                await sendChunk(`- **Total Pages:** ${source.total_pages}\n`, 30);
              }
              
              if (source.page) {
                await sendChunk(`- **Page:** ${source.page}\n`, 30);
              }
              
              if (source.content) {
                const snippet = source.content.substring(0, 200);
                await sendChunk(`- **Content:** ${snippet}...\n`, 30);
              }
              
              if (source.download_available && source.filename) {
                await sendChunk(`- **[Download PDF](http://localhost:5000/api/files/download/${source.filename})**\n`, 30);
                if (source.file_size_mb) {
                  await sendChunk(`- **File Size:** ${source.file_size_mb.toFixed(1)} MB\n`, 30);
                }
              } else if (source.filename && source.filename !== 'Unknown') {
                await sendChunk(`- **[Download PDF](http://localhost:5000/api/files/download/${source.filename})** _(File may not be available)_\n`, 30);
              }
              
              await sendChunk('\n', 30);
            }
            
            await sendChunk(`\n**Confidence Score:** ${(confidence * 100).toFixed(1)}%\n\n</details>`, 50);
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
