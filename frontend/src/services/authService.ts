import api from './api';

export interface User {
  username: string;
  email: string;
  full_name?: string;
  phone?: string;
  address?: string;
  role: string;
}

export interface UserProfile {
  id: string;
  username: string;
  email: string;
  role: string;
  phone_verified?: boolean;
  email_verified?: boolean;
  full_name?: string;
  phone?: string;
  address?: string;
  address_data?: {
    street1?: string;
    street2?: string;
    landmark?: string;
    district?: string;
    area?: string;
    state?: string;
    country?: string;
    pincode?: string;
    phone?: string;
  };
  saved_payment_data?: {
    card_holder?: string;
    card_last4?: string;
    card_brand?: string;
    expiry_month?: number;
    expiry_year?: number;
    upi_id?: string;
  };
  created_at?: string;
  updated_at?: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface OTPSendPayload {
  username: string;
  email: string;
  full_name: string;
  phone: string;
  dob: string;
  password: string;
}

export interface OTPVerifyPayload extends OTPSendPayload {
  otp: string;
}

export interface MobileOTPConfig {
  enable_mobile_otp_verification: boolean;
}

export interface EmailVerificationConfig {
  enable_email_verification: boolean;
}

const getStoredUser = (): User | null => {
  const rawUser = localStorage.getItem('user');
  if (!rawUser) {
    return null;
  }

  try {
    return JSON.parse(rawUser) as User;
  } catch {
    localStorage.removeItem('user');
    return null;
  }
};

export const authService = {
  /** @deprecated Use sendRegistrationOTP + verifyRegistrationOTP instead */
  async register(username: string, email: string, password: string, fullName?: string, phone?: string, dob?: string) {
    const response = await api.post('/auth/register', {
      username,
      email,
      password,
      full_name: fullName,
      phone,
      dob,
    });
    return response.data;
  },

  async getMobileOTPConfig(): Promise<MobileOTPConfig> {
    const response = await api.get('/auth/mobile-otp-config');
    return response.data;
  },

  async getEmailVerificationConfig(): Promise<EmailVerificationConfig> {
    const response = await api.get('/auth/email-verification-config');
    return response.data;
  },

  async sendRegistrationOTP(payload: OTPSendPayload) {
    const response = await api.post('/auth/register/send-otp', payload);
    return response.data;
  },

  async verifyRegistrationOTP(payload: OTPVerifyPayload) {
    const response = await api.post('/auth/register/verify-otp', payload);
    return response.data;
  },

  async sendChangePhoneOTP(newPhone: string) {
    const response = await api.post('/auth/change-phone/send-otp', { new_phone: newPhone });
    return response.data as { message: string; expires_at: string; phone: string };
  },

  async verifyChangePhoneOTP(newPhone: string, otp: string) {
    const response = await api.post('/auth/change-phone/verify-otp', { new_phone: newPhone, otp });
    return response.data as { message: string };
  },

  async sendEmailVerification(email: string) {
    const response = await api.post('/auth/verify-email/send', { email });
    return response.data as { message: string; email: string; verification_token?: string };
  },

  async login(username: string, password: string): Promise<LoginResponse> {
    const response = await api.post('/auth/login', {
      username,
      password,
    });
    const { access_token, user } = response.data;
    localStorage.setItem('access_token', access_token);
    localStorage.setItem('user', JSON.stringify(user));
    sessionStorage.setItem('active_session', '1');
    return response.data;
  },

  async getCurrentUser(): Promise<User | null> {
    try {
      const response = await api.get('/auth/me');
      localStorage.setItem('user', JSON.stringify(response.data));
      return response.data;
    } catch (error: any) {
      const status = error?.response?.status;
      if (status === 401 || status === 403 || status === 404) {
        await this.logout();
        return null;
      }
      return getStoredUser();
    }
  },

  async logout() {
    try {
      await api.post('/auth/logout');
    } catch {
      // Local token cleanup still proceeds even if backend session cookie is missing.
    }
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    sessionStorage.removeItem('active_session');
  },

  async getProfile(): Promise<UserProfile> {
    const response = await api.get('/auth/profile');
    return response.data;
  },

  async updateProfile(profile: Partial<UserProfile>): Promise<{ message: string; email_verification_pending?: boolean; profile: UserProfile }> {
    const response = await api.put('/auth/profile', profile);
    return response.data;
  },

  getToken(): string | null {
    return localStorage.getItem('access_token');
  },

  isAuthenticated(): boolean {
    return !!this.getToken() && !!sessionStorage.getItem('active_session');
  },

  async initializeAdmin() {
    const response = await api.post('/auth/init-admin');
    return response.data;
  },

  async changePassword(currentPassword: string, newPassword: string) {
    const response = await api.put('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
    return response.data;
  },
};
