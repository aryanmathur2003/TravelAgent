import React from 'react';
import Header from './components/Header';
import Chat from './components/Chat';

const App: React.FC = () => {
  return (
    <div className="flex flex-col h-screen">
      <Header />
      <main className="flex-grow overflow-hidden">
        <div className="container mx-auto h-full">
          <Chat />
        </div>
      </main>
    </div>
  );
};

export default App; 