export default function PocResults() {
  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="max-w-xl w-full bg-white/5 border border-white/10 rounded-2xl p-8">
        <h1 className="text-2xl font-bold text-white mb-6">POC Status</h1>

        <div className="space-y-4">
          <div className="flex items-center gap-3 bg-green-500/10 border border-green-500/20 rounded-lg p-4">
            <span className="text-green-400 text-xl">✓</span>
            <div>
              <p className="text-green-400 font-medium">Anchor Sync</p>
              <p className="text-white/50 text-sm">Keys synced successfully</p>
            </div>
          </div>

          <div className="flex items-center gap-3 bg-green-500/10 border border-green-500/20 rounded-lg p-4">
            <span className="text-green-400 text-xl">✓</span>
            <div>
              <p className="text-green-400 font-medium">Anchor Build</p>
              <p className="text-white/50 text-sm">Program built successfully</p>
            </div>
          </div>

          <div className="flex items-center gap-3 bg-green-500/10 border border-green-500/20 rounded-lg p-4">
            <span className="text-green-400 text-xl">✓</span>
            <div>
              <p className="text-green-400 font-medium">Anchor Test</p>
              <p className="text-white/50 text-sm">All tests passed</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
