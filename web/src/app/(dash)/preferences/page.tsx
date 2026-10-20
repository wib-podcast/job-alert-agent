import { TabHeader } from "@/components/Character";
import { PreferencesForm } from "@/components/PreferencesForm";
import { TAB_CHARACTERS } from "@/lib/characters";
import { loadSettings } from "@/lib/settings";

export const dynamic = "force-dynamic";

export default async function PreferencesPage() {
  const settings = await loadSettings();

  return (
    <>
      <TabHeader title="Search Preferences" character={TAB_CHARACTERS.preferences}>
        These settings control <strong className="text-text">what gets scraped and scored</strong> on
        every run — including the scheduled one at 8&nbsp;AM and 6&nbsp;PM IST.
      </TabHeader>
      <PreferencesForm initial={settings} />
    </>
  );
}
