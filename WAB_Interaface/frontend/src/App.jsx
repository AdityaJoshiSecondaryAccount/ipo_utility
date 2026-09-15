import React from 'react';
import { ChatProvider, useChat } from './context/ChatContext';
import { Sidebar } from './components/Sidebar';
import { ChatArea } from './components/ChatArea';

function MainLayout() {
  const { activeConversation } = useChat();
  return (
    <div className={`app-container ${activeConversation ? 'has-active-chat' : 'no-active-chat'}`}>
      <Sidebar />
      <ChatArea />
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
