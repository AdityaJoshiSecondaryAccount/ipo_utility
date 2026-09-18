import React from 'react';
import { Check, CheckCheck, AlertCircle, FileText, Download, Play, Music } from 'lucide-react';
import { formatMessageTime } from '../utils/dateUtils';

export const MessageBubble = ({ message, onPreviewMedia }) => {
  const isInbound = message.direction === 'inbound';
  
  // Patch old URLs from DB if they still use the old /api/ prefix
  const safeMediaUrl = message.media_url ? message.media_url.replace('/api/media/file/', '/chat-api/file/') : null;

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
            {message.text && message.text !== '[Image]' && <p>{message.text}</p>}
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
      <div className="message-bubble">
        {renderContent()}
        <div className="message-meta">
          <span>{formatMessageTime(message.timestamp)}</span>
          {renderStatus()}
        </div>
      </div>
    </div>
  );
};
