import React, { useEffect, useState } from 'react';
import { Save, Key, Plus, Loader2, Copy, Check, Trash2 } from 'lucide-react';
import { tenantApi, apiKeyApi, type Tenant, type TenantSettings, type ApiKey } from '../lib/api';

export default function Settings() {
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [newKeyValue, setNewKeyValue] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Form state
  const [name, setName] = useState('');
  const [assistantName, setAssistantName] = useState('');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [voiceId, setVoiceId] = useState('');
  const [maxCalls, setMaxCalls] = useState(5);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [tenantData, keysData] = await Promise.all([
          tenantApi.getMe(),
          apiKeyApi.list(),
        ]);
        setTenant(tenantData);
        setApiKeys(keysData);

        // Populate form
        setName(tenantData.name);
        setAssistantName(tenantData.settings.assistant_name);
        setSystemPrompt(tenantData.settings.system_prompt);
        setVoiceId(tenantData.settings.tts_voice_id);
        setMaxCalls(tenantData.settings.max_concurrent_calls);
      } catch (err: any) {
        setError(err.message || 'Failed to load settings');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      const settings: TenantSettings = {
        system_prompt: systemPrompt,
        tts_voice_id: voiceId,
        assistant_name: assistantName,
        max_concurrent_calls: maxCalls,
      };

      const updated = await tenantApi.updateMe({ name, settings });
      setTenant(updated);
      setSuccess('Settings saved successfully');
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.message || 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const handleCreateApiKey = async () => {
    try {
      const result = await apiKeyApi.create('Dashboard Key');
      setNewKeyValue(result.key);
      // Refresh keys list
      const keys = await apiKeyApi.list();
      setApiKeys(keys);
    } catch (err: any) {
      setError(err.message || 'Failed to create API key');
    }
  };

  const handleDeactivateKey = async (keyId: string) => {
    if (!confirm('Are you sure you want to deactivate this API key?')) return;
    try {
      await apiKeyApi.deactivate(keyId);
      const keys = await apiKeyApi.list();
      setApiKeys(keys);
    } catch (err: any) {
      setError(err.message || 'Failed to deactivate API key');
    }
  };

  const handleCopyKey = async (key: string) => {
    await navigator.clipboard.writeText(key);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-500 mt-1">Configure your voice assistant and manage API keys</p>
      </div>

      {/* Messages */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-700 mb-6">
          {error}
        </div>
      )}
      {success && (
        <div className="bg-green-50 border border-green-200 rounded-xl px-4 py-3 text-sm text-green-700 mb-6">
          {success}
        </div>
      )}

      {/* Assistant Settings */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-6">Assistant Configuration</h2>

        <div className="space-y-5">
          {/* Tenant Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Tenant Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>

          {/* Assistant Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Assistant Name</label>
            <input
              type="text"
              value={assistantName}
              onChange={(e) => setAssistantName(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>

          {/* System Prompt */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">System Prompt</label>
            <textarea
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              rows={4}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
              placeholder="Instructions for how the assistant should behave..."
            />
            <p className="text-xs text-gray-400 mt-1">This prompt guides the assistant's personality and behavior during calls.</p>
          </div>

          {/* Voice */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">OpenAI Realtime Voice</label>
            <select
              value={voiceId}
              onChange={(e) => setVoiceId(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            >
              <option value="alloy">Alloy</option>
              <option value="ash">Ash</option>
              <option value="ballad">Ballad</option>
              <option value="coral">Coral</option>
              <option value="echo">Echo</option>
              <option value="sage">Sage</option>
              <option value="shimmer">Shimmer</option>
              <option value="verse">Verse</option>
            </select>
            <p className="text-xs text-gray-400 mt-1">Voice used for the assistant's speech responses via OpenAI Realtime API</p>
          </div>

          {/* Max Concurrent Calls */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Max Concurrent Calls</label>
            <input
              type="number"
              value={maxCalls}
              onChange={(e) => setMaxCalls(parseInt(e.target.value) || 1)}
              min={1}
              max={50}
              className="w-32 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>

          {/* Save Button */}
          <div className="pt-2">
            <button
              onClick={handleSave}
              disabled={saving}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              Save Settings
            </button>
          </div>
        </div>
      </div>

      {/* API Keys */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">API Keys</h2>
            <p className="text-sm text-gray-500 mt-1">Manage API keys for programmatic access</p>
          </div>
          <button
            onClick={handleCreateApiKey}
            className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Create Key
          </button>
        </div>

        {/* New key alert */}
        {newKeyValue && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 mb-4">
            <p className="text-sm font-medium text-amber-800 mb-2">
              New API key created. Copy it now - it won't be shown again!
            </p>
            <div className="flex items-center gap-2">
              <code className="flex-1 bg-white border border-amber-300 rounded px-3 py-1.5 text-sm font-mono text-gray-900 break-all">
                {newKeyValue}
              </code>
              <button
                onClick={() => handleCopyKey(newKeyValue)}
                className="p-2 text-amber-700 hover:text-amber-900 transition-colors"
              >
                {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
              </button>
            </div>
          </div>
        )}

        {/* Keys list */}
        <div className="space-y-3">
          {apiKeys.length === 0 ? (
            <p className="text-sm text-gray-500 text-center py-4">No API keys found</p>
          ) : (
            apiKeys.map((key) => (
              <div key={key.id} className="flex items-center justify-between border border-gray-200 rounded-lg px-4 py-3">
                <div className="flex items-center gap-3">
                  <Key className={`w-4 h-4 ${key.is_active ? 'text-green-500' : 'text-gray-400'}`} />
                  <div>
                    <p className="text-sm font-medium text-gray-900">{key.name}</p>
                    <p className="text-xs text-gray-500 font-mono">{key.key_prefix}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    key.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                  }`}>
                    {key.is_active ? 'Active' : 'Inactive'}
                  </span>
                  {key.is_active && (
                    <button
                      onClick={() => handleDeactivateKey(key.id)}
                      className="p-1.5 text-gray-400 hover:text-red-600 transition-colors"
                      title="Deactivate key"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
