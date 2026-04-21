import api from './api';

const COMPANY_IMAGE_CACHE_NAME = 'company-image-ui-cache-v1';
const COMPANY_IMAGE_ETAG_KEY = 'company-image-etag';
const SKIP_EXIT_CLEAR_KEY = 'company-image-skip-exit-clear-once';

let activeObjectUrl: string | null = null;
let exitCleanupRegistered = false;

const getCompanyImageEndpoint = (): string => {
  const baseURL = (api.defaults.baseURL || '').replace(/\/api\/?$/, '');
  return `${baseURL}/api/brand/image`;
};

const revokeActive = () => {
  if (activeObjectUrl) {
    URL.revokeObjectURL(activeObjectUrl);
    activeObjectUrl = null;
  }
};

const blobToObjectUrl = (blob: Blob): string => {
  revokeActive();
  activeObjectUrl = URL.createObjectURL(blob);
  return activeObjectUrl;
};

// ─── Cache Storage helpers ────────────────────────────────────────────────────

const getCachedBlob = async (): Promise<Blob | null> => {
  if (!('caches' in window)) return null;
  const cache = await caches.open(COMPANY_IMAGE_CACHE_NAME);
  const cached = await cache.match(getCompanyImageEndpoint());
  if (!cached || !cached.ok) return null;
  return cached.blob();
};

const putInCache = async (response: Response): Promise<void> => {
  if (!('caches' in window)) return;
  const cache = await caches.open(COMPANY_IMAGE_CACHE_NAME);
  await cache.put(getCompanyImageEndpoint(), response);
};

const evictCache = async (): Promise<void> => {
  if ('caches' in window) {
    await caches.delete(COMPANY_IMAGE_CACHE_NAME);
  }
  sessionStorage.removeItem(COMPANY_IMAGE_ETAG_KEY);
};

// ─── Network fetch with ETag revalidation ────────────────────────────────────

/**
 * Fetches the company image from the server.
 * - Sends If-None-Match when a cached ETag exists.
 * - Returns the cached blob on 304, the fresh blob on 200, null on 404/error.
 */
const fetchImage = async (): Promise<Blob | null> => {
  const storedEtag = sessionStorage.getItem(COMPANY_IMAGE_ETAG_KEY);
  const headers: Record<string, string> = {};
  if (storedEtag) {
    headers['If-None-Match'] = storedEtag;
  }
  // Include device identification headers for session management.
  const { getDeviceHeadersSync } = await import('../utils/deviceInfo');
  const deviceHeaders = getDeviceHeadersSync();
  headers['X-Client-MAC'] = deviceHeaders['X-Client-MAC'];
  headers['X-Client-IP'] = deviceHeaders['X-Client-IP'];

  let response: Response;
  try {
    response = await fetch(getCompanyImageEndpoint(), {
      method: 'GET',
      credentials: 'include',
      headers,
    });
  } catch {
    return null;
  }

  // Not modified — serve from cache
  if (response.status === 304) {
    return getCachedBlob();
  }

  // No image in DB yet — evict any stale cached image and return null
  if (response.status === 404) {
    await evictCache();
    return null;
  }

  if (!response.ok) {
    return null;
  }

  // Fresh image — update ETag and cache
  const newEtag = response.headers.get('ETag');
  if (newEtag) {
    sessionStorage.setItem(COMPANY_IMAGE_ETAG_KEY, newEtag);
  }
  const blob = await response.blob();
  // Store a synthetic OK response in Cache Storage for offline resilience
  await putInCache(new Response(blob.slice(), { status: 200, headers: { 'Content-Type': blob.type } }));
  return blob;
};

// ─── Public API ───────────────────────────────────────────────────────────────

const consumeSkipExitFlag = (): boolean => {
  if (sessionStorage.getItem(SKIP_EXIT_CLEAR_KEY) === '1') {
    sessionStorage.removeItem(SKIP_EXIT_CLEAR_KEY);
    return true;
  }
  return false;
};

export const markSkipCompanyImageClearOnNextExit = () => {
  sessionStorage.setItem(SKIP_EXIT_CLEAR_KEY, '1');
};

export const clearCompanyImageCache = async (): Promise<void> => {
  revokeActive();
  await evictCache();
};

export const registerCompanyImageExitCleanup = (): void => {
  if (exitCleanupRegistered) return;
  exitCleanupRegistered = true;
  window.addEventListener('beforeunload', () => {
    if (consumeSkipExitFlag()) return;
    void clearCompanyImageCache();
  });
};

/**
 * Load company image:
 * 1. Check Cache Storage for a stored blob (fast path).
 * 2. Revalidate with server via ETag (304 = use cache, 200 = update cache, 404 = no image).
 * Returns an object URL string, or null if no image exists in the database.
 */
export const loadCompanyImage = async (): Promise<string | null> => {
  try {
    // Fast path: serve from cache immediately while revalidating in background
    const cachedBlob = await getCachedBlob();
    if (cachedBlob) {
      // Revalidate in background — update state via event if image changed
      fetchImage().then((freshBlob) => {
        if (!freshBlob) {
          // 404: image deleted from DB — clear and notify
          revokeActive();
          window.dispatchEvent(new Event('company-image-updated'));
        }
      });
      return blobToObjectUrl(cachedBlob);
    }

    // No cache — fetch from server
    const blob = await fetchImage();
    if (!blob) return null;
    return blobToObjectUrl(blob);
  } catch {
    revokeActive();
    return null;
  }
};

/**
 * Force-fetch a fresh image from the server (used after admin uploads a new image).
 * Clears the existing cache entry first so the server always returns 200.
 */
export const refreshCompanyImage = async (): Promise<string | null> => {
  try {
    await evictCache();
    const blob = await fetchImage();
    if (!blob) {
      revokeActive();
      return null;
    }
    return blobToObjectUrl(blob);
  } catch {
    revokeActive();
    return null;
  }
};
