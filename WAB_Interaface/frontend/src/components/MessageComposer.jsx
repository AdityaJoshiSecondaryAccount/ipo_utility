import React, { useState, useRef } from 'react';
import { useChat } from '../context/ChatContext';
import { Send, Paperclip, Zap, Smile, Image as ImageIcon, FileText, Loader2 } from 'lucide-react';
import { CannedRepliesModal } from './CannedRepliesModal';

export const MessageComposer = () => {
  const { sendMessage, activeConversation } = useChat();
  const [text, setText] = useState('');
  const [sending, setSending] = useState(false);
  const [showCannedModal, setShowCannedModal] = useState(false);
  const fileInputRef = useRef(null);
  const textareaRef = useRef(null);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = async () => {
    if (!text.trim() || sending) return;
    const msgToSend = text.trim();
    setText('');
    setSending(true);

    try {
      await sendMessage({ text: msgToSend, messageType: 'text' });
    } catch (err) {
      alert(`Message sending failed: ${err.message}`);
      setText(msgToSend); // Restore text on failure
    } finally {
      setSending(false);
      if (textareaRef.current) {
        textareaRef.current.focus();
      }
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    setSending(true);
    try {
      const uploadRes = await fetch('/chat-api/upload', {
        method: 'POST',
        body: formData
      });
      if (!uploadRes.ok) throw new Error('File upload failed');
      const uploadData = await uploadRes.json();

      const isImage = file.type.startsWith('image/');
      const msgType = isImage ? 'image' : 'document';

      const fullMediaUrl = window.location.origin + uploadData.media_url;

      await sendMessage({
        text: file.name,
        messageType: msgType,
        mediaUrl: fullMediaUrl,
        mediaFilename: file.name
      });
    } catch (err) {
      alert(`Upload/Send failed: ${err.message}`);
    } finally {
      setSending(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handlePaste = (e) => {
    // If it's a file (like an image screenshot)
    if (e.clipboardData.files && e.clipboardData.files.length > 0) {
      e.preventDefault();
      const fakeEvent = { target: { files: e.clipboardData.files } };
      handleFileUpload(fakeEvent);
    }
    // Normal text pasting continues default behavior
  };

  return (
    <div className="composer-container">
      {/* Hidden File Input */}
      <input 
        type="file" 
        ref={fileInputRef} 
        style={{ display: 'none' }} 
        onChange={handleFileUpload}
      />

      {/* Canned replies trigger button */}
      <button 
        className="composer-btn" 
        onClick={() => setShowCannedModal(true)}
        title="Quick Canned Replies (/)"
      >
        <Zap size={20} color="var(--accent-wa)" />
      </button>

      {/* Attachment Button */}
      <button 
        className="composer-btn" 
        onClick={() => fileInputRef.current?.click()}
        title="Attach Image or Document"
        disabled={sending}
      >
        <Paperclip size={20} />
      </button>

      {/* Text Area */}
      <div className="composer-input-box">
        <textarea
          ref={textareaRef}
          className="composer-textarea"
          rows={1}
          placeholder="Type a reply... (Press Enter to send)"
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            if (e.target.value === '/') {
              setShowCannedModal(true);
            }
          }}
          onKeyDown={handleKeyDown}
          onPaste={handlePaste}
          disabled={sending}
        />
      </div>

      {/* Send Button */}
      <button 
        className="send-btn" 
        onClick={handleSend}
        disabled={!text.trim() || sending}
        title="Send WhatsApp Message"
      >
        {sending ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
      </button>

      {/* Canned Replies Modal */}
      <CannedRepliesModal 
        isOpen={showCannedModal} 
        onClose={() => setShowCannedModal(false)}
        onSelect={(cannedText) => setText(cannedText)}
      />
    </div>
  );
};
