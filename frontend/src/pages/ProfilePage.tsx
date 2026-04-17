import React, { useEffect, useState } from 'react';
import { authService, UserProfile } from '../services/authService';

export const ProfilePage: React.FC = () => {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [pwdMessage, setPwdMessage] = useState('');
  const [mobileOTPEnabled, setMobileOTPEnabled] = useState(true);
  const [emailVerificationEnabled, setEmailVerificationEnabled] = useState(false);
  const [phoneUpdateMessage, setPhoneUpdateMessage] = useState('');
  const [emailVerificationMessage, setEmailVerificationMessage] = useState('');
  const [emailVerificationBusy, setEmailVerificationBusy] = useState(false);
  const [emailVerificationPending, setEmailVerificationPending] = useState(false);
  const [phoneOtpBusy, setPhoneOtpBusy] = useState(false);
  const [newPhone, setNewPhone] = useState('');
  const [phoneOtp, setPhoneOtp] = useState('');
  const [phoneOtpStep, setPhoneOtpStep] = useState<'input' | 'verify'>('input');

  const [formData, setFormData] = useState<UserProfile>({
    id: '',
    username: '',
    email: '',
    role: 'customer',
    full_name: '',
    phone: '',
    address: '',
    address_data: {
      street1: '',
      street2: '',
      landmark: '',
      district: '',
      area: '',
      state: '',
      country: '',
      pincode: '',
      phone: '',
    },
    saved_payment_data: {
      card_holder: '',
      card_last4: '',
      card_brand: '',
      expiry_month: undefined,
      expiry_year: undefined,
      upi_id: '',
    },
  });

  useEffect(() => {
    authService.getMobileOTPConfig()
      .then(cfg => setMobileOTPEnabled(Boolean(cfg.enable_mobile_otp_verification)))
      .catch(() => setMobileOTPEnabled(true));

    authService.getEmailVerificationConfig()
      .then(cfg => setEmailVerificationEnabled(Boolean(cfg.enable_email_verification)))
      .catch(() => setEmailVerificationEnabled(false));

    const loadProfile = async () => {
      try {
        setLoading(true);
        const data = await authService.getProfile();
        setProfile(data);
        setFormData({
          ...formData,
          ...data,
          address_data: {
            ...formData.address_data,
            ...data.address_data,
          },
          saved_payment_data: {
            ...formData.saved_payment_data,
            ...data.saved_payment_data,
          },
        });
        setEmailVerificationPending(!Boolean(data.email_verified));
      } catch (err: any) {
        setMessage(err?.response?.data?.detail || 'Failed to load profile');
      } finally {
        setLoading(false);
      }
    };

    loadProfile();
  }, []);

  const setField = (key: keyof UserProfile, value: any) => {
    setFormData((prev) => ({ ...prev, [key]: value }));
  };

  const setAddressField = (key: string, value: string) => {
    setFormData((prev) => ({
      ...prev,
      address_data: {
        ...(prev.address_data || {}),
        [key]: value,
      },
    }));
  };

  const setPaymentField = (key: string, value: string | number | undefined) => {
    setFormData((prev) => ({
      ...prev,
      saved_payment_data: {
        ...(prev.saved_payment_data || {}),
        [key]: value,
      },
    }));
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMessage('');
    setEmailVerificationMessage('');

    try {
      const response = await authService.updateProfile({
        email: formData.email,
        full_name: formData.full_name,
        phone: mobileOTPEnabled ? undefined : formData.phone,
        address: formData.address,
        address_data: formData.address_data,
        saved_payment_data: formData.saved_payment_data,
      });
      const updated = response.profile;
      setProfile(updated);
      setMessage(response.message || 'Profile updated successfully');
      const pending = Boolean(response.email_verification_pending) || !Boolean(updated?.email_verified);
      setEmailVerificationPending(pending);
      if (pending) {
        setEmailVerificationMessage('Your email is pending verification. Click "Initiate Email Verification" to resend verification.');
      }
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || 'Failed to update profile');
    } finally {
      setSaving(false);
    }
  };

  const handleSendPhoneOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    setPhoneUpdateMessage('');
    if (!newPhone.trim()) {
      setPhoneUpdateMessage('Please enter a new phone number.');
      return;
    }
    setPhoneOtpBusy(true);
    try {
      const result = await authService.sendChangePhoneOTP(newPhone.trim());
      setPhoneUpdateMessage(result.message || 'OTP sent to new phone number.');
      setPhoneOtpStep('verify');
    } catch (err: any) {
      setPhoneUpdateMessage(err?.response?.data?.detail || 'Failed to send OTP for phone change.');
    } finally {
      setPhoneOtpBusy(false);
    }
  };

  const handleVerifyPhoneOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    setPhoneUpdateMessage('');
    if (!phoneOtp.trim()) {
      setPhoneUpdateMessage('Please enter the OTP.');
      return;
    }
    setPhoneOtpBusy(true);
    try {
      const result = await authService.verifyChangePhoneOTP(newPhone.trim(), phoneOtp.trim());
      setPhoneUpdateMessage(result.message || 'Phone number updated successfully.');
      setField('phone', newPhone.trim());
      setPhoneOtp('');
      setPhoneOtpStep('input');
      const refreshed = await authService.getProfile();
      setProfile(refreshed);
      setFormData(prev => ({ ...prev, ...refreshed }));
    } catch (err: any) {
      setPhoneUpdateMessage(err?.response?.data?.detail || 'Failed to verify OTP.');
    } finally {
      setPhoneOtpBusy(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPwdMessage('');
    if (newPassword !== confirmPassword) { setPwdMessage('New passwords do not match'); return; }
    if (newPassword.length < 8) { setPwdMessage('Password must be at least 8 characters long'); return; }
    if (!/[A-Z]/.test(newPassword)) { setPwdMessage('Password must include at least one uppercase letter'); return; }
    if (!/[a-z]/.test(newPassword)) { setPwdMessage('Password must include at least one lowercase letter'); return; }
    if (!/[0-9]/.test(newPassword)) { setPwdMessage('Password must include at least one number'); return; }
    if (!/[^A-Za-z0-9]/.test(newPassword)) { setPwdMessage('Password must include at least one special character'); return; }
    try {
      const result = await authService.changePassword(currentPassword, newPassword);
      setPwdMessage(result.message || 'Password changed');
      setCurrentPassword(''); setNewPassword(''); setConfirmPassword('');
    } catch (err: any) {
      setPwdMessage(err?.response?.data?.detail || 'Failed to change password');
    }
  };

  const handleInitiateEmailVerification = async () => {
    if (!formData.email) {
      setEmailVerificationMessage('Email is required to initiate verification.');
      return;
    }
    setEmailVerificationBusy(true);
    setEmailVerificationMessage('');
    try {
      const result = await authService.sendEmailVerification(formData.email);
      setEmailVerificationPending(true);
      setEmailVerificationMessage(result.message || 'Verification link initiated.');
    } catch (err: any) {
      setEmailVerificationMessage(err?.response?.data?.detail || 'Failed to initiate email verification.');
    } finally {
      setEmailVerificationBusy(false);
    }
  };

  if (loading) {
    return <div className="container" style={{ padding: '40px 0' }}>Loading profile...</div>;
  }

  return (
    <div className="container" style={{ marginTop: '30px', marginBottom: '50px', maxWidth: '900px' }}>
      <h1>My Profile</h1>
      <p style={{ color: '#555' }}>Manage your personal, account, address and saved payment information.</p>
      {message && <div className="alert alert-info">{message}</div>}

      <form onSubmit={handleSave}>
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Account Data</h3>
          <div className="form-group">
            <label>Username</label>
            <input value={formData.username} disabled />
          </div>
          <div className="form-group">
            <label>Email</label>
            <input
              value={formData.email}
              onChange={(e) => setField('email', e.target.value)}
              type="email"
              disabled={!emailVerificationEnabled}
            />
            {!emailVerificationEnabled && <small style={{ color: '#666' }}>Email verification is disabled by company configuration.</small>}
          </div>
          <div className="form-group">
            <label>Role</label>
            <input value={formData.role} disabled />
          </div>
        </div>

        {emailVerificationEnabled && (
          <div className="card">
            <h3 style={{ marginTop: 0 }}>Email Verification</h3>
            {emailVerificationPending && (
              <div className="alert" style={{ background: '#fff3cd', color: '#856404', border: '1px solid #ffeeba' }}>
                Email verification is pending for <strong>{formData.email}</strong>.
              </div>
            )}
            {emailVerificationMessage && <div className="alert alert-info">{emailVerificationMessage}</div>}
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleInitiateEmailVerification}
              disabled={emailVerificationBusy}
            >
              {emailVerificationBusy ? 'Initiating...' : 'Initiate Email Verification'}
            </button>
          </div>
        )}

        <div className="card">
          <h3 style={{ marginTop: 0 }}>Personal Data</h3>
          <div className="form-group">
            <label>Full Name</label>
            <input value={formData.full_name || ''} onChange={(e) => setField('full_name', e.target.value)} />
          </div>
          <div className="form-group">
            <label>Phone {mobileOTPEnabled && <span style={{ color: '#666', fontSize: 12 }}>(read-only when OTP verification is enabled)</span>}</label>
            <input value={formData.phone || ''} onChange={(e) => setField('phone', e.target.value)} disabled={mobileOTPEnabled} />
          </div>
        </div>

        {mobileOTPEnabled && (
          <div className="card">
            <h3 style={{ marginTop: 0 }}>Change Phone Number (OTP Verification)</h3>
            {phoneUpdateMessage && <div className="alert alert-info">{phoneUpdateMessage}</div>}

            {phoneOtpStep === 'input' && (
              <form onSubmit={handleSendPhoneOTP}>
                <div className="form-group">
                  <label>New Phone Number</label>
                  <input value={newPhone} onChange={(e) => setNewPhone(e.target.value)} placeholder="Enter new phone number" required />
                </div>
                <button type="submit" className="btn btn-secondary" disabled={phoneOtpBusy}>
                  {phoneOtpBusy ? 'Sending OTP...' : 'Send OTP'}
                </button>
              </form>
            )}

            {phoneOtpStep === 'verify' && (
              <form onSubmit={handleVerifyPhoneOTP}>
                <div className="form-group">
                  <label>OTP</label>
                  <input value={phoneOtp} onChange={(e) => setPhoneOtp(e.target.value)} placeholder="Enter OTP" required maxLength={6} />
                </div>
                <button type="submit" className="btn btn-secondary" disabled={phoneOtpBusy} style={{ marginRight: 8 }}>
                  {phoneOtpBusy ? 'Verifying...' : 'Verify OTP'}
                </button>
                <button type="button" className="btn btn-light" onClick={() => { setPhoneOtpStep('input'); setPhoneOtp(''); }}>
                  Back
                </button>
              </form>
            )}
          </div>
        )}

        <div className="card">
          <h3 style={{ marginTop: 0 }}>Address Data</h3>
          <div className="form-group">
            <label>Address (single line)</label>
            <input value={formData.address || ''} onChange={(e) => setField('address', e.target.value)} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div className="form-group"><label>Street 1</label>
              <input value={formData.address_data?.street1 || ''} onChange={(e) => setAddressField('street1', e.target.value)} />
            </div>
            <div className="form-group"><label>Street 2</label>
              <input value={formData.address_data?.street2 || ''} onChange={(e) => setAddressField('street2', e.target.value)} />
            </div>
            <div className="form-group"><label>Landmark</label>
              <input value={formData.address_data?.landmark || ''} onChange={(e) => setAddressField('landmark', e.target.value)} />
            </div>
            <div className="form-group"><label>District</label>
              <input value={formData.address_data?.district || ''} onChange={(e) => setAddressField('district', e.target.value)} />
            </div>
            <div className="form-group"><label>Area / Town / Region</label>
              <input value={formData.address_data?.area || ''} onChange={(e) => setAddressField('area', e.target.value)} />
            </div>
            <div className="form-group"><label>State</label>
              <input value={formData.address_data?.state || ''} onChange={(e) => setAddressField('state', e.target.value)} />
            </div>
            <div className="form-group"><label>Country</label>
              <input value={formData.address_data?.country || ''} onChange={(e) => setAddressField('country', e.target.value)} />
            </div>
            <div className="form-group"><label>PIN Code</label>
              <input value={formData.address_data?.pincode || ''} onChange={(e) => setAddressField('pincode', e.target.value)} />
            </div>
            <div className="form-group"><label>Phone</label>
              <input value={formData.address_data?.phone || ''} onChange={(e) => setAddressField('phone', e.target.value)} />
            </div>
          </div>
        </div>

        <div className="card">
          <h3 style={{ marginTop: 0 }}>Saved Payment Data</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div className="form-group"><label>Card Holder</label>
              <input value={formData.saved_payment_data?.card_holder || ''} onChange={(e) => setPaymentField('card_holder', e.target.value)} />
            </div>
            <div className="form-group"><label>Card Brand</label>
              <input value={formData.saved_payment_data?.card_brand || ''} onChange={(e) => setPaymentField('card_brand', e.target.value)} />
            </div>
            <div className="form-group"><label>Card Last 4</label>
              <input value={formData.saved_payment_data?.card_last4 || ''} maxLength={4} onChange={(e) => setPaymentField('card_last4', e.target.value.replace(/\D/g, ''))} />
            </div>
            <div className="form-group"><label>UPI ID</label>
              <input value={formData.saved_payment_data?.upi_id || ''} onChange={(e) => setPaymentField('upi_id', e.target.value)} />
            </div>
            <div className="form-group"><label>Expiry Month</label>
              <input
                type="number"
                min={1}
                max={12}
                value={formData.saved_payment_data?.expiry_month || ''}
                onChange={(e) => setPaymentField('expiry_month', e.target.value ? Number(e.target.value) : undefined)}
              />
            </div>
            <div className="form-group"><label>Expiry Year</label>
              <input
                type="number"
                min={2026}
                value={formData.saved_payment_data?.expiry_year || ''}
                onChange={(e) => setPaymentField('expiry_year', e.target.value ? Number(e.target.value) : undefined)}
              />
            </div>
          </div>
        </div>

        <button type="submit" className="btn btn-primary" disabled={saving}>
          {saving ? 'Saving...' : 'Save Profile'}
        </button>
      </form>

      {formData.role !== 'admin' && (
        <div className="card" style={{ marginTop: '20px' }}>
          <h3 style={{ marginTop: 0 }}>Change Password</h3>
          {pwdMessage && <div className="alert alert-info">{pwdMessage}</div>}
          <form onSubmit={handleChangePassword}>
            <div className="form-group">
              <label>Current Password</label>
              <input type="password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} required />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div className="form-group">
                <label>New Password</label>
                <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required minLength={8} />
                <small style={{ color: '#666' }}>Use at least 8 chars with uppercase, lowercase, number, and special character.</small>
              </div>
              <div className="form-group">
                <label>Confirm New Password</label>
                <input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} required minLength={8} />
              </div>
            </div>
            <button type="submit" className="btn btn-secondary">Change Password</button>
          </form>
        </div>
      )}

      {profile?.updated_at && (
        <p style={{ marginTop: '16px', color: '#666' }}>Last updated: {new Date(profile.updated_at).toLocaleString()}</p>
      )}
    </div>
  );
};
