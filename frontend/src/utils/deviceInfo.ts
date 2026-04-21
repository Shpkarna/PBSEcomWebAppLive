/**
 * Device fingerprinting and client IP detection.
 *
 * Browsers cannot access the real MAC address for security reasons.
 * Instead we generate a stable device fingerprint from browser properties
 * (user-agent, screen resolution, timezone, language, platform) and format
 * it as a MAC-like hex string so the backend session management can use it
 * as a device identifier.
 *
 * The client IP is fetched once per session from a lightweight public API
 * and cached in sessionStorage so subsequent calls are instant.
 */

const DEVICE_ID_KEY = 'device_fingerprint';
const CLIENT_IP_KEY = 'client_ip';

/* ------------------------------------------------------------------ */
/*  Stable device fingerprint (MAC-like)                              */
/* ------------------------------------------------------------------ */

/**
 * Simple non-crypto hash (djb2) that produces a deterministic 48-bit
 * integer from a string, formatted as a colon-separated hex string
 * resembling a MAC address — e.g. "4A:3F:01:B7:C2:8E".
 */
function djb2Hash(str: string): number {
  let hash = 5381;
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) + hash + str.charCodeAt(i)) & 0xffffffffffff; // keep 48 bits
  }
  return Math.abs(hash);
}

function toMacFormat(hash: number): string {
  const hex = hash.toString(16).padStart(12, '0').slice(0, 12);
  return hex.match(/.{2}/g)!.join(':').toUpperCase();
}

function buildFingerprint(): string {
  const parts = [
    navigator.userAgent,
    `${screen.width}x${screen.height}x${screen.colorDepth}`,
    Intl.DateTimeFormat().resolvedOptions().timeZone,
    navigator.language,
    navigator.platform,
    navigator.hardwareConcurrency?.toString() ?? '',
  ];
  return toMacFormat(djb2Hash(parts.join('|')));
}

/** Returns a stable MAC-like device ID, cached in localStorage. */
export function getDeviceId(): string {
  let id = localStorage.getItem(DEVICE_ID_KEY);
  if (!id) {
    id = buildFingerprint();
    localStorage.setItem(DEVICE_ID_KEY, id);
  }
  return id;
}

/* ------------------------------------------------------------------ */
/*  Client IP detection                                               */
/* ------------------------------------------------------------------ */

/** Fetches the client's public IP once per session. Falls back to 'unknown'. */
export async function getClientIp(): Promise<string> {
  const cached = sessionStorage.getItem(CLIENT_IP_KEY);
  if (cached) return cached;

  try {
    const resp = await fetch('https://api.ipify.org?format=json', { signal: AbortSignal.timeout(3000) });
    const data = await resp.json();
    const ip: string = data.ip || 'unknown';
    sessionStorage.setItem(CLIENT_IP_KEY, ip);
    return ip;
  } catch {
    return 'unknown';
  }
}

/**
 * Returns both device headers synchronously from cache if available,
 * or 'unknown' for IP when not yet resolved.
 * Prefer `getDeviceHeaders()` (async) which ensures IP is fetched.
 */
export function getDeviceHeadersSync(): Record<string, string> {
  return {
    'X-Client-MAC': getDeviceId(),
    'X-Client-IP': sessionStorage.getItem(CLIENT_IP_KEY) || 'unknown',
  };
}

/** Returns device identification headers { X-Client-MAC, X-Client-IP }. */
export async function getDeviceHeaders(): Promise<Record<string, string>> {
  const [ip] = await Promise.all([getClientIp()]);
  return {
    'X-Client-MAC': getDeviceId(),
    'X-Client-IP': ip,
  };
}
