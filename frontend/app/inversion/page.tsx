import Link from "next/link";
import { fetchInversionFeeds } from "../../lib/api/inversionApi";
import InversionFeedList from "../../components/InversionFeedList";

// Force dynamic rendering to handle searchParams properly
export const dynamic = 'force-dynamic';

export default async function InversionPage({
  searchParams,
}: {
  searchParams: { symbol?: string; status?: string; narrative_risk?: string; page?: string };
}) {
  const page = Number(searchParams.page) || 1;
  const limit = 20;
  const offset = (page - 1) * limit;

  // Fetch data
  const { items, total } = await fetchInversionFeeds({
    symbol: searchParams.symbol,
    status: searchParams.status,
    narrative_risk: searchParams.narrative_risk,
    limit,
    offset,
  });

  return (
    <main className="max-w-4xl mx-auto p-4 md:p-8">
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center gap-4">
          <Link href="/" className="text-indigo-400 hover:underline text-sm">← Dashboard</Link>
          <h1 className="text-2xl font-bold">Inversion Feeds</h1>
        </div>
        {process.env.NEXT_PUBLIC_FEATURE_INVERSION !== 'true' && (
            <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded">Feature Flag: Disabled?</span>
        )}
      </div>
      
      <InversionFeedList initialItems={items} total={total} currentPage={page} />
    </main>
  );
}
