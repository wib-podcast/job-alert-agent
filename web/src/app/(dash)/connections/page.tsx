import { TabHeader } from "@/components/Character";
import { Note } from "@/components/ui";
import { TAB_CHARACTERS } from "@/lib/characters";

export const dynamic = "force-dynamic";

/**
 * Connections & Referrals.
 *
 * dashboard.py read `data/connections.csv`, a file produced on the laptop by
 * `scrapers/connections_scraper.py` and never checked in. Nothing has been
 * imported into Postgres yet, so this tab states that plainly rather than
 * rendering an empty table that looks broken.
 */
export default function ConnectionsPage() {
  return (
    <>
      <TabHeader title="Connections & Referrals" character={TAB_CHARACTERS.connections}>
        Find your LinkedIn connections by company and institute, to work out who to ask for a
        referral.
      </TabHeader>

      <Note tone="warn">
        Not migrated yet. The Streamlit version read{" "}
        <code className="text-amber">data/connections.csv</code> from the laptop — a file that was
        never checked in and doesn&apos;t exist in the database, so there is nothing for this tab to
        show.
      </Note>

      <div className="mt-6">
        <h3 className="mb-3 text-sm font-semibold">What this needs</h3>
        <ol className="flex list-decimal flex-col gap-2 pl-5 text-sm leading-relaxed text-dim">
          <li>
            A <code className="text-amber">connections</code> table — name, company, title,
            seniority, institutes, months in role, profile URL.
          </li>
          <li>
            An importer for LinkedIn&apos;s official data export. Request it at{" "}
            <a
              href="https://www.linkedin.com/mypreferences/d/data-privacy"
              target="_blank"
              rel="noopener noreferrer"
              className="text-amber underline underline-offset-4"
            >
              Data privacy → Get a copy of your data
            </a>
            , pick <strong className="text-text">Connections</strong> only, and it arrives in about
            ten minutes.
          </li>
          <li>
            Joining it to the board, so a job at a company you already know says so on the card —
            which is the point of the tab, and something the CSV version never did.
          </li>
        </ol>
        <p className="mt-4 text-xs text-faint">
          Say the word and I&apos;ll build it. It was the lowest-value tab to port blind, because
          the interesting version is the join, not the table.
        </p>
      </div>
    </>
  );
}
