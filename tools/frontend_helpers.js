/*
 * Small frontend helper utilities for the portal to normalize phone numbers
 * and dates and to call the member/champion registration endpoints.
 * Copy these into your frontend `apiService` or similar.
 */

// Normalize a Kenyan phone number to something the backend accepts.
// Examples:
//  - "0712345678" -> "+254712345678"
//  - "+254712345678" -> "+254712345678"
//  - "254712345678" -> "+254712345678"
export function normalizePhone(phone) {
  if (!phone) return null;
  let raw = String(phone).trim();
  // Remove non-digit and non-plus chars
  raw = raw.replace(/[^\d+]/g, '');
  if (raw.startsWith('+')) {
    return raw;
  }
  if (raw.startsWith('0')) {
    // local 0-prefixed number -> +254
    return '+254' + raw.slice(1);
  }
  if (raw.startsWith('254')) {
    return '+' + raw;
  }
  // Fallback: return as-is (caller can validate)
  return raw;
}

// Format a Date or date string into YYYY-MM-DD for the backend
export function formatDateYYYYMMDD(value) {
  if (!value) return null;
  const d = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(d.getTime())) return null;
  return d.toISOString().slice(0, 10);
}

// Example: register a member using fetch. Returns the parsed JSON response.
export async function registerMember(payload, baseUrl = '') {
  const body = {
    full_name: payload.full_name,
    phone_number: normalizePhone(payload.phone_number),
    username: payload.username,
    password: payload.password,
    email: payload.email || undefined,
    date_of_birth: payload.date_of_birth ? formatDateYYYYMMDD(payload.date_of_birth) : undefined,
    gender: payload.gender || undefined,
    county_sub_county: payload.county_sub_county || undefined
  };

  const res = await fetch(baseUrl + '/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  return res.json();
}

// Example: register a champion (public self-registration)
export async function registerChampion(payload, baseUrl = '') {
  const body = Object.assign({}, payload);
  body.phone_number = normalizePhone(payload.phone_number);
  if (payload.date_of_birth) body.date_of_birth = formatDateYYYYMMDD(payload.date_of_birth);

  const res = await fetch(baseUrl + '/api/champions/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  return res.json();
}

// Export convenience wrappers for older API if needed
export async function applyChampionLegacy(payload, baseUrl = '') {
  const res = await fetch(baseUrl + '/api/champion/apply', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  return res.json();
}

// Simple client-side validators you can reuse
export function isValidPhoneForChampion(phone) {
  const p = normalizePhone(phone);
  // Very simple rule: must contain + and 9-13 digits total
  return !!p && /^\+?\d{9,15}$/.test(p);
}

export function isValidDateYYYYMMDD(value) {
  return !!formatDateYYYYMMDD(value);
}

/*
Usage examples (frontend):

import { registerMember } from './tools/frontend_helpers';

const resp = await registerMember({
  full_name: 'Test User',
  phone_number: '0712345678',
  username: 'testuser',
  password: 'P@ssw0rd1',
  date_of_birth: '2002-01-01'
});

console.log(resp);
*/
