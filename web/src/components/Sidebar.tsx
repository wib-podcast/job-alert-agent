import { signOut } from "@/lib/auth";
import { CharacterPortrait, CharacterQuote } from "@/components/Character";
import { SIDEBAR_CHARACTER } from "@/lib/characters";
import { Metric } from "@/components/ui";

export interface SidebarStats {
  total: number;
  newCount: number;
  highFit: number;
  sources: string[];
}

export function Sidebar({ stats }: { stats: SidebarStats }) {
  return (
    <aside className="w-full shrink-0 border-line-strong bg-sidebar px-5 py-6 lg:h-dvh lg:w-[280px] lg:overflow-y-auto lg:border-r">
      <div className="mx-auto max-w-[220px] lg:max-w-none">
        <CharacterPortrait character={SIDEBAR_CHARACTER} size={240} />
      </div>

      <h1 className="glow-title mt-4 text-[1.9rem]">
        Job Alert
        <br />
        Agent
      </h1>
      <p className="mt-1 text-[0.82rem] text-faint">Your personal PM job radar</p>

      <hr className="my-5 border-line" />

      <div className="grid grid-cols-2 gap-2">
        <Metric label="Total" value={stats.total} />
        <Metric label="New" value={stats.newCount} />
      </div>
      <div className="mt-2">
        <Metric label="High-fit (≥8)" value={stats.highFit} />
      </div>

      <hr className="my-5 border-line" />

      <CharacterQuote character={SIDEBAR_CHARACTER} />

      <p className="mt-4 text-[11px] leading-relaxed text-faint">
        v2.0 · {stats.sources.length > 0 ? stats.sources.join(" + ") : "no sources yet"}
      </p>

      <form
        className="mt-4"
        action={async () => {
          "use server";
          await signOut({ redirectTo: "/login" });
        }}
      >
        <button type="submit" className="btn-ghost w-full px-3 py-2 text-xs">
          Sign out
        </button>
      </form>
    </aside>
  );
}
