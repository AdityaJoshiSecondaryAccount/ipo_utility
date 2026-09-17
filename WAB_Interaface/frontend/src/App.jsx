import React, { useState } from 'react';
import { ChatProvider, useChat } from './context/ChatContext';
import { Sidebar } from './components/Sidebar';
import { ChatArea } from './components/ChatArea';

function UserDropdown() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div style={{ position: 'relative' }}>
      <div 
        onClick={() => setIsOpen(!isOpen)}
        style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', color: 'white' }}
      >
        <span style={{ fontSize: '16px' }}>👤</span>
        <span>Welcome, broker ▾</span>
      </div>
      
      {isOpen && (
        <div 
          style={{
            position: 'absolute',
            top: '100%',
            right: 0,
            background: '#686868',
            border: '1px solid rgba(0,0,0,0.15)',
            borderRadius: '4px',
            minWidth: '220px',
            padding: '8px 0',
            marginTop: '12px',
            zIndex: 1000,
            boxShadow: '0 4px 12px rgba(0,0,0,0.2)'
          }}
          onMouseLeave={() => setIsOpen(false)}
        >
          <a href="https://hostinger.ipoutility.in/user_profile" style={{ display: 'block', padding: '8px 24px', color: 'white', textDecoration: 'none', fontSize: '14px' }}>
            User Profile
          </a>
          <div style={{ display: 'block', padding: '8px 24px', color: 'white', fontSize: '14px' }}>
            Expiry Date : (Check Dashboard)
          </div>
          <a href="https://hostinger.ipoutility.in/" style={{ display: 'block', padding: '8px 24px', color: 'white', textDecoration: 'none', fontSize: '14px' }}>
            Change Password
          </a>
          <div style={{ height: '4px' }}></div>
          <a href="https://hostinger.ipoutility.in/logout" style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 24px', color: 'white', textDecoration: 'none', fontSize: '14px' }}>
            <span style={{ color: '#ff5252', fontSize: '16px' }}>↪</span> Logout
          </a>
        </div>
      )}
    </div>
  );
}

function MainLayout() {
  const { activeConversation } = useChat();
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', width: '100vw', overflow: 'hidden', backgroundColor: '#686868' }}>
      {/* Django-style Header */}
      <nav style={{
        background: '#686868',
        height: '56px',
        display: 'flex',
        alignItems: 'center',
        padding: '0 20px',
        color: 'white',
        fontWeight: 'bold',
        fontSize: '16px',
        flexShrink: 0,
        justifyContent: 'space-between',
        borderBottom: '1px solid rgba(0,0,0,0.2)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px', fontSize: '15px', fontWeight: 'normal' }}>
          <a href="https://hostinger.ipoutility.in/" style={{ color: 'orange', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '5px', fontWeight: 'bold' }}>
            <span>🏠 IPO UTILITY</span>
          </a>
          
          <a href="https://hostinger.ipoutility.in/IPOSETUP" style={{ color: 'white', textDecoration: 'none' }}>
            <b style={{ color: '#fff' }}>|</b> &nbsp; Setup
          </a>
          
          <a href="https://hostinger.ipoutility.in/GroupWiseDashboard" style={{ color: 'white', textDecoration: 'none' }}>
            <b style={{ color: '#fff' }}>|</b> &nbsp; Group Wise Dashboard
          </a>
          
          <a href="https://hostinger.ipoutility.in/group-billing-details/" style={{ color: 'white', textDecoration: 'none' }}>
            <b style={{ color: '#fff' }}>|</b> &nbsp; Positions
          </a>
          
          <a href="https://hostinger.ipoutility.in/accounting" style={{ color: 'white', textDecoration: 'none' }}>
            <b style={{ color: '#fff' }}>|</b> &nbsp; Accounting
          </a>
          
          <a href="https://hostinger.ipoutility.in/BackUp" style={{ color: 'white', textDecoration: 'none' }}>
            <b style={{ color: '#fff' }}>|</b> &nbsp; Backup
          </a>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px', fontSize: '14px', fontWeight: 'normal' }}>
          <UserDropdown />
        </div>
      </nav>

      {/* Main App Container */}
      <div 
        className={`app-container ${activeConversation ? 'has-active-chat' : 'no-active-chat'}`} 
        style={{ flex: 1, height: 'calc(100vh - 56px)' }}
      >
        <Sidebar />
        <ChatArea />
      </div>
    </div>
  );
}

function App() {
  return (
    <ChatProvider>
      <MainLayout />
    </ChatProvider>
  );
}

export default App;
