import React, { useState, useEffect } from 'react';
import { apiService } from '../lib/api';
import { Button } from './ui/button';
import { RefreshCw, CheckCircle, AlertCircle, Info } from 'lucide-react';

interface SystemStatus {
  status: string;
  components: {
    vector_db: boolean;
    chatbot: boolean;
    llm_service: boolean;
    azure_service: boolean;
  };
  configuration: {
    vector_db_type: string;
    embedding_model: string;
    max_context_chunks: number;
    enable_citations: boolean;
    enable_context_expansion: boolean;
  };
}

export function SystemStatus() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadStatus = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getSystemStatus();
      setStatus(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load system status');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStatus();
  }, []);

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mr-4" />
          Loading system status...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center gap-3">
            <AlertCircle className="text-red-600" size={20} />
            <span className="text-red-800">Error: {error}</span>
          </div>
          <Button onClick={loadStatus} className="mt-4" variant="outline">
            <RefreshCw size={16} className="mr-2" />
            Retry
          </Button>
        </div>
      </div>
    );
  }

  const getStatusColor = (isHealthy: boolean) => {
    return isHealthy ? 'text-green-600' : 'text-red-600';
  };

  const getStatusIcon = (isHealthy: boolean) => {
    return isHealthy ? <CheckCircle size={20} /> : <AlertCircle size={20} />;
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">System Status</h2>
          <p className="text-muted-foreground">
            Monitor the health and configuration of system components
          </p>
        </div>
        <Button onClick={loadStatus} variant="outline">
          <RefreshCw size={16} className="mr-2" />
          Refresh
        </Button>
      </div>

      {/* Overall Status */}
      <div className="bg-card rounded-lg border p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className={getStatusColor(status?.status === 'ready')}>
            {getStatusIcon(status?.status === 'ready')}
          </div>
          <h3 className="text-lg font-semibold">Overall System Status</h3>
        </div>
        <div className={`text-sm font-medium ${getStatusColor(status?.status === 'ready')}`}>
          {status?.status === 'ready' ? 'System Ready' : 'System Not Ready'}
        </div>
      </div>

      {/* Components Status */}
      <div className="bg-card rounded-lg border p-6">
        <h3 className="text-lg font-semibold mb-4">Components</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {status && Object.entries(status.components).map(([component, isHealthy]) => (
            <div key={component} className="flex items-center justify-between p-3 bg-muted rounded-lg">
              <span className="font-medium capitalize">
                {component.replace('_', ' ')}
              </span>
              <div className={`flex items-center gap-2 ${getStatusColor(isHealthy)}`}>
                {getStatusIcon(isHealthy)}
                <span className="text-sm">{isHealthy ? 'Active' : 'Inactive'}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Configuration */}
      <div className="bg-card rounded-lg border p-6">
        <h3 className="text-lg font-semibold mb-4">Configuration</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {status && Object.entries(status.configuration).map(([key, value]) => (
            <div key={key} className="p-3 bg-muted rounded-lg">
              <div className="text-sm font-medium text-muted-foreground capitalize mb-1">
                {key.replace(/_/g, ' ')}
              </div>
              <div className="font-medium">
                {typeof value === 'boolean' ? (value ? 'Enabled' : 'Disabled') : String(value)}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* System Information */}
      <div className="bg-card rounded-lg border p-6">
        <div className="flex items-center gap-3 mb-4">
          <Info size={20} className="text-primary" />
          <h3 className="text-lg font-semibold">System Information</h3>
        </div>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Backend API:</span>
            <span>Flask REST API</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Frontend:</span>
            <span>React with Assistant UI</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Vector Database:</span>
            <span>{status?.configuration.vector_db_type || 'Unknown'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Embedding Model:</span>
            <span>{status?.configuration.embedding_model || 'Unknown'}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
