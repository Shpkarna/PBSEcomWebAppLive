import axios from 'axios';
import { getDeviceHeadersSync, getClientIp } from '../utils/deviceInfo';

// Kick off IP detection early so subsequent sync reads have a cached value.
getClientIp();

const getRuntimeApiBaseUrl = () => {
  if (typeof window === 'undefined') {
    return 'http://localhost:7999/api';
  }

  const host = window.location.hostname || 'localhost';
  const protocol = window.location.protocol === 'https:' ? 'https:' : 'http:';
  return `${protocol}//${host}:7999/api`;
};

const isLocalHostname = (hostname: string): boolean => {
  const localHosts = new Set(['localhost', '127.0.0.1', '0.0.0.0']);
  return localHosts.has((hostname || '').toLowerCase());
};

// process.env.REACT_APP_API_URL is replaced at build time by webpack DefinePlugin.
// eslint-disable-next-line no-undef
const INJECTED_API_URL: string | undefined = process.env.REACT_APP_API_URL as any;
const runtimeApiBaseUrl = getRuntimeApiBaseUrl();
const shouldPreferDirectLocalApi =
  typeof window !== 'undefined' &&
  INJECTED_API_URL === '/api' &&
  isLocalHostname(window.location.hostname);
const enableLocalPortFallback =
  typeof window !== 'undefined' &&
  isLocalHostname(window.location.hostname);
const DEFAULT_API_BASE_URL = shouldPreferDirectLocalApi
  ? runtimeApiBaseUrl
  : (INJECTED_API_URL || runtimeApiBaseUrl);

const getLocalApiFallback = (baseUrl: string): string | null => {
  if (!enableLocalPortFallback || !baseUrl) {
    return null;
  }

  try {
    const url = new URL(baseUrl);
    if (url.port === '7999') {
      url.port = '8000';
      return url.toString().replace(/\/$/, '');
    }
    if (url.port === '8000') {
      url.port = '7999';
      return url.toString().replace(/\/$/, '');
    }
  } catch {
    return null;
  }

  return null;
};

const api = axios.create({
  baseURL: DEFAULT_API_BASE_URL,
  timeout: 5000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add authorization token and device identification headers to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  // Attach device fingerprint (MAC-like) and client IP on every request.
  const deviceHeaders = getDeviceHeadersSync();
  config.headers['X-Client-MAC'] = deviceHeaders['X-Client-MAC'];
  config.headers['X-Client-IP'] = deviceHeaders['X-Client-IP'];
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const cfg = error?.config as any;

    // Handle 401 Unauthorized — session expired or token invalid.
    // Skip for login/register endpoints to avoid redirect loops.
    if (
      error?.response?.status === 401 &&
      cfg?.url &&
      !cfg.url.includes('/auth/login') &&
      !cfg.url.includes('/auth/register')
    ) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      sessionStorage.removeItem('active_session');
      // Redirect to login only once (prevent multiple concurrent 401s from stacking)
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login';
      }
      return Promise.reject(error);
    }

    // Local port fallback for network errors only
    const currentBase = String(cfg?.baseURL || api.defaults.baseURL || '');
    const fallbackBase = getLocalApiFallback(currentBase);

    if (!cfg || cfg._fallbackTried || !fallbackBase || error?.response) {
      return Promise.reject(error);
    }

    cfg._fallbackTried = true;
    cfg.baseURL = fallbackBase;
    return api.request(cfg);
  }
);

export default api;
