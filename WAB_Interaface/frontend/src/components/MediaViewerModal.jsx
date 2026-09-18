import React from 'react';
import { X, Download } from 'lucide-react';

export const MediaViewerModal = ({ mediaUrl, onClose }) => {
  if (!mediaUrl) return null;

  const proxiedUrl = mediaUrl.startsWith('http') 
    ? `/chat-api/proxy?url=${encodeURIComponent(mediaUrl)}` 
    : mediaUrl;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div 
        style={{ 
          position: 'relative', 
          maxWidth: '90vw', 
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center'
        }} 
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ position: 'absolute', top: -45, right: 0, display: 'flex', gap: '10px' }}>
          <a 
            href={proxiedUrl} 
            download="whatsapp_attachment" 
            className="header-btn" 
            style={{ background: 'rgba(0,0,0,0.6)' }}
            title="Download"
          >
            <Download size={20} color="#fff" />
          </a>
          <button 
            className="header-btn" 
            style={{ background: 'rgba(0,0,0,0.6)' }} 
            onClick={onClose}
          >
            <X size={20} color="#fff" />
          </button>
        </div>

        <img 
          src={proxiedUrl} 
          alt="WhatsApp Media Preview" 
          style={{ 
            maxWidth: '100%', 
            maxHeight: '85vh', 
            borderRadius: '8px', 
            boxShadow: '0 8px 30px rgba(0,0,0,0.8)' 
          }} 
        />
      </div>
    </div>
  );
};
