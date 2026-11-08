/** HMAC-SHA256 con Web Crypto: firma y verificación en tiempo constante. */

const encoder = new TextEncoder()

async function hmacKey(secret: string, usage: 'sign' | 'verify'): Promise<CryptoKey> {
  return crypto.subtle.importKey('raw', encoder.encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, [usage])
}

/** Bytes de un hexadecimal, o null si no es un hexadecimal válido de la longitud esperada. */
export function hexToBytes(hex: string, expectedBytes: number): Uint8Array | null {
  if (hex.length !== expectedBytes * 2 || !/^[0-9a-f]+$/i.test(hex)) return null
  const bytes = new Uint8Array(expectedBytes)
  for (let i = 0; i < expectedBytes; i++) bytes[i] = parseInt(hex.slice(i * 2, i * 2 + 2), 16)
  return bytes
}

export function bytesToHex(bytes: ArrayBuffer): string {
  return [...new Uint8Array(bytes)].map((b) => b.toString(16).padStart(2, '0')).join('')
}

/**
 * Verifica una cabecera `sha256=<hex>` sobre el cuerpo.
 * `crypto.subtle.verify` compara en tiempo constante: no filtra cuántos bytes coinciden.
 */
export async function verifySha256Signature(secret: string, body: ArrayBuffer, header: string | null): Promise<boolean> {
  if (!secret || !header?.startsWith('sha256=')) return false
  const signature = hexToBytes(header.slice('sha256='.length), 32)
  if (!signature) return false
  return crypto.subtle.verify('HMAC', await hmacKey(secret, 'verify'), signature, body)
}

export async function signSha256(secret: string, message: string): Promise<string> {
  const signature = await crypto.subtle.sign('HMAC', await hmacKey(secret, 'sign'), encoder.encode(message))
  return bytesToHex(signature)
}
