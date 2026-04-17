import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { authService } from '../services/authService';

interface RegisterPageProps {
  onRegisterSuccess: () => void;
}

type Step = 'details' | 'otp' | 'success';

const toErrorMessage = (err: any): string => {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return (
      detail.map((item: any) => item?.msg || item?.message).filter(Boolean).join(', ') ||
      'Please check your input.'
    );
  }
  return 'Something went wrong. Please try again.';
};

export const RegisterPage: React.FC<RegisterPageProps> = ({ onRegisterSuccess }) => {
  const navigate = useNavigate();
  const [mobileOTPEnabled, setMobileOTPEnabled] = useState(true);
  const [emailVerificationEnabled, setEmailVerificationEnabled] = useState(false);
  const [emailVerificationPending, setEmailVerificationPending] = useState(false);
  const [step, setStep] = useState<Step>('details');
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    full_name: '',
    phone: '',
    dob: '',
  });
  const [otp, setOtp] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [otpInfo, setOtpInfo] = useState<{ phone: string; expires_at: string } | null>(null);

  React.useEffect(() => {
    authService.getMobileOTPConfig()
      .then(cfg => setMobileOTPEnabled(Boolean(cfg.enable_mobile_otp_verification)))
      .catch(() => setMobileOTPEnabled(true));

    authService.getEmailVerificationConfig()
      .then(cfg => setEmailVerificationEnabled(Boolean(cfg.enable_email_verification)))
      .catch(() => setEmailVerificationEnabled(false));
  }, []);

  const getStrongPasswordError = (password: string): string | null => {
    if (password.length < 8) return 'Password must be at least 8 characters long.';
    if (!/[A-Z]/.test(password)) return 'Password must include at least one uppercase letter.';
    if (!/[a-z]/.test(password)) return 'Password must include at least one lowercase letter.';
    if (!/[0-9]/.test(password)) return 'Password must include at least one number.';
    if (!/[^A-Za-z0-9]/.test(password)) return 'Password must include at least one special character.';
    return null;
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSendOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    const strongPasswordError = getStrongPasswordError(formData.password);
    if (strongPasswordError) {
      setError(strongPasswordError);
      return;
    }
    setLoading(true);
    try {
      if (mobileOTPEnabled) {
        const res = await authService.sendRegistrationOTP({
          username: formData.username,
          email: formData.email,
          full_name: formData.full_name,
          phone: formData.phone,
          dob: formData.dob,
          password: formData.password,
        });
        setEmailVerificationPending(Boolean(res?.email_verification_pending));
        setOtpInfo({ phone: res.phone, expires_at: res.expires_at });
        setStep('otp');
      } else {
        const res = await authService.register(
          formData.username,
          formData.email,
          formData.password,
          formData.full_name,
          formData.phone,
          formData.dob,
        );
        setEmailVerificationPending(Boolean(res?.email_verification_pending));
        setStep('success');
      }
    } catch (err: any) {
      setError(toErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await authService.verifyRegistrationOTP({
        username: formData.username,
        email: formData.email,
        full_name: formData.full_name,
        phone: formData.phone,
        dob: formData.dob,
        password: formData.password,
        otp,
      });
      setEmailVerificationPending(Boolean(res?.email_verification_pending));
      setStep('success');
    } catch (err: any) {
      setError(toErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container" style={{ maxWidth: '440px', margin: '50px auto' }}>
      <div className="card">
        <h2 style={{ textAlign: 'center', marginBottom: '30px' }}>Create Account</h2>

        {step === 'success' && (
          <div>
            <div className="alert" style={{ background: '#d4edda', color: '#155724', border: '1px solid #c3e6cb', borderRadius: 4, padding: '12px 16px', marginBottom: 20 }}>
              <strong>Registration successful!</strong><br />
              Welcome to Hutt. Hutt is open 24/7 all day!!. Have fun
              {emailVerificationEnabled && emailVerificationPending && (
                <>
                  <br />
                  <span>Your email verification is pending. Please complete it from your profile.</span>
                </>
              )}
            </div>
            <button className="btn btn-primary" style={{ width: '100%' }} onClick={() => navigate('/login', { replace: true })}>
              Go to Login
            </button>
          </div>
        )}

        {step === 'details' && (
          <form onSubmit={handleSendOTP}>
            {error && <div className="alert alert-danger">{error}</div>}
            <div className="form-group">
              <label>Full Name <span style={{ color: 'red' }}>*</span></label>
              <input type="text" name="full_name" value={formData.full_name} onChange={handleChange} placeholder="John Doe" required minLength={1} />
            </div>
            <div className="form-group">
              <label>Username <span style={{ color: 'red' }}>*</span></label>
              <input type="text" name="username" value={formData.username} onChange={handleChange} required minLength={3} maxLength={50} />
            </div>
            <div className="form-group">
              <label>Email</label>
              <input type="email" name="email" value={formData.email} onChange={handleChange} />
            </div>
            <div className="form-group">
              <label>Phone Number <span style={{ color: 'red' }}>*</span></label>
              <input type="tel" name="phone" value={formData.phone} onChange={handleChange} placeholder="+91XXXXXXXXXX" required minLength={10} />
            </div>
            <div className="form-group">
              <label>Date of Birth <span style={{ color: 'red' }}>*</span></label>
              <input type="date" name="dob" value={formData.dob} onChange={handleChange} required max={new Date().toISOString().split('T')[0]} />
            </div>
            <div className="form-group">
              <label>Password <span style={{ color: 'red' }}>*</span></label>
              <input type="password" name="password" value={formData.password} onChange={handleChange} required minLength={8} />
              <small style={{ color: '#666' }}>Use at least 8 chars with uppercase, lowercase, number, and special character.</small>
            </div>
            <div className="form-group">
              <label>Confirm Password <span style={{ color: 'red' }}>*</span></label>
              <input type="password" name="confirmPassword" value={formData.confirmPassword} onChange={handleChange} required />
            </div>
            <button type="submit" className="btn btn-success" style={{ width: '100%' }} disabled={loading}>
              {loading ? (mobileOTPEnabled ? 'Sending OTP...' : 'Registering...') : (mobileOTPEnabled ? 'Send OTP to Phone' : 'Register')}
            </button>
          </form>
        )}

        {step === 'otp' && (
          <form onSubmit={handleVerifyOTP}>
            {error && <div className="alert alert-danger">{error}</div>}
            <div className="alert" style={{ background: '#fff3cd', color: '#856404', border: '1px solid #ffeeba', borderRadius: 4, padding: '12px 16px', marginBottom: 16 }}>
              An OTP has been sent to <strong>{otpInfo?.phone}</strong>. Enter it below to complete registration.
            </div>
            <div className="form-group">
              <label>OTP Code <span style={{ color: 'red' }}>*</span></label>
              <input
                type="text"
                value={otp}
                onChange={e => setOtp(e.target.value)}
                placeholder="Enter 6-digit OTP"
                required
                maxLength={6}
                style={{ letterSpacing: '0.2em', fontSize: '1.2em' }}
                autoFocus
              />
            </div>
            <button type="submit" className="btn btn-success" style={{ width: '100%', marginBottom: 10 }} disabled={loading}>
              {loading ? 'Verifying...' : 'Verify & Complete Registration'}
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ width: '100%' }}
              onClick={() => { setStep('details'); setError(''); setOtp(''); }}
            >
              Back
            </button>
          </form>
        )}

        {step !== 'success' && (
          <p style={{ textAlign: 'center', marginTop: '20px' }}>
            Already have an account? <Link to="/login">Login here</Link>
          </p>
        )}
      </div>
    </div>
  );
};
