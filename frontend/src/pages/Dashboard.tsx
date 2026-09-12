import React, { useEffect, useState } from 'react';
import { FileText, Phone, Clock, Activity } from 'lucide-react';
import { tenantApi, documentApi, type Tenant, type DocumentList } from '../lib/api';

export default function Dashboard() {
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [docs, setDocs] = useState<DocumentList | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [tenantData, docsData] = await Promise.all([
          tenantApi.getMe(),
          documentApi.list(),
        ]);
        setTenant(tenantData);
        setDocs(docsData);
      } catch (err) {
        console.error('Failed to fetch dashboard data:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  const stats = [
    {
      label: 'Total Documents',
      value: docs?.total || 0,
      icon: FileText,
      color: 'bg-blue-500',
    },
    {
      label: 'Ready Documents',
      value: docs?.documents.filter((d) => d.status === 'ready').length || 0,
      icon: Activity,
      color: 'bg-green-500',
    },
    {
      label: 'Total Chunks',
      value: docs?.documents.reduce((sum, d) => sum + d.chunk_count, 0) || 0,
      icon: Clock,
      color: 'bg-purple-500',
    },
    {
      label: 'Max Concurrent Calls',
      value: tenant?.settings.max_concurrent_calls || 0,
      icon: Phone,
      color: 'bg-orange-500',
    },
  ];

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 mt-1">
          Welcome back{tenant ? `, ${tenant.name}` : ''}
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.label} className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <div className={`${stat.color} p-2.5 rounded-lg`}>
                  <Icon className="w-5 h-5 text-white" />
                </div>
              </div>
              <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
              <p className="text-sm text-gray-500 mt-1">{stat.label}</p>
            </div>
          );
        })}
      </div>

      {/* Tenant Info */}
      {tenant && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Tenant Information</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-500">Tenant Name</p>
              <p className="text-sm font-medium text-gray-900">{tenant.name}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Assistant Name</p>
              <p className="text-sm font-medium text-gray-900">{tenant.settings.assistant_name}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Status</p>
              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                tenant.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
              }`}>
                {tenant.is_active ? 'Active' : 'Inactive'}
              </span>
            </div>
            <div>
              <p className="text-sm text-gray-500">Created</p>
              <p className="text-sm font-medium text-gray-900">
                {new Date(tenant.created_at).toLocaleDateString()}
              </p>
            </div>
          </div>

          <div className="mt-4 pt-4 border-t border-gray-100">
            <p className="text-sm text-gray-500 mb-1">System Prompt</p>
            <p className="text-sm text-gray-700 bg-gray-50 rounded-lg p-3">
              {tenant.settings.system_prompt}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
