import React, { useState } from 'react';
import { useChat } from '../context/ChatContext';
import { X, Search, Zap, Plus } from 'lucide-react';

export const CannedRepliesModal = ({ isOpen, onClose, onSelect }) => {
  const { cannedReplies } = useChat();
  const [search, setSearch] = useState('');

  if (!isOpen) return null;

  const filtered = cannedReplies.filter(r => 
    r.title.toLowerCase().includes(search.toLowerCase()) ||
    r.shortcut.toLowerCase().includes(search.toLowerCase()) ||
    r.body.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Zap size={18} color="var(--accent-wa)" />
            <h3>Quick Canned Replies</h3>
          </div>
          <button className="header-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border-color)' }}>
          <div className="search-box">
            <Search size={16} />
            <input
              type="text"
              placeholder="Search templates (/greet, /order)..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              autoFocus
            />
          </div>
        </div>

        <div className="canned-list">
          {filtered.length > 0 ? (
            filtered.map((item) => (
              <div 
                key={item.id} 
                className="canned-item"
                onClick={() => {
                  onSelect(item.body);
                  onClose();
                }}
              >
                <div className="canned-title">
                  <span>{item.title}</span>
                  <span className="canned-shortcut">{item.shortcut}</span>
                </div>
                <div className="canned-body">{item.body}</div>
              </div>
            ))
          ) : (
            <p style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '20px' }}>
              No matching canned responses
            </p>
          )}
        </div>
      </div>
    </div>
  );
};
