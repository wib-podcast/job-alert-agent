import { CharacterPortrait } from "@/components/Character";
import { SIDEBAR_CHARACTER } from "@/lib/characters";
import { googleConfigured, passcodeConfigured, signIn } from "@/lib/auth";

export const dynamic = "force-dynamic";

/**
 * Two ways in. Google is the intended one; the passcode exists so the board is
 * usable before an OAuth client has been created, and both land on the same
 * allowlisted identity.
 */
export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ from?: string; error?: string }>;
}) {
  const { from, error } = await searchParams;
  const redirectTo = from && from.startsWith("/") ? from : "/";

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-sm flex-col justify-center px-6 py-10">
      <div className="mx-auto mb-6 w-[200px]">
        <CharacterPortrait character={SIDEBAR_CHARACTER} size={200} />
      </div>
      <h1 className="glow-title text-[1.9rem]">Job Alert Agent</h1>
      <p className="mt-1 text-[0.82rem] text-faint">
        PM and AI PM roles across UAE, Singapore, UK, Ireland and SEA.
      </p>

      {error ? (
        <p className="mt-5 rounded-lg border border-amber/40 px-3 py-2 text-sm text-amber">
          That didn&apos;t work. Check the address is on the allowlist.
        </p>
      ) : null}

      {googleConfigured ? (
        <form
          className="mt-6"
          action={async () => {
            "use server";
            await signIn("google", { redirectTo });
          }}
        >
          <button
            type="submit"
            className="btn-primary w-full px-4 py-2.5 text-sm"
          >
            Continue with Google
          </button>
        </form>
      ) : null}

      {passcodeConfigured ? (
        <form
          className="mt-3 flex gap-2"
          action={async (formData: FormData) => {
            "use server";
            await signIn("passcode", {
              passcode: String(formData.get("passcode") ?? ""),
              redirectTo,
            });
          }}
        >
          <input
            name="passcode"
            type="password"
            inputMode="numeric"
            autoComplete="current-password"
            placeholder="Passcode"
            aria-label="Passcode"
            className="field min-w-0 flex-1 px-3 py-2.5 text-sm"
          />
          <button
            type="submit"
            className="btn-primary px-4 py-2.5 text-sm"
          >
            Enter
          </button>
        </form>
      ) : null}

      {!googleConfigured && !passcodeConfigured ? (
        <p className="mt-6 text-sm text-dim">
          No sign-in method is configured. Set <code className="text-amber">APP_PASSCODE</code>, or{" "}
          <code className="text-amber">AUTH_GOOGLE_ID</code> and <code className="text-amber">AUTH_GOOGLE_SECRET</code>.
        </p>
      ) : null}
    </main>
  );
}
