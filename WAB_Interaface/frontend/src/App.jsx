import React, { useState } from 'react';
import { ChatProvider, useChat } from './context/ChatContext';
import { Sidebar } from './components/Sidebar';
import { ChatArea } from './components/ChatArea';

function TempLogin({ onLogin }) {
  const [password, setPassword] = useState('');
  
  const handleLogin = (e) => {
    e.preventDefault();
    if (password === 'adwealth2026') {
      localStorage.setItem('temp_wa_auth', 'true');
      onLogin();
    } else {
      alert('Incorrect Password!');
    }
  };

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw', alignItems: 'center', justifyContent: 'center', backgroundColor: '#0b141a', color: 'white' }}>
      <form onSubmit={handleLogin} style={{ background: '#111b21', padding: '40px', borderRadius: '10px', textAlign: 'center', boxShadow: '0 4px 12px rgba(0,0,0,0.5)', width: '90%', maxWidth: '400px' }}>
        <h2 style={{ marginBottom: '10px' }}>ADwealth Admin</h2>
        <p style={{ color: '#8696a0', marginBottom: '25px', fontSize: '14px' }}>Please enter the password to access the inbox.</p>
        <input 
          type="password" 
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password" 
          style={{ padding: '12px', width: '100%', marginBottom: '20px', borderRadius: '5px', border: '1px solid #222e35', background: '#202c33', color: 'white', fontSize: '15px' }}
        />
        <button type="submit" style={{ padding: '12px', width: '100%', background: '#00a884', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer', fontWeight: 'bold', fontSize: '15px' }}>
          Secure Login
        </button>
      </form>
    </div>
  );
}

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
      <nav className="top-nav" style={{
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
        <div className="top-nav-links" style={{ display: 'flex', alignItems: 'center', gap: '20px', fontSize: '15px', fontWeight: 'normal' }}>
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
          
          <a href="/chat" style={{ color: 'white', textDecoration: 'none' }}>
            <b style={{ color: '#fff' }}>|</b> &nbsp; WhatsApp Chat
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
  const [isAuthenticated, setIsAuthenticated] = useState(
    localStorage.getItem('temp_wa_auth') === 'true'
  );

  if (!isAuthenticated) {
    return <TempLogin onLogin={() => setIsAuthenticated(true)} />;
  }

  return (
    <ChatProvider>
      <MainLayout />
    </ChatProvider>
  );
}

export default App;
