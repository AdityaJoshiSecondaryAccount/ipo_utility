import React from 'react';
import { useChat } from '../context/ChatContext';
import { ConversationItem } from './ConversationItem';
import { MessageSquare, Search, RefreshCw, MessageCircle } from 'lucide-react';

export const Sidebar = () => {
  const {
    conversations,
    allConversationsCount,
    unreadCount,
    searchQuery,
    setSearchQuery,
    filterType,
    setFilterType,
    wsConnected,
    refreshConversations
  } = useChat();

  return (
    <aside className="sidebar">
      {/* Brand Header */}
      <div className="sidebar-header">
        <div className="brand-badge">
          <div className="brand-icon">
            <MessageSquare size={20} />
          </div>
          <div className="brand-info">
            <h1>ADwealth Inbox</h1>
            <span>
              <span className={`status-dot ${wsConnected ? '' : 'offline'}`}></span>
              {wsConnected ? 'Live Synchronized' : 'Connecting...'}
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>

          <button 
            className="header-btn" 
            onClick={refreshConversations}
            title="Refresh Conversations"
          >
            <RefreshCw size={17} />
          </button>
        </div>
      </div>

      {/* Search & Tabs */}
      <div className="sidebar-search-container">
        <div className="search-box">
          <Search size={16} />
          <input
            type="text"
            placeholder="Search name, phone, or message..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div className="filter-tabs">
          <button 
            className={`filter-tab ${filterType === 'all' ? 'active' : ''}`}
            onClick={() => setFilterType('all')}
          >
            All Chats ({allConversationsCount})
          </button>
          <button 
            className={`filter-tab ${filterType === 'unread' ? 'active' : ''}`}
            onClick={() => setFilterType('unread')}
          >
            Unread
            {unreadCount > 0 && <span className="badge">{unreadCount}</span>}
          </button>
        </div>
      </div>

      {/* Conversation List */}
      <div className="conversation-list">
        {conversations.length > 0 ? (
          conversations.map((conv) => (
            <ConversationItem key={conv.id} conversation={conv} />
          ))
        ) : (
          <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--text-muted)' }}>
            <MessageCircle size={36} style={{ opacity: 0.4, marginBottom: '8px' }} />
            <p>No conversations found</p>
          </div>
        )}
      </div>
    </aside>
  );
};
