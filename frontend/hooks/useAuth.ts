import { useState, useEffect } from 'react';
import axios from 'axios';
import { useRouter } from 'next/router';

interface User {
  id: string;
  email: string;
  name: string;
}

interface AuthState {
  user: User | null;
  loading: boolean;
  error: string | null;
}

export function useAuth() {
  const [state, setState] = useState<AuthState>({
    user: null,
    loading: true,
    error: null,
  });
  const router = useRouter();

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        setState({ user: null, loading: false, error: null });
        return;
      }

      const response = await axios.get('/api/auth/me', {
        headers: { Authorization: `Bearer ${token}` },
      });

      setState({ user: response.data, loading: false, error: null });
    } catch (error) {
      localStorage.removeItem('token');
      setState({ user: null, loading: false, error: 'Authentication failed' });
    }
  };

  const login = async (email: string, password: string) => {
    try {
      setState({ ...state, loading: true, error: null });
      const response = await axios.post('/api/auth/login', { email, password });
      const { token, user } = response.data;
      
      localStorage.setItem('token', token);
      setState({ user, loading: false, error: null });
      router.push('/');
    } catch (error) {
      setState({
        ...state,
        loading: false,
        error: 'Invalid email or password',
      });
    }
  };

  const register = async (name: string, email: string, password: string) => {
    try {
      setState({ ...state, loading: true, error: null });
      const response = await axios.post('/api/auth/register', {
        name,
        email,
        password,
      });
      const { token, user } = response.data;
      
      localStorage.setItem('token', token);
      setState({ user, loading: false, error: null });
      router.push('/');
    } catch (error) {
      setState({
        ...state,
        loading: false,
        error: 'Registration failed',
      });
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setState({ user: null, loading: false, error: null });
    router.push('/login');
  };

  return {
    user: state.user,
    loading: state.loading,
    error: state.error,
    login,
    register,
    logout,
  };
} 