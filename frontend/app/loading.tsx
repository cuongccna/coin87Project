export default function Loading() {
  return (
    <div className="min-h-screen bg-bg text-text">
      <div className="mx-auto max-w-6xl px-4 py-6">
        {/* Top bar skeleton */}
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="skeleton h-5 w-16" />
            <div className="skeleton h-8 w-24 rounded-md" />
          </div>
          <div className="flex items-center gap-3">
            <div className="skeleton h-8 w-32 rounded-md" />
          </div>
        </div>

        {/* Market state skeleton */}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <div className="rounded-lg border border-border bg-panel p-4 shadow-soft">
              <div className="skeleton mb-2 h-3 w-20" />
              <div className="flex items-baseline gap-4">
                <div className="skeleton h-6 w-24" />
                <div className="skeleton h-4 w-12" />
                <div className="skeleton h-4 w-12" />
              </div>
            </div>
          </div>
          <div className="lg:col-span-1">
            <div className="rounded-lg border border-border bg-panel p-4 shadow-soft">
              <div className="skeleton mb-3 h-3 w-16" />
              <div className="grid grid-cols-2 gap-3">
                {[...Array(5)].map((_, i) => (
                  <div key={i}>
                    <div className="skeleton mb-1 h-2 w-14" />
                    <div className="skeleton h-4 w-20" />
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Filters skeleton */}
        <div className="mt-4 rounded-lg border border-border bg-panel p-3 shadow-soft">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="flex items-center justify-between">
                <div className="skeleton h-3 w-12" />
                <div className="skeleton h-7 w-36 rounded-md" />
              </div>
            ))}
          </div>
        </div>

        {/* News cards skeleton */}
        <div className="mt-4">
          <div className="flex items-end justify-between">
            <div>
              <div className="skeleton mb-1 h-3 w-28" />
              <div className="skeleton h-4 w-24" />
            </div>
            <div className="skeleton h-3 w-16" />
          </div>

          <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
            {[...Array(4)].map((_, i) => (
              <div
                key={i}
                className="min-h-[118px] rounded-lg border border-l-2 border-border bg-panel p-3 shadow-soft"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <div className="skeleton h-4 w-4 rounded" />
                      <div className="skeleton h-4 w-48" />
                    </div>
                    <div className="skeleton mt-2 h-3 w-full max-w-xs" />
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    <div className="skeleton h-3 w-20" />
                    <div className="skeleton h-4 w-8" />
                    <div className="skeleton h-3 w-14" />
                  </div>
                </div>
                <div className="mt-2 flex items-center justify-between">
                  <div className="skeleton h-5 w-16 rounded" />
                  <div className="skeleton h-3 w-20" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
