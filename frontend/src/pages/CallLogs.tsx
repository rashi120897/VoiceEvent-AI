import React, { useEffect, useState } from 'react';
import { Phone, PhoneIncoming, PhoneOutgoing, Clock, ChevronDown, ChevronUp } from 'lucide-react';

// Since we don't have a dedicated call logs endpoint with pagination yet,
// we'll show a placeholder that works with the tenant API
export default function CallLogs() {
  const [expandedCall, setExpandedCall] = useState<string | null>(null);

  // Placeholder data structure - in production, this would come from the API
  const [callLogs] = useState<any[]>([]);
  const [loading] = useState(false);

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return '--';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatDate = (date: string) => {
    return new Date(date).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-700';
      case 'in_progress':
        return 'bg-blue-100 text-blue-700';
      case 'failed':
        return 'bg-red-100 text-red-700';
      default:
        return 'bg-gray-100 text-gray-700';
    }
  };

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Call Logs</h1>
        <p className="text-gray-500 mt-1">
          View history and transcripts of voice assistant calls
        </p>
      </div>

      {/* Call Logs Table */}
      <div className="bg-white rounded-xl border border-gray-200">
        {loading ? (
          <div className="flex items-center justify-center h-32">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-600"></div>
          </div>
        ) : callLogs.length === 0 ? (
          <div className="text-center py-16">
            <Phone className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500 text-sm">No calls yet</p>
            <p className="text-gray-400 text-xs mt-1">
              Call logs will appear here once your voice assistant receives its first call
            </p>
          </div>
        ) : (
          <div className="overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead>
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Direction</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Caller</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Duration</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {callLogs.map((call: any) => (
                  <React.Fragment key={call.id}>
                    <tr className="hover:bg-gray-50 transition-colors cursor-pointer"
                        onClick={() => setExpandedCall(expandedCall === call.id ? null : call.id)}>
                      <td className="px-4 py-3">
                        {call.direction === 'inbound' ? (
                          <PhoneIncoming className="w-4 h-4 text-green-500" />
                        ) : (
                          <PhoneOutgoing className="w-4 h-4 text-blue-500" />
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-900">{call.caller_number || 'Unknown'}</td>
                      <td className="px-4 py-3 text-sm text-gray-500">
                        <div className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {formatDuration(call.duration_seconds)}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${getStatusColor(call.status)}`}>
                          {call.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500">{formatDate(call.started_at)}</td>
                      <td className="px-4 py-3 text-right">
                        {expandedCall === call.id ? (
                          <ChevronUp className="w-4 h-4 text-gray-400" />
                        ) : (
                          <ChevronDown className="w-4 h-4 text-gray-400" />
                        )}
                      </td>
                    </tr>

                    {/* Expanded transcript */}
                    {expandedCall === call.id && call.transcript && (
                      <tr>
                        <td colSpan={6} className="px-4 py-4 bg-gray-50">
                          <div className="space-y-3 max-h-64 overflow-y-auto">
                            <p className="text-xs font-medium text-gray-500 uppercase">Transcript</p>
                            {call.transcript.map((entry: any, idx: number) => (
                              <div key={idx} className={`flex gap-3 ${entry.role === 'assistant' ? 'pl-4' : ''}`}>
                                <span className={`text-xs font-medium px-2 py-0.5 rounded ${
                                  entry.role === 'user' ? 'bg-blue-100 text-blue-700' : 'bg-indigo-100 text-indigo-700'
                                }`}>
                                  {entry.role === 'user' ? 'Caller' : 'Assistant'}
                                </span>
                                <p className="text-sm text-gray-700">{entry.content || entry.text}</p>
                              </div>
                            ))}
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
