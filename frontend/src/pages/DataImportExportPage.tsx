import React, { useEffect, useMemo, useState } from 'react';
import { ProtectedRoute } from '../components/ProtectedRoute';
import { adminService, DataSyncJob } from '../services/adminService';

const ENTITY_LABELS: Record<string, string> = {
  vendor: 'Vendor',
  customer: 'Customer',
  product_category: 'Product Category',
  product_master: 'Product Master',
};

const DEFAULT_ENTITIES = ['vendor', 'customer', 'product_category', 'product_master'];

export const DataImportExportPage: React.FC = () => {
  const [entities, setEntities] = useState<string[]>(DEFAULT_ENTITIES);
  const [importEntity, setImportEntity] = useState<string>(DEFAULT_ENTITIES[0]);
  const [exportEntity, setExportEntity] = useState<string>(DEFAULT_ENTITIES[0]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [jobs, setJobs] = useState<DataSyncJob[]>([]);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  const refreshJobs = async () => {
    try {
      const data = await adminService.listDataSyncJobs(0, 40);
      setJobs(data);
    } catch {
      // no-op
    }
  };

  useEffect(() => {
    adminService.listDataSyncEntities()
      .then((data) => {
        const loaded = data.entities?.length ? data.entities : DEFAULT_ENTITIES;
        setEntities(loaded);
        setImportEntity((prev) => loaded.includes(prev) ? prev : loaded[0]);
        setExportEntity((prev) => loaded.includes(prev) ? prev : loaded[0]);
      })
      .catch(() => {
        setEntities(DEFAULT_ENTITIES);
      });

    refreshJobs();
  }, []);

  useEffect(() => {
    const timer = window.setInterval(() => {
      refreshJobs();
    }, 3000);

    return () => {
      window.clearInterval(timer);
    };
  }, []);

  const handleImportSubmit = async () => {
    if (!selectedFile) {
      setMessage('Please choose a CSV file for import.');
      return;
    }

    setBusy(true);
    setMessage('');
    try {
      const result = await adminService.createImportJob(importEntity, selectedFile);
      setMessage(`Import queued for ${ENTITY_LABELS[result.entity] || result.entity}. Job ID: ${result.job_id}`);
      setSelectedFile(null);
      const fileInput = document.getElementById('import-file-input') as HTMLInputElement | null;
      if (fileInput) fileInput.value = '';
      refreshJobs();
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || 'Failed to queue import job.');
    } finally {
      setBusy(false);
    }
  };

  const handleExportSubmit = async () => {
    setBusy(true);
    setMessage('');
    try {
      const result = await adminService.createExportJob(exportEntity);
      setMessage(`Export queued for ${ENTITY_LABELS[result.entity] || result.entity}. Job ID: ${result.job_id}`);
      refreshJobs();
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || 'Failed to queue export job.');
    } finally {
      setBusy(false);
    }
  };

  const handleDownload = async (job: DataSyncJob) => {
    try {
      const blob = await adminService.downloadExportJob(job.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${job.entity}_export_${job.id}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      setMessage('Failed to download export CSV.');
    }
  };

  const handleDownloadTemplate = async (entity: string) => {
    try {
      const blob = await adminService.downloadTemplate(entity);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${entity}_template.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      setMessage('Failed to download CSV template.');
    }
  };

  const handleDownloadErrorReport = async (job: DataSyncJob) => {
    try {
      const blob = await adminService.downloadErrorReport(job.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${job.entity}_import_errors_${job.id}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      setMessage('Failed to download error report.');
    }
  };

  const statusColor = (status: string) => {
    if (status === 'completed') return '#0f6b2a';
    if (status === 'completed_with_errors') return '#8a5800';
    if (status === 'failed') return '#8f1d1d';
    return '#1f5f8f';
  };

  const sortedJobs = useMemo(() => {
    return [...jobs].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  }, [jobs]);

  return (
    <ProtectedRoute requiredRole="admin">
      <div className="container" style={{ marginTop: 30, marginBottom: 40 }}>
        <h1>Data Import - Export</h1>
        <p style={{ color: '#5b6d78' }}>
          Asynchronous CSV jobs for vendor, customer, product category, and product master entities.
        </p>

        {message && <div className="alert alert-info">{message}</div>}

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 16, marginBottom: 18 }}>
          <div className="card" style={{ border: '1px solid #d8e3ea', borderRadius: 12 }}>
            <h3 style={{ marginTop: 0 }}>Data Import</h3>
            <label style={{ display: 'block', marginBottom: 8, fontWeight: 600 }}>Target table</label>
            <select className="form-input" value={importEntity} onChange={(e) => setImportEntity(e.target.value)} style={{ marginBottom: 10 }}>
              {entities.map((entity) => (
                <option key={entity} value={entity}>{ENTITY_LABELS[entity] || entity}</option>
              ))}
            </select>

            <label style={{ display: 'block', marginBottom: 8, fontWeight: 600 }}>CSV file</label>
            <input
              id="import-file-input"
              type="file"
              accept=".csv"
              onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
              style={{ display: 'block', marginBottom: 12 }}
            />

            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn btn-primary" onClick={handleImportSubmit} disabled={busy}>
                {busy ? 'Submitting...' : 'Start Import'}
              </button>
              <button className="btn btn-secondary" onClick={() => handleDownloadTemplate(importEntity)}>
                Download Template
              </button>
            </div>
          </div>

          <div className="card" style={{ border: '1px solid #d8e3ea', borderRadius: 12 }}>
            <h3 style={{ marginTop: 0 }}>Data Export</h3>
            <label style={{ display: 'block', marginBottom: 8, fontWeight: 600 }}>Target table</label>
            <select className="form-input" value={exportEntity} onChange={(e) => setExportEntity(e.target.value)} style={{ marginBottom: 12 }}>
              {entities.map((entity) => (
                <option key={entity} value={entity}>{ENTITY_LABELS[entity] || entity}</option>
              ))}
            </select>

            <button className="btn btn-primary" onClick={handleExportSubmit} disabled={busy}>
              {busy ? 'Submitting...' : 'Start Export'}
            </button>
          </div>
        </div>

        <div className="card" style={{ border: '1px solid #d8e3ea', borderRadius: 12 }}>
          <h3 style={{ marginTop: 0 }}>Import / Export Job Status</h3>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', minWidth: 840, borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: '#eef5fa' }}>
                  <th style={{ textAlign: 'left', padding: 10 }}>Created</th>
                  <th style={{ textAlign: 'left', padding: 10 }}>Entity</th>
                  <th style={{ textAlign: 'left', padding: 10 }}>Type</th>
                  <th style={{ textAlign: 'left', padding: 10 }}>Status</th>
                  <th style={{ textAlign: 'left', padding: 10 }}>Processed</th>
                  <th style={{ textAlign: 'left', padding: 10 }}>Success</th>
                  <th style={{ textAlign: 'left', padding: 10 }}>Failed</th>
                  <th style={{ textAlign: 'left', padding: 10 }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {sortedJobs.map((job) => (
                  <tr key={job.id} style={{ borderTop: '1px solid #edf1f4' }}>
                    <td style={{ padding: 10 }}>{new Date(job.created_at).toLocaleString()}</td>
                    <td style={{ padding: 10 }}>{ENTITY_LABELS[job.entity] || job.entity}</td>
                    <td style={{ padding: 10 }}>{job.job_type}</td>
                    <td style={{ padding: 10, color: statusColor(job.status), fontWeight: 700 }}>{job.status}</td>
                    <td style={{ padding: 10 }}>{job.processed_rows}</td>
                    <td style={{ padding: 10 }}>{job.success_rows}</td>
                    <td style={{ padding: 10 }}>{job.failed_rows}</td>
                    <td style={{ padding: 10 }}>
                      {job.job_type === 'export' && (job.status === 'completed' || job.status === 'completed_with_errors') ? (
                        <button className="btn btn-secondary" onClick={() => handleDownload(job)}>Download CSV</button>
                      ) : job.job_type === 'import' && (job.status === 'completed_with_errors' || job.status === 'failed') && job.failed_rows > 0 ? (
                        <button className="btn btn-secondary" style={{ color: '#8a5800' }} onClick={() => handleDownloadErrorReport(job)}>Error Report</button>
                      ) : (
                        <span style={{ color: '#6c757d' }}>-</span>
                      )}
                    </td>
                  </tr>
                ))}
                {sortedJobs.length === 0 && (
                  <tr>
                    <td colSpan={8} style={{ padding: 14, color: '#6c757d' }}>No jobs submitted yet.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
};
