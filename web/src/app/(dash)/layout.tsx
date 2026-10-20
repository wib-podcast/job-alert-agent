import { Sidebar } from "@/components/Sidebar";
import { TabNav } from "@/components/TabNav";
import { boardStats, facets } from "@/lib/jobs";

export const dynamic = "force-dynamic";

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [stats, { sources }] = await Promise.all([boardStats(), facets()]);

  return (
    <div className="flex min-h-dvh flex-col lg:flex-row">
      <Sidebar
        stats={{
          total: stats.total,
          newCount: stats.newCount,
          highFit: stats.highFit,
          sources: sources.map((s) => s.value),
        }}
      />
      <main className="min-w-0 flex-1 px-4 py-6 sm:px-8 [padding-bottom:calc(2rem+env(safe-area-inset-bottom,0px))]">
        <div className="mx-auto w-full max-w-5xl">
          <TabNav />
          {children}
        </div>
      </main>
    </div>
  );
}
