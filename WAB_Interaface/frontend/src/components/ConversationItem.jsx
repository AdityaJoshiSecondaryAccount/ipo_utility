import React from 'react';
import { useChat } from '../context/ChatContext';
import { Check, CheckCheck, AlertCircle, Image, FileText, Mic } from 'lucide-react';
import { formatConversationTime } from '../utils/dateUtils';

const getInitials = (name, phone) => {
  if (name && !name.startsWith('+')) {
    const parts = name.trim().split(' ');
    if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
    return name.slice(0, 2).toUpperCase();
  }
  return phone ? phone.slice(-2) : 'WA';
};

export const ConversationItem = ({ conversation }) => {
  const { activeConversation, selectConversation } = useChat();
  const isActive = activeConversation?.id === conversation.id;
  const { contact, unread_count, last_message_text, last_message_time, last_message_status } = conversation;

  const renderStatus = () => {
    if (conversation.last_message_direction === 'inbound') return null;
    if (last_message_status === 'read') return <CheckCheck size={14} className="status-icon read" />;
    if (last_message_status === 'delivered') return <CheckCheck size={14} className="status-icon" />;
    if (last_message_status === 'sent') return <Check size={14} className="status-icon" />;
    if (last_message_status === 'failed') return <AlertCircle size={14} className="status-icon failed" />;
    return null;
  };

  return (
    <div 
      className={`conversation-item ${isActive ? 'active' : ''}`}
      onClick={() => selectConversation(conversation)}
    >
      <div className="avatar">
        {getInitials(contact.name, contact.phone_number)}
      </div>
      
      <div className="conv-details">
        <div className="conv-top">
          <span className="conv-name">{contact.name || `+${contact.phone_number}`}</span>
          <span className="conv-time">{formatConversationTime(last_message_time)}</span>
        </div>
        
        <div className="conv-bottom">
          <span className="conv-snippet">
            {renderStatus()}
            {last_message_text || 'No messages yet'}
          </span>
          {unread_count > 0 && (
            <span className="unread-badge">{unread_count}</span>
          )}
        </div>
      </div>
    </div>
  );
};
