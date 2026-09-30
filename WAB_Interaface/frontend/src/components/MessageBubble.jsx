import React, { useState, useRef, useEffect } from 'react';
import { 
  Check, CheckCheck, AlertCircle, FileText, Download, Play, Music,
  ChevronDown, Trash2, Copy, Info, CornerUpLeft, Smile, Forward, Star, Pin 
} from 'lucide-react';
import { formatMessageTime } from '../utils/dateUtils';
import { useChat } from '../context/ChatContext';

export const MessageBubble = ({ message, onPreviewMedia }) => {
  const { deleteMessage } = useChat();
  const [showMenu, setShowMenu] = useState(false);
  const menuRef = useRef(null);

  const isInbound = message.direction === 'inbound';
  
  // Patch old URLs from DB if they still use the old /api/ prefix
  const safeMediaUrl = message.media_url ? message.media_url.replace('/api/media/file/', '/chat-api/file/') : null;

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setShowMenu(false);
      }
    };
    if (showMenu) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showMenu]);

  const handleCopy = () => {
    if (message.text) {
      navigator.clipboard.writeText(message.text);
    }
    setShowMenu(false);
  };

  const handleDelete = () => {
    setShowMenu(false);
    if (window.confirm('Delete this message?')) {
      deleteMessage(message.id);
    }
  };

  const renderStatus = () => {
    if (isInbound) return null;
    if (message.status === 'read') return <CheckCheck size={14} className="status-icon read" title="Read" />;
    if (message.status === 'delivered') return <CheckCheck size={14} className="status-icon" title="Delivered" />;
    if (message.status === 'sent') return <Check size={14} className="status-icon" title="Sent to WhatsApp" />;
    if (message.status === 'failed') return <AlertCircle size={14} className="status-icon failed" title={message.error_message || "Failed to send"} />;
    return <span style={{ fontSize: '10px' }}>⏱️</span>;
  };

  const renderContent = () => {
    switch (message.message_type) {
      case 'image':
        return (
          <div>
            {message.media_url && (
              <img 
                src={safeMediaUrl.startsWith('http') ? `/chat-api/proxy?url=${encodeURIComponent(safeMediaUrl)}` : safeMediaUrl} 
                alt="Attachment" 
                className="message-media-img"
                onClick={() => onPreviewMedia && onPreviewMedia(safeMediaUrl)}
              />
            )}
            {message.text && message.text !== '[Image]' && <p style={{ whiteSpace: 'pre-wrap', marginTop: '5px' }}>{message.text}</p>}
          </div>
        );

      case 'document':
        return (
          <div>
            <a 
              href={safeMediaUrl?.startsWith('http') ? `/chat-api/proxy?url=${encodeURIComponent(safeMediaUrl)}` : safeMediaUrl}
              target="_blank" 
              rel="noopener noreferrer"
              className="document-card"
            >
              <FileText size={28} color="var(--accent-teal)" />
              <div className="document-info">
                <span className="document-name">{message.media_filename || 'Document.pdf'}</span>
                <span className="document-hint">Click to download</span>
              </div>
              <Download size={16} style={{ marginLeft: 'auto', opacity: 0.8 }} />
            </a>
            {message.text && message.text !== '[Document]' && <p>{message.text}</p>}
          </div>
        );

      case 'audio':
        return (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '4px 0' }}>
            <Music size={22} color="var(--accent-wa)" />
            <audio controls style={{ height: '32px', maxWidth: '220px' }}>
              <source src={safeMediaUrl?.startsWith('http') ? `/chat-api/proxy?url=${encodeURIComponent(safeMediaUrl)}` : safeMediaUrl} />
              Audio not supported
            </audio>
          </div>
        );

      case 'interactive':
      case 'button':
        return (
          <div>
            <p style={{ whiteSpace: 'pre-wrap' }}>{message.text}</p>
            <div style={{ marginTop: '8px', paddingTop: '8px', borderTop: '1px solid rgba(255,255,255,0.1)', textAlign: 'center' }}>
              <span style={{ color: '#00a884', fontWeight: 'bold' }}>🔘 Interactive Response</span>
            </div>
          </div>
        );

      case 'template':
        return (
          <div>
            <p style={{ whiteSpace: 'pre-wrap' }}>{message.text}</p>
            <div style={{ marginTop: '8px', paddingTop: '8px', borderTop: '1px solid rgba(255,255,255,0.1)', textAlign: 'center' }}>
              <span style={{ color: '#00a884', fontWeight: '500', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '5px' }}>
                <span style={{ fontSize: '16px' }}>🔗</span> View Order Status
              </span>
            </div>
          </div>
        );

      default:
        return <p style={{ whiteSpace: 'pre-wrap' }}>{message.text}</p>;
    }
  };

  return (
    <div className={`message-wrapper ${message.direction}`}>
      <div className="message-bubble" ref={menuRef}>
        {/* Chevron Dropdown Trigger Button */}
        <button 
          className={`message-menu-btn ${showMenu ? 'active' : ''}`}
          onClick={() => setShowMenu(!showMenu)}
          title="Message options"
        >
          <ChevronDown size={15} />
        </button>

        {/* WhatsApp-Style Options Menu */}
        {showMenu && (
          <div className="message-dropdown-menu">
            <div className="message-dropdown-item" onClick={() => setShowMenu(false)}>
              <Info size={15} />
              <span>Message info</span>
            </div>
            <div className="message-dropdown-item" onClick={() => setShowMenu(false)}>
              <CornerUpLeft size={15} />
              <span>Reply</span>
            </div>
            <div className="message-dropdown-item" onClick={handleCopy}>
              <Copy size={15} />
              <span>Copy</span>
            </div>
            <div className="message-dropdown-item" onClick={() => setShowMenu(false)}>
              <Smile size={15} />
              <span>React</span>
            </div>
            <div className="message-dropdown-item" onClick={() => setShowMenu(false)}>
              <Forward size={15} />
              <span>Forward</span>
            </div>
            <div className="message-dropdown-item" onClick={() => setShowMenu(false)}>
              <Pin size={15} />
              <span>Pin</span>
            </div>
            <div className="message-dropdown-item" onClick={() => setShowMenu(false)}>
              <Star size={15} />
              <span>Star</span>
            </div>
            <div className="message-dropdown-item danger" onClick={handleDelete}>
              <Trash2 size={15} color="#ff5252" />
              <span style={{ color: '#ff5252' }}>Delete</span>
            </div>
          </div>
        )}

        {renderContent()}

        <div className="message-meta">
          <span>{formatMessageTime(message.timestamp)}</span>
          {renderStatus()}
        </div>
      </div>
    </div>
  );
};

