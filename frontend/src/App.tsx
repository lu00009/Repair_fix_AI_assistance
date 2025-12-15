import { useState, useEffect } from 'react';
import { Chat } from './components/Chat';
import { Login } from './components/Login';
import { apiService } from './services/api';
import './index.css';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check if user has a token
    const token = localStorage.getItem('auth_token');
    if (token) {
      setIsAuthenticated(true);
    }
    setIsLoading(false);
  }, []);

  const handleLogin = async (email: string, password: string) => {
    await apiService.login({ email, password });
    setIsAuthenticated(true);
  };

  const handleSignup = async (email: string, password: string) => {
    await apiService.signup({ email, password });
  };

  const handleLogout = () => {
    apiService.clearToken();
    setIsAuthenticated(false);
  };

  if (isLoading) {
    return (
      <div className="h-screen w-full flex items-center justify-center bg-chat-bg">
        <div className="text-chat-text">Loading...</div>
      </div>
    );
  }

  return (
    <>
      {isAuthenticated ? (
        <Chat onLogout={handleLogout} />
      ) : (
        <Login onLogin={handleLogin} onSignup={handleSignup} />
      )}
    </>
  );
}

export default App;
