import { TabHeader } from "@/components/Character";
import { CookieForm } from "@/components/CookieForm";
import { Note } from "@/components/ui";
import { TAB_CHARACTERS } from "@/lib/characters";
import { linkedInCookieStatus } from "@/lib/settings";

export const dynamic = "force-dynamic";

const STEPS = [
  {
    n: "1️⃣",
    body: (
      <>
        Install the{" "}
        <a
          href="https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm"
          target="_blank"
          rel="noopener noreferrer"
          className="text-amber underline underline-offset-4"
        >
          Cookie-Editor
        </a>{" "}
        Chrome extension.
      </>
    ),
  },
  {
    n: "2️⃣",
    body: (
      <>
        Go to{" "}
        <a
          href="https://www.linkedin.com"
          target="_blank"
          rel="noopener noreferrer"
          className="text-amber underline underline-offset-4"
        >
          linkedin.com
        </a>{" "}
        and make sure you&apos;re <strong className="text-text">logged in</strong>.
      </>
    ),
  },
  { n: "3️⃣", body: <>Click the Cookie-Editor icon → <strong className="text-text">Export</strong> → <strong className="text-text">Export as JSON</strong>.</> },
  { n: "4️⃣", body: <>Paste the JSON into the box below.</> },
  { n: "5️⃣", body: <>Go to <strong className="text-text">⚙️ Preferences</strong>, tick <strong className="text-text">LinkedIn Jobs</strong>, and save.</> },
];

export default async function LinkedInPage() {
  const status = await linkedInCookieStatus();

  return (
    <>
      <TabHeader title="LinkedIn Setup" character={TAB_CHARACTERS.linkedin}>
        LinkedIn needs your <strong className="text-text">session cookies</strong> to authenticate.
        There is no login automation on purpose — LinkedIn challenges scripted logins.
      </TabHeader>

      <div className="grid gap-8 lg:grid-cols-2">
        <div>
          <h3 className="mb-3 text-sm font-semibold">Step-by-step</h3>
          <ol className="flex flex-col gap-2.5">
            {STEPS.map((s) => (
              <li key={s.n} className="flex gap-2.5 text-sm text-dim">
                <span aria-hidden className="shrink-0">
                  {s.n}
                </span>
                <span>{s.body}</span>
              </li>
            ))}
          </ol>
        </div>

        <div>
          <h3 className="mb-3 text-sm font-semibold">Status</h3>
          {!status.present ? (
            <Note tone="warn">⚠️ No cookies saved yet — paste them below to set up.</Note>
          ) : !status.hasSessionToken ? (
            <Note tone="warn">
              ❌ Saved, but no <code className="text-amber">li_at</code> token — re-export while
              logged in.
            </Note>
          ) : status.stale ? (
            <Note tone="warn">
              ⚠️ {status.count} cookies, saved{" "}
              {status.ageDays} days ago. They
              expire around 30 days — re-export if scraping stops returning anything.
            </Note>
          ) : (
            <Note tone="good">
              ✅ {status.count} cookies active, <code className="text-amber">li_at</code> present —
              ready to scrape.
            </Note>
          )}

          <h3 className="mt-6 mb-3 text-sm font-semibold">⚠️ Important notes</h3>
          <ul className="flex list-disc flex-col gap-1.5 pl-5 text-xs leading-relaxed text-dim">
            <li>Cookies expire in roughly 30 days — re-export when scraping stops working.</li>
            <li>Personal use only. The scraper paces itself and caps each search.</li>
            <li>If LinkedIn blocks you, turn it off in Preferences and try again in 24 hours.</li>
            <li>
              These are stored in the database rather than a local file, because that is the only
              place a scheduled run could read them from. Anyone with{" "}
              <code className="text-amber">DATABASE_URL</code> can read them.
            </li>
          </ul>
        </div>
      </div>

      <hr className="my-6 border-line" />
      <CookieForm />
    </>
  );
}
