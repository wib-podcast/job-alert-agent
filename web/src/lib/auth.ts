import NextAuth, { type NextAuthConfig } from "next-auth";
import Credentials from "next-auth/providers/credentials";
import Google from "next-auth/providers/google";

import { checkPasscode, isAllowed } from "./allowlist";

/**
 * Two ways in, both landing on the same allowlisted identity:
 *
 *   - Google, for one-tap sign-in on a phone.
 *   - A shared passcode, so the app is usable before an OAuth client exists.
 *
 * Only the providers that are actually configured get registered, so a missing
 * key shows up as a hidden button rather than a 500 on click.
 *
 * The access policy itself lives in `./allowlist` — see the note there.
 */

export { isAllowed };

export const googleConfigured = Boolean(process.env.AUTH_GOOGLE_ID && process.env.AUTH_GOOGLE_SECRET);
export const passcodeConfigured = Boolean(process.env.APP_PASSCODE);

const providers: NextAuthConfig["providers"] = [];

if (googleConfigured) {
  providers.push(Google);
}

if (passcodeConfigured) {
  providers.push(
    Credentials({
      id: "passcode",
      name: "Passcode",
      credentials: { passcode: { label: "Passcode", type: "password" } },
      authorize(credentials) {
        const granted = checkPasscode(credentials?.passcode);
        return granted ? { id: "owner", email: granted.email, name: "Owner" } : null;
      },
    }),
  );
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers,
  // Required for the credentials provider, and correct for Google here too:
  // there's no database adapter holding sessions.
  session: { strategy: "jwt" },
  pages: { signIn: "/login", error: "/login" },
  callbacks: {
    signIn({ account, profile }) {
      // authorize() already verified the passcode and picked an allowlisted
      // identity; there is no profile to check.
      if (account?.provider === "passcode") return true;
      return isAllowed(profile?.email);
    },
    // Re-checked on every request, so removing an address from the allowlist
    // kills existing sessions instead of waiting for them to expire.
    session({ session }) {
      return isAllowed(session.user?.email) ? session : { ...session, user: undefined! };
    },
  },
});
