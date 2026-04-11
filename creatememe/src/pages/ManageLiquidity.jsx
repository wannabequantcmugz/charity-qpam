import { useState } from "react"
import { useWallet } from "@solana/wallet-adapter-react"
import { WalletMultiButton } from "@solana/wallet-adapter-react-ui"
import { Droplets, ChevronDown, Plus, Info } from "lucide-react"

const MOCK_TOKENS = [
  { mint: "token1", symbol: "PEPE", name: "Pepe Coin", balance: "1,000,000,000" },
  { mint: "token2", symbol: "DOGE", name: "Doge Token", balance: "420,690,000" },
]

export default function ManageLiquidity() {
  const { connected } = useWallet()
  const [selectedToken, setSelectedToken] = useState("")
  const [solAmount, setSolAmount] = useState("")
  const [tokenAmount, setTokenAmount] = useState("")
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const token = MOCK_TOKENS.find(t => t.mint === selectedToken)

  return (
    <div className="max-w-2xl mx-auto px-4 py-16">
      <div className="text-center mb-12">
        <h1 className="font-display text-4xl font-extrabold mb-3">Create Raydium Liquidity Pool</h1>
        <p className="text-muted text-sm">Pair your token with SOL and launch a tradable market on Raydium.</p>
      </div>
      <div className="card animate-fade-up">
        <div className="mb-6">
          <label className="text-xs text-muted font-mono mb-2 block">FOR WHICH TOKEN WOULD YOU LIKE TO CREATE A POOL?</label>
          <div className="relative">
            <button onClick={() => setDropdownOpen(o => !o)} className="w-full input-field flex items-center justify-between text-left" disabled={!connected}>
              {token ? (
                <div className="flex items-center gap-3">
                  <div className="w-7 h-7 bg-accent/20 rounded-full flex items-center justify-center">
                    <span className="text-accent-light text-xs font-bold">{token.symbol[0]}</span>
                  </div>
                  <span className="text-white text-sm">{token.name}</span>
                </div>
              ) : (
                <span className="text-muted">Choose your token</span>
              )}
              <ChevronDown size={16} className={"text-muted transition-transform " + (dropdownOpen ? "rotate-180" : "")} />
            </button>
            {dropdownOpen && connected && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-card border border-border rounded-xl overflow-hidden z-10">
                {MOCK_TOKENS.map(t => (
                  <button key={t.mint} onClick={() => { setSelectedToken(t.mint); setDropdownOpen(false) }} className="w-full flex items-center justify-between px-4 py-3 hover:bg-surface transition-colors text-left">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-accent/20 rounded-full flex items-center justify-center">
                        <span className="text-accent-light text-sm font-bold">{t.symbol[0]}</span>
                      </div>
                      <div>
                        <p className="text-white text-sm">{t.name}</p>
                        <p className="text-muted text-xs font-mono">${t.symbol}</p>
                      </div>
                    </div>
                    <span className="text-muted text-xs font-mono">{t.balance}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
        {selectedToken && connected && (
          <div className="space-y-4 mb-6">
            <div className="bg-surface rounded-xl p-4">
              <label className="text-xs text-muted font-mono mb-2 block">INITIAL SOL AMOUNT</label>
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-gradient-to-br from-purple-400 to-cyan-400 rounded-full flex-shrink-0" />
                <input type="number" value={solAmount} onChange={e => setSolAmount(e.target.value)} placeholder="0.00" className="flex-1 bg-transparent text-2xl font-display font-bold text-white placeholder-muted outline-none" />
                <span className="text-muted font-mono text-sm">SOL</span>
              </div>
            </div>
            <div className="flex items-center justify-center">
              <div className="w-8 h-8 bg-surface border border-border rounded-full flex items-center justify-center">
                <Plus size={14} className="text-muted" />
              </div>
            </div>
            <div className="bg-surface rounded-xl p-4">
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs text-muted font-mono">INITIAL {token?.symbol} AMOUNT</label>
                <span className="text-xs text-muted font-mono">Balance: {token?.balance}</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-accent/20 rounded-full flex items-center justify-center flex-shrink-0">
                  <span className="text-accent-light text-sm font-bold">{token?.symbol[0]}</span>
                </div>
                <input type="number" value={tokenAmount} onChange={e => setTokenAmount(e.target.value)} placeholder="0.00" className="flex-1 bg-transparent text-2xl font-display font-bold text-white placeholder-muted outline-none" />
                <span className="text-muted font-mono text-sm">{token?.symbol}</span>
              </div>
            </div>
            {solAmount && tokenAmount && (
              <div className="flex items-center gap-2 p-3 bg-accent/5 border border-accent/10 rounded-lg">
                <Info size={14} className="text-accent-light shrink-0" />
                <p className="text-xs text-muted font-mono">
                  Initial price: <span className="text-accent-light">{(Number(solAmount) / Number(tokenAmount)).toFixed(8)} SOL / {token?.symbol}</span>
                </p>
              </div>
            )}
          </div>
        )}
        {!connected ? (
          <div className="text-center py-8">
            <Droplets size={24} className="text-muted mx-auto mb-4" />
            <p className="text-white font-display font-semibold mb-1">Please connect your wallet to create a pool.</p>
            <p className="text-muted text-sm mb-6">You will need SOL to pay for pool creation fees.</p>
            <WalletMultiButton />
          </div>
        ) : (
          <button onClick={() => { setLoading(true); setTimeout(() => setLoading(false), 2000) }} disabled={!selectedToken || !solAmount || !tokenAmount || loading} className="btn-primary w-full flex items-center justify-center gap-2 py-3 disabled:opacity-40 disabled:cursor-not-allowed">
            {loading ? <><span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Creating Pool...</> : <><Droplets size={18} /> Create Liquidity Pool</>}
          </button>
        )}
      </div>
    </div>
  )
}
