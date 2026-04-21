import React, { useState, useRef, useEffect } from 'react';
import { AdminStats } from '../components/AdminStats';
import { adminService } from '../services/adminService';
import api from '../services/api';

export const AdminDashboardPage: React.FC = () => {
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [packageOption, setPackageOption] = useState<string>('');
  const fileRef = useRef<HTMLInputElement>(null);

  // Payment gateways state
  const [pgMessage, setPgMessage] = useState('');
  const [pgBusy, setPgBusy] = useState(false);
  const [razorpayKeyId, setRazorpayKeyId] = useState('');
  const [razorpayKeySecret, setRazorpayKeySecret] = useState('');
  const [showSecret, setShowSecret] = useState(false);

  // Company configuration (MSG91) state
  const [ccMessage, setCcMessage] = useState('');
  const [ccBusy, setCcBusy] = useState(false);
  const [msg91Authkey, setMsg91Authkey] = useState('');
  const [msg91TemplateId, setMsg91TemplateId] = useState('');
  const [msg91SenderId, setMsg91SenderId] = useState('AIESHP');
  const [enableMobileOTPVerification, setEnableMobileOTPVerification] = useState(true);
  const [enableEmailVerification, setEnableEmailVerification] = useState(false);
  const [showAuthkey, setShowAuthkey] = useState(false);

  useEffect(() => {
    api.get('/config/package-option').then(res => {
      setPackageOption(res.data?.package_option || 'prod');
    }).catch(() => setPackageOption('prod'));

    // Load existing Razorpay config
    adminService.getPaymentGateway('razorpay').then(cfg => {
      setRazorpayKeyId(cfg.key_id || '');
      setRazorpayKeySecret(cfg.key_secret || '');
    }).catch(() => {});

    // Load existing MSG91 config
    adminService.getMsg91Config().then(cfg => {
      setMsg91Authkey(cfg.authkey || '');
      setMsg91TemplateId(cfg.template_id || '');
      setMsg91SenderId(cfg.sender_id || 'AIESHP');
      setEnableMobileOTPVerification(Boolean(cfg.enable_mobile_otp_verification));
    }).catch(() => {});

    adminService.getMiscConfig().then(cfg => {
      setEnableEmailVerification(Boolean(cfg.enable_email_verification));
    }).catch(() => {});
  }, []);

  const handleSaveRazorpay = async () => {
    setPgBusy(true);
    setPgMessage('');
    try {
      const result = await adminService.updatePaymentGateway('razorpay', {
        key_id: razorpayKeyId,
        key_secret: razorpayKeySecret,
      });
      setPgMessage(result.message || 'Razorpay configuration saved.');
    } catch (err: any) {
      setPgMessage(err?.response?.data?.detail || 'Failed to save Razorpay configuration.');
    } finally {
      setPgBusy(false);
    }
  };

  const handleSaveMsg91 = async () => {
    setCcBusy(true);
    setCcMessage('');
    try {
      const result = await adminService.updateMsg91Config({
        authkey: msg91Authkey,
        template_id: msg91TemplateId,
        sender_id: msg91SenderId,
        enable_mobile_otp_verification: enableMobileOTPVerification,
      });
      setCcMessage(result.message || 'MSG91 configuration saved.');
    } catch (err: any) {
      setCcMessage(err?.response?.data?.detail || 'Failed to save MSG91 configuration.');
    } finally {
      setCcBusy(false);
    }
  };

  const handleSaveMisc = async () => {
    setCcBusy(true);
    setCcMessage('');
    try {
      const result = await adminService.updateMiscConfig({
        enable_email_verification: enableEmailVerification,
      });
      setCcMessage(result.message || 'Misc configuration saved.');
    } catch (err: any) {
      setCcMessage(err?.response?.data?.detail || 'Failed to save misc configuration.');
    } finally {
      setCcBusy(false);
    }
  };

  const handleLoadSample = async () => {
    if (!window.confirm('Load sample data into database?')) return;
    setBusy(true);
    try {
      const result = await adminService.loadSampleData();
      setMessage(result.message || 'Sample data loaded');
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || 'Failed to load sample data');
    } finally {
      setBusy(false);
    }
  };

  const handleDiscardSample = async () => {
    if (!window.confirm('Discard sample data using sample index?')) return;
    setBusy(true);
    try {
      const result = await adminService.discardSampleData();
      setMessage(result.message || 'Sample data discarded');
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || 'Failed to discard sample data');
    } finally {
      setBusy(false);
    }
  };

  const handleBrandUpload = async () => {
    const file = fileRef.current?.files?.[0];
    if (!file) { setMessage('Please select a file'); return; }
    setBusy(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const resp = await api.post('/brand/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      window.dispatchEvent(new Event('company-image-updated'));
      setMessage(resp.data?.message || 'Company image uploaded.');
      if (fileRef.current) fileRef.current.value = '';
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || 'Failed to upload company image');
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <h1 style={{ marginTop: 0, marginBottom: 16 }}>Admin Dashboard</h1>
      {message && <div className="alert alert-info">{message}</div>}
      <AdminStats />

      <div className="admin-cards-grid" style={{ marginTop: 20 }}>
        <div className="card">
          <h3>Company Image</h3>
          <p style={{ color: '#666', fontSize: 13 }}>Upload a new company logo (SVG, PNG, JPG, WebP, max 5 MB). It will replace the current company image across the site.</p>
          <input type="file" ref={fileRef} accept=".svg,.png,.jpg,.jpeg,.webp" style={{ marginBottom: 8, display: 'block' }} />
          <button className="btn btn-primary" style={{ width: '100%' }} onClick={handleBrandUpload} disabled={busy}>Upload Company Image</button>
        </div>
        {packageOption && packageOption !== 'prod' && (
          <div className="card">
            <h3>Sample Data ({packageOption})</h3>
            <p style={{ color: '#666', fontSize: 13 }}>Use only in non-production environments.</p>
            <button className="btn btn-secondary" style={{ width: '100%', marginBottom: 8 }} onClick={handleLoadSample} disabled={busy}>Load Sample Data</button>
            <button className="btn" style={{ width: '100%', backgroundColor: '#dc3545', color: '#fff' }} onClick={handleDiscardSample} disabled={busy}>Discard Sample Data</button>
          </div>
        )}
      </div>

      {/* Payment Gateways */}
      <div style={{ marginTop: 24 }}>
        <h2 style={{ marginBottom: 12 }}>Payment Gateways</h2>
        {pgMessage && (
          <div className={`alert ${pgMessage.toLowerCase().includes('fail') || pgMessage.toLowerCase().includes('error') ? 'alert-danger' : 'alert-info'}`} style={{ marginBottom: 12 }}>
            {pgMessage}
          </div>
        )}
        <div className="card">
          <div style={{ borderLeft: '4px solid #528FF0', paddingLeft: 16 }}>
            <h4 style={{ marginBottom: 12, color: '#333' }}>Razorpay</h4>
            <div style={{ marginBottom: 12 }}>
              <label style={{ display: 'block', fontWeight: 600, marginBottom: 4, fontSize: 14 }}>Key ID</label>
              <input
                type="text"
                className="form-control"
                value={razorpayKeyId}
                onChange={e => setRazorpayKeyId(e.target.value)}
                placeholder="rzp_test_XXXXXXXXXXXX"
                style={{ width: '100%', maxWidth: 480 }}
              />
            </div>
            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', fontWeight: 600, marginBottom: 4, fontSize: 14 }}>Key Secret</label>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, maxWidth: 480 }}>
                <input
                  type={showSecret ? 'text' : 'password'}
                  className="form-control"
                  value={razorpayKeySecret}
                  onChange={e => setRazorpayKeySecret(e.target.value)}
                  placeholder="Your Razorpay key secret"
                  style={{ flex: 1 }}
                />
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ whiteSpace: 'nowrap', padding: '6px 12px', fontSize: 13 }}
                  onClick={() => setShowSecret(v => !v)}
                >
                  {showSecret ? 'Hide' : 'Show'}
                </button>
              </div>
            </div>
            <button
              className="btn btn-primary"
              onClick={handleSaveRazorpay}
              disabled={pgBusy}
              style={{ minWidth: 160 }}
            >
              {pgBusy ? 'Saving…' : 'Save Razorpay Settings'}
            </button>
          </div>
        </div>
      </div>

      {/* Company Configuration */}
      <div style={{ marginTop: 24 }}>
        <h2 style={{ marginBottom: 12 }}>Company Configuration</h2>
        {ccMessage && (
          <div className={`alert ${ccMessage.toLowerCase().includes('fail') || ccMessage.toLowerCase().includes('error') ? 'alert-danger' : 'alert-info'}`} style={{ marginBottom: 12 }}>
            {ccMessage}
          </div>
        )}
        <div className="card">
          <div style={{ borderLeft: '4px solid #28a745', paddingLeft: 16 }}>
            <h4 style={{ marginBottom: 4, color: '#333' }}>MSG91 — OTP / SMS</h4>
            <p style={{ color: '#666', fontSize: 13, marginBottom: 16 }}>
              Credentials for MSG91 OTP delivery. Obtain these from{' '}
              <a href="https://msg91.com" target="_blank" rel="noreferrer">msg91.com</a>.
              Leave blank to use console-log mode (dev only).
            </p>
            <div style={{ marginBottom: 12 }}>
              <label style={{ display: 'block', fontWeight: 600, marginBottom: 4, fontSize: 14 }}>Auth Key</label>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, maxWidth: 480 }}>
                <input
                  type={showAuthkey ? 'text' : 'password'}
                  className="form-control"
                  value={msg91Authkey}
                  onChange={e => setMsg91Authkey(e.target.value)}
                  placeholder="Your MSG91 Auth Key"
                  style={{ flex: 1 }}
                />
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ whiteSpace: 'nowrap', padding: '6px 12px', fontSize: 13 }}
                  onClick={() => setShowAuthkey(v => !v)}
                >
                  {showAuthkey ? 'Hide' : 'Show'}
                </button>
              </div>
            </div>
            <div style={{ marginBottom: 12 }}>
              <label style={{ display: 'block', fontWeight: 600, marginBottom: 4, fontSize: 14 }}>OTP Template ID</label>
              <input
                type="text"
                className="form-control"
                value={msg91TemplateId}
                onChange={e => setMsg91TemplateId(e.target.value)}
                placeholder="DLT-approved template ID from MSG91"
                style={{ width: '100%', maxWidth: 480 }}
              />
              <span style={{ fontSize: 12, color: '#888' }}>
                The template must contain <code>{'{{otp}}'}</code> and be approved on the DLT portal.
              </span>
            </div>
            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', fontWeight: 600, marginBottom: 4, fontSize: 14 }}>Mobile OTP Verification</label>
              <label style={{ display: 'inline-flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={enableMobileOTPVerification}
                  onChange={e => setEnableMobileOTPVerification(e.target.checked)}
                />
                <span style={{ fontSize: 14 }}>
                  Enable mobile OTP verification in registration and profile phone-change flows
                </span>
              </label>
            </div>
            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', fontWeight: 600, marginBottom: 4, fontSize: 14 }}>Sender ID</label>
              <input
                type="text"
                className="form-control"
                value={msg91SenderId}
                onChange={e => setMsg91SenderId(e.target.value)}
                placeholder="6-char sender ID e.g. AIESHP"
                maxLength={6}
                style={{ width: '100%', maxWidth: 200 }}
              />
            </div>
            <button
              className="btn btn-primary"
              onClick={handleSaveMsg91}
              disabled={ccBusy}
              style={{ minWidth: 180 }}
            >
              {ccBusy ? 'Saving…' : 'Save MSG91 Settings'}
            </button>
          </div>

          <div style={{ borderLeft: '4px solid #17a2b8', paddingLeft: 16, marginTop: 20 }}>
            <h4 style={{ marginBottom: 4, color: '#333' }}>Misc. Config</h4>
            <p style={{ color: '#666', fontSize: 13, marginBottom: 16 }}>
              General authentication switches independent of mobile OTP.
            </p>
            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', fontWeight: 600, marginBottom: 4, fontSize: 14 }}>Email Verification</label>
              <label style={{ display: 'inline-flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={enableEmailVerification}
                  onChange={e => setEnableEmailVerification(e.target.checked)}
                />
                <span style={{ fontSize: 14 }}>
                  Require and initiate email verification for new registrations and changed profile emails
                </span>
              </label>
            </div>
            <button
              className="btn btn-primary"
              onClick={handleSaveMisc}
              disabled={ccBusy}
              style={{ minWidth: 180 }}
            >
              {ccBusy ? 'Saving…' : 'Save Misc Settings'}
            </button>
          </div>
        </div>
      </div>
    </>
  );
};
