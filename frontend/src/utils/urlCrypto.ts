const textEncoder = new TextEncoder();
const textDecoder = new TextDecoder();

const KEY_VERSION = 'v1';
const KEY_SALT = 'hatt-url-crypto-salt';
const IV_LENGTH = 12;

function toBase64Url(bytes: Uint8Array): string {
  let binary = '';
  bytes.forEach((byte) => {
    binary += String.fromCharCode(byte);
  });
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}

function fromBase64Url(value: string): Uint8Array {
  const base64 = value.replace(/-/g, '+').replace(/_/g, '/');
  const padded = base64 + '='.repeat((4 - (base64.length % 4)) % 4);
  const binary = atob(padded);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

function toArrayBuffer(bytes: Uint8Array): ArrayBuffer {
  return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer;
}

let cachedKeyPromise: Promise<CryptoKey> | null = null;

async function getKey(): Promise<CryptoKey> {
  if (cachedKeyPromise) return cachedKeyPromise;

  cachedKeyPromise = (async () => {
    const secret = String(process.env.REACT_APP_URL_CRYPTO_KEY || 'hatt-default-url-key');
    const keyMaterial = await crypto.subtle.importKey(
      'raw',
      textEncoder.encode(secret),
      'PBKDF2',
      false,
      ['deriveKey']
    );

    return crypto.subtle.deriveKey(
      {
        name: 'PBKDF2',
        salt: textEncoder.encode(KEY_SALT),
        iterations: 100000,
        hash: 'SHA-256',
      },
      keyMaterial,
      { name: 'AES-GCM', length: 256 },
      false,
      ['encrypt', 'decrypt']
    );
  })();

  return cachedKeyPromise;
}

export async function encryptRouteParam(plainText: string): Promise<string> {
  const key = await getKey();
  const iv = crypto.getRandomValues(new Uint8Array(IV_LENGTH));
  const encrypted = await crypto.subtle.encrypt(
    { name: 'AES-GCM', iv: toArrayBuffer(iv) },
    key,
    textEncoder.encode(plainText)
  );

  const payload = toBase64Url(new Uint8Array(encrypted));
  const ivPart = toBase64Url(iv);
  return `${KEY_VERSION}.${ivPart}.${payload}`;
}

export async function decryptRouteParam(value: string): Promise<string> {
  const parts = value.split('.');
  if (parts.length !== 3 || parts[0] !== KEY_VERSION) {
    throw new Error('Invalid encrypted route token');
  }

  const iv = fromBase64Url(parts[1]);
  const payload = fromBase64Url(parts[2]);
  const key = await getKey();

  const decrypted = await crypto.subtle.decrypt(
    { name: 'AES-GCM', iv: toArrayBuffer(iv) },
    key,
    toArrayBuffer(payload)
  );

  return textDecoder.decode(decrypted);
}

export async function decryptRouteParamOrFallback(value: string): Promise<string> {
  try {
    return await decryptRouteParam(value);
  } catch {
    try {
      return decodeURIComponent(value);
    } catch {
      return value;
    }
  }
}

export function fallbackRouteParam(value: string): string {
  return encodeURIComponent(value);
}
