import React, { useEffect, useRef, useState } from 'react';
import { useChat } from '../context/ChatContext';
import { MessageBubble } from './MessageBubble';
import { MessageComposer } from './MessageComposer';
import { MediaViewerModal } from './MediaViewerModal';
import { MessageSquare, Clock, Phone, ShieldCheck, User, ArrowLeft } from 'lucide-react';

export const ChatArea = () => {
  const { activeConversation, clearActiveConversation, messages, loadingMessages } = useChat();
  const messagesEndRef = useRef(null);
  const [previewMediaUrl, setPreviewMediaUrl] = useState(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  if (!activeConversation) {
    return (
      <main className="chat-area">
        <div className="empty-chat">
          <div className="empty-chat-icon">
            <MessageSquare size={44} />
          </div>
          <h2 style={{ fontSize: '20px', color: 'var(--text-primary)' }}>ADwealth WhatsApp Inbox</h2>
          <p style={{ maxWidth: '400px', fontSize: '13.5px', lineHeight: '1.5' }}>
            Select a conversation from the left sidebar to view messages, receive live customer updates, and send replies.
          </p>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: 'var(--accent-wa)' }}>
            <ShieldCheck size={16} />
            <span>Connected to Meta WhatsApp Cloud API</span>
          </div>
        </div>
      </main>
    );
  }

  const { contact } = activeConversation;

  const isWindowActive = () => {
    if (activeConversation.is_window_open === true) return true;
    if (!activeConversation.last_inbound_time) return false;
    const lastInbound = new Date(activeConversation.last_inbound_time);
    const now = new Date();
    const diffHours = (now.getTime() - lastInbound.getTime()) / (1000 * 60 * 60);
    return diffHours >= 0 && diffHours <= 24;
  };

  const windowOpen = isWindowActive();

  return (
    <main className="chat-area">
      {/* Active Chat Header */}
      <header className="chat-header">
        <div className="chat-header-user">
          <button 
            className="header-btn mobile-back-btn" 
            onClick={clearActiveConversation}
            title="Back to conversations"
          >
            <ArrowLeft size={20} />
          </button>
          <div className="avatar">
            <User size={22} />
          </div>
          <div className="chat-header-info">
            <h2>{contact.name || `+${contact.phone_number}`}</h2>
            <p>+{contact.phone_number}</p>
          </div>
        </div>

        <div className="chat-header-actions">
          {windowOpen ? (
            <div className="window-badge" title="Customer messaged within last 24 hours. Free-form replies are active.">
              <Clock size={14} />
              <span>24h Window Active</span>
            </div>
          ) : (
            <div className="window-badge expired" title="More than 24h since customer's last message. Use templates or wait for reply.">
              <Clock size={14} />
              <span>Window Expired</span>
            </div>
          )}
        </div>
      </header>

      {/* Messages Timeline */}
      <div className="messages-container">
        <div className="messages-date-divider">
          <span className="date-badge">End-to-End Encrypted via Meta WhatsApp API</span>
        </div>

        {loadingMessages ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
            Loading messages...
          </div>
        ) : messages.length > 0 ? (
          messages.map((msg) => (
            <MessageBubble 
              key={msg.id} 
              message={msg} 
              onPreviewMedia={(url) => setPreviewMediaUrl(url)}
            />
          ))
        ) : (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
            No messages in this conversation yet. Send the first reply below!
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Message Composer Input */}
      <MessageComposer />

      {/* Media Preview Modal */}
      <MediaViewerModal 
        mediaUrl={previewMediaUrl} 
        onClose={() => setPreviewMediaUrl(null)} 
      />
    </main>
  );
};
