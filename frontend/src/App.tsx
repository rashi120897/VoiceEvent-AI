import React, { useState, useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Documents from './pages/Documents';
import CallLogs from './pages/CallLogs';
import Settings from './pages/Settings';
import { getStoredApiKey, setApiKey, tenantApi, type TenantWithApiKey } from './lib/api';
import { Key, Loader2, ArrowRight, Phone } from 'lucide-react';

function LoginPage({ onLogin }: { onLogin: () => void }) {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [tenantName, setTenantName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [createdKey, setCreatedKey] = useState<string | null>(null);

  const handleLogin = async () => {
    if (!apiKeyInput.trim()) {
      setError('Please enter your API key');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      setApiKey(apiKeyInput.trim());
      await tenantApi.getMe();
      onLogin();
    } catch (err: any) {
      setError(err.message || 'Invalid API key');
      setApiKey('');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async () => {
    if (!tenantName.trim()) {
      setError('Please enter a tenant name');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result: TenantWithApiKey = await tenantApi.create(tenantName.trim());
      setCreatedKey(result.api_key);
      setApiKey(result.api_key);
    } catch (err: any) {
      setError(err.message || 'Failed to create tenant');
    } finally {
      setLoading(false);
    }
  };

  const handleContinueAfterRegister = () => {
    onLogin();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 bg-indigo-600 rounded-2xl mb-4">
            <Phone className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Voice Assistant</h1>
          <p className="text-gray-500 mt-1">Multi-tenant AI voice assistant platform</p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8">
          {/* Show created key */}
          {createdKey ? (
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-2">Tenant Created!</h2>
              <p className="text-sm text-gray-500 mb-4">
                Save your API key - it won't be shown again.
              </p>
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-4">
                <code className="text-sm font-mono break-all text-gray-900">{createdKey}</code>
              </div>
              <button
                onClick={handleContinueAfterRegister}
                className="w-full flex items-center justify-center gap-2 bg-indigo-600 text-white py-2.5 rounded-lg font-medium hover:bg-indigo-700 transition-colors"
              >
                Continue to Dashboard
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <>
              {/* Tab switcher */}
              <div className="flex gap-1 bg-gray-100 rounded-lg p-1 mb-6">
                <button
                  onClick={() => { setMode('login'); setError(null); }}
                  className={`flex-1 py-2 text-sm font-medium rounded-md transition-colors ${
                    mode === 'login' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'
                  }`}
                >
                  Connect
                </button>
                <button
                  onClick={() => { setMode('register'); setError(null); }}
                  className={`flex-1 py-2 text-sm font-medium rounded-md transition-colors ${
                    mode === 'register' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'
                  }`}
                >
                  New Tenant
                </button>
              </div>

              {mode === 'login' ? (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
                    <div className="relative">
                      <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                      <input
                        type="password"
                        value={apiKeyInput}
                        onChange={(e) => setApiKeyInput(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleLogin()}
                        placeholder="va_sk_..."
                        className="w-full border border-gray-300 rounded-lg pl-10 pr-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent font-mono"
                      />
                    </div>
                  </div>
                  <button
                    onClick={handleLogin}
                    disabled={loading}
                    className="w-full flex items-center justify-center gap-2 bg-indigo-600 text-white py-2.5 rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
                  >
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4" />}
                    Connect
                  </button>
                </div>
              ) : (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Tenant Name</label>
                    <input
                      type="text"
                      value={tenantName}
                      onChange={(e) => setTenantName(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleRegister()}
                      placeholder="My Company"
                      className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    />
                  </div>
                  <button
                    onClick={handleRegister}
                    disabled={loading}
                    className="w-full flex items-center justify-center gap-2 bg-indigo-600 text-white py-2.5 rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
                  >
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4" />}
                    Create Tenant
                  </button>
                </div>
              )}

              {error && (
                <div className="mt-4 bg-red-50 border border-red-200 rounded-lg px-4 py-2.5 text-sm text-red-700">
                  {error}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    const checkAuth = async () => {
      const key = getStoredApiKey();
      if (key) {
        try {
          await tenantApi.getMe();
          setIsAuthenticated(true);
        } catch {
          setIsAuthenticated(false);
        }
      }
      setChecking(false);
    };
    checkAuth();
  }, []);

  if (checking) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginPage onLogin={() => setIsAuthenticated(true)} />;
  }

  return (
    <Layout onLogout={() => setIsAuthenticated(false)}>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/documents" element={<Documents />} />
        <Route path="/calls" element={<CallLogs />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}
