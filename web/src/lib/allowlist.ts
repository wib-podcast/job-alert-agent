/**
 * Who may use this app, and how a passcode is checked.
 *
 * Kept separate from `auth.ts` on purpose: that module pulls in NextAuth, which
 * imports `next/server` and can't be loaded outside a Next runtime. The access
 * policy is the part worth testing directly, so it lives here with no
 * framework dependencies at all.
 */

export function allowedEmails(): string[] {
  return (process.env.ALLOWED_EMAILS ?? "")
    .split(",")
    .map((e) => e.trim().toLowerCase())
    .filter(Boolean);
}

export function isAllowed(email: string | null | undefined): boolean {
  if (!email) return false;
  const list = allowedEmails();
  // An empty allowlist locks everyone out rather than letting everyone in.
  if (list.length === 0) return false;
  return list.includes(email.toLowerCase());
}

/** The passcode grants this identity — the first address on the allowlist. */
export function ownerEmail(): string | null {
  return allowedEmails()[0] ?? null;
}

/**
 * Constant-time string comparison. Deliberately not `node:crypto.timingSafeEqual`
 * — this is reached from `src/proxy.ts`, which runs on the edge runtime where
 * the Node crypto built-in isn't available.
 *
 * Length is compared first and so leaks, which is an accepted trade for a
 * single-user passcode.
 */
export function safeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i += 1) {
    diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return diff === 0;
}

/** Verifies a submitted passcode and returns the identity it grants. */
export function checkPasscode(given: unknown): { email: string } | null {
  const expected = process.env.APP_PASSCODE;
  if (!expected) return null;
  if (typeof given !== "string" || given.length === 0) return null;
  if (!safeEqual(given, expected)) return null;

  const email = ownerEmail();
  // No allowlist means no identity to grant, so the passcode can't work.
  if (!email) return null;

  return { email };
}
