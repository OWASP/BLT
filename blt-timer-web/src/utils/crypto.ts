/**
 * Cryptography utilities for secure data storage
 */

/**
 * Generate a secure random token
 */
export function generateToken(length: number = 32): string {
  const array = new Uint8Array(length);
  crypto.getRandomValues(array);
  return Array.from(array, (byte) => byte.toString(16).padStart(2, '0')).join('');
}

/**
 * Hash data using SHA-256
 */
export async function hashData(data: string): Promise<string> {
  const encoder = new TextEncoder();
  const dataBuffer = encoder.encode(data);
  const hashBuffer = await crypto.subtle.digest('SHA-256', dataBuffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((byte) => byte.toString(16).padStart(2, '0')).join('');
}

/**
 * Generate a deterministic ID from input
 */
export async function generateId(...inputs: string[]): Promise<string> {
  const combined = inputs.join(':');
  return hashData(combined);
}

/**
 * Encrypt sensitive data (placeholder for actual implementation)
 * In production, use Web Crypto API with proper key management
 */
export async function encryptData(data: string, key: string): Promise<string> {
  // This is a placeholder - implement proper encryption in production
  // Use AES-GCM with the Web Crypto API
  const encoder = new TextEncoder();
  const dataBuffer = encoder.encode(data);
  const keyHash = await hashData(key);
  
  // In production, implement actual encryption here
  return btoa(JSON.stringify({ data: dataBuffer, keyHash }));
}

/**
 * Decrypt sensitive data (placeholder for actual implementation)
 */
export async function decryptData(encryptedData: string, key: string): Promise<string> {
  // This is a placeholder - implement proper decryption in production
  const keyHash = await hashData(key);
  
  // In production, implement actual decryption here
  const decoded = JSON.parse(atob(encryptedData));
  return new TextDecoder().decode(new Uint8Array(decoded.data));
}
