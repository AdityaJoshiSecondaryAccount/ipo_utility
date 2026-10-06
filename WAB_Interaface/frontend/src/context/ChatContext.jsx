import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';

const ChatContext = createContext(null);

// Web Audio synthesizer chime for incoming messages (zero external audio file needed!)
const playNotificationSound = () => {
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return;
    const ctx = new AudioContext();
    
    // Note 1: High crisp ping
    const osc1 = ctx.createOscillator();
    const gain1 = ctx.createGain();
    osc1.type = 'sine';
    osc1.frequency.setValueAtTime(880, ctx.currentTime); // A5
    gain1.gain.setValueAtTime(0.15, ctx.currentTime);
    gain1.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.25);
    osc1.connect(gain1);
    gain1.connect(ctx.destination);
    osc1.start();
    osc1.stop(ctx.currentTime + 0.25);

    // Note 2: Harmonic pleasant follow-up
    const osc2 = ctx.createOscillator();
    const gain2 = ctx.createGain();
    osc2.type = 'sine';
    osc2.frequency.setValueAtTime(1318.51, ctx.currentTime + 0.08); // E6
    gain2.gain.setValueAtTime(0.15, ctx.currentTime + 0.08);
    gain2.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.35);
    osc2.connect(gain2);
    gain2.connect(ctx.destination);
    osc2.start(ctx.currentTime + 0.08);
    osc2.stop(ctx.currentTime + 0.35);
  } catch (e) {
    console.warn("Audio chime playback blocked or not supported:", e);
  }
};

export const ChatProvider = ({ children }) => {
  const [conversations, setConversations] = useState([]);
  const [activeConversation, setActiveConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState('all'); // 'all' or 'unread'
  const [wsConnected, setWsConnected] = useState(false);
  const [cannedReplies, setCannedReplies] = useState([]);

  const [isRefreshing, setIsRefreshing] = useState(false);

  const wsRef = useRef(null);
  const activeConvRef = useRef(activeConversation);
  activeConvRef.current = activeConversation;

  // 1. Fetch Conversations from backend
  const fetchConversations = useCallback(async () => {
    setIsRefreshing(true);
    try {
      const res = await fetch('/chat-api/conversations');
      if (res.ok) {
        const data = await res.json();
        setConversations(data);
      }
    } catch (err) {
      console.error("Failed to fetch conversations:", err);
    } finally {
      setTimeout(() => setIsRefreshing(false), 600);
    }
  }, []);

  // 2. Fetch Canned Replies
  const fetchCannedReplies = useCallback(async () => {
    try {
      const res = await fetch('/chat-api/canned-responses');
      if (res.ok) {
        const data = await res.json();
        setCannedReplies(data);
      }
    } catch (err) {
      console.error("Failed to fetch canned responses:", err);
    }
  }, []);

  // 3. Select active conversation and load messages
  const selectConversation = useCallback(async (conv) => {
    setActiveConversation(conv);
    setLoadingMessages(true);
    try {
      const res = await fetch(`/chat-api/conversations/${conv.id}/messages`);
      if (res.ok) {
        const data = await res.json();
        setMessages(data);
      }

      // Send read receipt to backend & Meta
      await fetch(`/chat-api/conversations/${conv.id}/read`, { method: 'POST' });
      setConversations(prev => prev.map(c => c.id === conv.id ? { ...c, unread_count: 0 } : c));
    } catch (err) {
      console.error("Failed to load messages:", err);
    } finally {
      setLoadingMessages(false);
    }
  }, []);

  // 4. Send Message (text or media)
  const sendMessage = useCallback(async ({ text, messageType = 'text', mediaUrl = null, mediaFilename = null }) => {
    if (!activeConversation) return false;
    const phone = activeConversation.contact.phone_number;

    try {
      const res = await fetch('/chat-api/messages/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          phone_number: phone,
          text: text || '',
          message_type: messageType,
          media_url: mediaUrl,
          media_filename: mediaFilename
        })
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Failed to send message");
      }

      const sentMsg = await res.json();
      return sentMsg;
    } catch (err) {
      console.error("Send message error:", err);
      throw err;
    }
  }, [activeConversation]);

  // 5. Delete Message
  const deleteMessage = useCallback(async (messageId) => {
    try {
      const res = await fetch(`/chat-api/messages/${messageId}`, {
        method: 'DELETE'
      });
      if (!res.ok) {
        let errorMsg = "Failed to delete message";
        try {
          const errData = await res.json();
          errorMsg = errData.detail || errorMsg;
        } catch {
          const text = await res.text();
          if (text) errorMsg = text;
        }
        throw new Error(errorMsg);
      }
      const data = await res.json().catch(() => ({}));
      setMessages(prev => prev.filter(m => m.id !== messageId));
      if (data && data.conversation_id) {
        setConversations(prev => prev.map(c => {
          if (c.id === data.conversation_id) {
            return {
              ...c,
              last_message_text: data.last_message_text !== undefined ? data.last_message_text : c.last_message_text,
              last_message_time: data.last_message_time || c.last_message_time,
              last_message_status: data.last_message_status || c.last_message_status,
              unread_count: data.unread_count !== undefined ? data.unread_count : c.unread_count
            };
          }
          return c;
        }));
      }
      fetchConversations();
      return true;
    } catch (err) {
      console.error("Delete message error:", err);
      alert(`Delete failed: ${err.message}`);
      return false;
    }
  }, [fetchConversations]);

  // 5. WebSocket Live Synchronization
  useEffect(() => {
    fetchConversations();
    fetchCannedReplies();

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/chat-api/ws`;

    let reconnectTimer;
    const connectWS = () => {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setWsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          const { type, data } = payload;

          if (type === 'NEW_MESSAGE') {
            const { message, conversation } = data;

            // Play alert chime if inbound
            if (message.direction === 'inbound') {
              playNotificationSound();
            }

            // Update conversation list item or push to top
            setConversations(prev => {
              const existingIdx = prev.findIndex(c => c.id === conversation.id);
              if (existingIdx >= 0) {
                const updated = [...prev];
                updated.splice(existingIdx, 1);
                return [conversation, ...updated];
              }
              return [conversation, ...prev];
            });

            // If active conversation matches, append message
            if (activeConvRef.current && activeConvRef.current.id === message.conversation_id) {
              setMessages(prev => {
                if (prev.some(m => m.id === message.id)) return prev;
                return [...prev, message];
              });
              // Auto mark read if viewing this conversation
              if (message.direction === 'inbound') {
                fetch(`/chat-api/conversations/${message.conversation_id}/read`, { method: 'POST' });
              }
            }
          } else if (type === 'MESSAGE_STATUS_UPDATE') {
            const { message_id, status, error_message } = data;
            setMessages(prev => prev.map(m => m.id === message_id ? { ...m, status, error_message } : m));
          } else if (type === 'CONVERSATION_READ') {
            const { conversation_id } = data;
            setConversations(prev => prev.map(c => c.id === conversation_id ? { ...c, unread_count: 0 } : c));
          } else if (type === 'MESSAGE_DELETED') {
            const { message_id, conversation_id, last_message_text, last_message_time, last_message_status, unread_count } = data;
            setMessages(prev => prev.filter(m => m.id !== message_id));
            if (conversation_id) {
              setConversations(prev => prev.map(c => {
                if (c.id === conversation_id) {
                  return {
                    ...c,
                    last_message_text: last_message_text !== undefined ? last_message_text : c.last_message_text,
                    last_message_time: last_message_time || c.last_message_time,
                    last_message_status: last_message_status || c.last_message_status,
                    unread_count: unread_count !== undefined ? unread_count : c.unread_count
                  };
                }
                return c;
              }));
            }
            fetchConversations();
          }
        } catch (err) {
          console.error("WS message parse error:", err);
        }
      };

      ws.onclose = () => {
        setWsConnected(false);
        reconnectTimer = setTimeout(connectWS, 3000);
      };

      ws.onerror = () => {
        ws.close();
      };
    };

    connectWS();

    return () => {
      clearTimeout(reconnectTimer);
      if (wsRef.current) {
        // Only close if it's actually open to prevent React StrictMode warnings
        if (wsRef.current.readyState === 1) {
          wsRef.current.close();
        } else {
          // If connecting, wait for open then close, or just set onopen to close it
          wsRef.current.onopen = () => wsRef.current.close();
        }
      }
    };
  }, [fetchConversations, fetchCannedReplies]);

  // Filtered conversations
  const filteredConversations = conversations.filter(conv => {
    if (filterType === 'unread' && conv.unread_count === 0) return false;
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    const nameMatch = conv.contact.name && conv.contact.name.toLowerCase().includes(q);
    const phoneMatch = conv.contact.phone_number.includes(q);
    const msgMatch = conv.last_message_text && conv.last_message_text.toLowerCase().includes(q);
    return nameMatch || phoneMatch || msgMatch;
  });

  return (
    <ChatContext.Provider value={{
      conversations: filteredConversations,
      allConversationsCount: conversations.length,
      unreadCount: conversations.filter(c => c.unread_count > 0).length,
      activeConversation,
      clearActiveConversation: () => setActiveConversation(null),
      messages,
      loadingMessages,
      searchQuery,
      setSearchQuery,
      filterType,
      setFilterType,
      selectConversation,
      sendMessage,
      deleteMessage,
      wsConnected,
      cannedReplies,
      isRefreshing,
      refreshConversations: fetchConversations
    }}>
      {children}
    </ChatContext.Provider>
  );
};

export const useChat = () => {
  const context = useContext(ChatContext);
  if (!context) throw new Error("useChat must be used within ChatProvider");
  return context;
};
