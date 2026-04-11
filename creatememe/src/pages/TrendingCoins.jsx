import { useState, useEffect } from "react"
import { useWallet } from "@solana/wallet-adapter-react"
import { WalletMultiButton } from "@solana/wallet-adapter-react-ui"
import { RefreshCw, Zap, MessageCircle } from "lucide-react"

const MOCK_TRENDING = [
  { id: 1, name: "Chudjak", symbol: "Chud", marketCap: 1111266, replies: 881, lastBuy: "10s", tags: ["pump", "twitter", "telegram"] },
  { id: 2, name: "Pippin", symbol: "pippin", marketCap: 347658246, replies: 20780, lastBuy: "11s", tags: ["pump", "twitter"] },
  { id: 3, name: "blormmy", symbol: "blormmy", marketCap: 54606, replies: 125, lastBuy: "11s", tags: ["pump"] },
  { id: 4, name: "Comedian", symbol: "Ban", marketCap: 113310240, replies: 5048, lastBuy: "12s", tags: ["pump"] },
  { id: 5, name: "401jk", symbol: "401jk", marketCap: 2124184, replies: 1471, lastBuy: "12s", tags: ["pump", "twitter"] },
  { id: 6, name: "AgixCloudAI", symbol: "AgixAI", marketCap: 26826, replies: 176, lastBuy: "12s", tags: ["pump"] },
  { id: 7, name: "GORK", symbol: "GORK", marketCap: 88420000, replies: 9321, lastBuy: "5s", tags: ["pump", "twitter"] },
  { id: 8, name: "LetsBONK", symbol: "BONK2", marketCap: 4200000, replies: 2211, lastBuy: "8s", tags: ["pump"] },
]

const MOCK_NEW = [
  { id: 9, name: "FartCoin2", symbol: "FART2", marketCap: 1240, replies: 3, lastBuy: "2s", tags: ["pump"] },
  { id: 10, name: "BasedPepe", symbol: "BPEPE", marketCap: 8800, replies: 14, lastBuy: "5s", tags: ["pump"] },
  { id: 11, name: "SolanaInu", symbol: "SINU", marketCap: 22000, replies: 52, lastBuy: "9s", tags: ["pump"] },
  { id: 12, name: "MoonDoge", symbol: "MDOGE", marketCap: 5500, replies: 7, lastBuy: "1s", tags: ["pump"] },
]

function formatMcap(n) {
  if (n >= 1000000) return "$" + (n / 1000000).toFixed(2) + "M"
  if (n >= 1000) return "$" + (n / 1000).toFixed(1) + "K"
  return "$" + n.toLocaleString()
}

function CoinCard({ coin }) {
  const { connected } = useWallet()
  const [copying, setCopying] = useState(false)

  const handleCopy = async () => {
    if (!connected) return
    setCopying(true)
    setTimeout(() => setCopying(false), 2000)
  }

  const mcapColor = coin.marketCap > 100000000 ? "text-green" : coin.marketCap > 1000000 ? "text-yellow-400" : "text-muted"

  return (
    <div className="coin-card">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-accent/20 border border-border flex items-center justify-center font-display font-bold text-sm text-accent-light flex-shrink-0">
            {coin.symbol[0]}
          </div>
          <div>
            <p className="font-display font-bold text-white text-sm">{coin.name}</p>
            <p className="text-muted text-xs font-mono">${coin.symbol} · {coin.replies.toLocaleString()} replies</p>
          </div>
        </div>
        <div className="text-right">
          <p className="text-muted text-xs font-mono mb-0.5">Market Cap:</p>
          <p className={"font-display font-bold text-sm " + mcapColor}>{formatMcap(coin.marketCap)}</p>
        </div>
      </div>
      <div className="flex items-center justify-between mt-3">
        <div className="flex items-center gap-2">
          <span className="text-orange text-xs font-mono">Last buy: {coin.lastBuy} ago</span>
          <div className="flex items-center gap-1 ml-1">
            {coin.tags.includes("twitter") && <span className="text-muted text-xs">X</span>}
            {coin.tags.includes("telegram") && <MessageCircle size={12} className="text-muted" />}
            {coin.tags.includes("pump") && <span className="text-green text-xs">🌱</span>}
          </div>
        </div>
        <button onClick={handleCopy} disabled={!connected || copying} className="flex items-center gap-1.5 bg-accent hover:bg-accent-light disabled:opacity-50 text-white text-xs font-semibold px-3 py-1.5 rounded-lg transition-all">
          {copying ? <><RefreshCw size={12} className="animate-spin" /> Copying...</> : <><Zap size={12} /> Copy to Raydium</>}
        </button>
      </div>
    </div>
  )
}

export default function TrendingCoins() {
  const { connected } = useWallet()
  const [tab, setTab] = useState("trending")
  const [refreshing, setRefreshing] = useState(false)
  const [coins, setCoins] = useState(MOCK_TRENDING)

  useEffect(() => {
    setCoins(tab === "trending" ? MOCK_TRENDING : MOCK_NEW)
  }, [tab])

  return (
    <div className="max-w-6xl mx-auto px-4 py-12">
      <div className="text-center mb-10">
        <h1 className="font-display text-5xl font-extrabold mb-3">Copy Trending Coins in 1 Click ⚡</h1>
        <p className="text-muted text-sm">Copy the latest trending coins from pump.fun and deploy on Raydium before the community does.</p>
      </div>

      <div className="ticker-wrap mb-8 border-y border-border py-2">
        <div className="ticker-inner">
          {[...MOCK_TRENDING, ...MOCK_TRENDING].map((c, i) => (
            <span key={i} className="inline-flex items-center gap-2 mr-8 text-xs font-mono text-muted">
              <span className="text-white">{c.symbol}</span>
              <span className="text-green">{formatMcap(c.marketCap)}</span>
            </span>
          ))}
        </div>
      </div>

      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-1 bg-surface border border-border rounded-xl p-1">
          {["trending", "new"].map(t => (
            <button key={t} onClick={() => setTab(t)} className={"px-5 py-2 rounded-lg text-sm font-display font-semibold capitalize transition-all duration-200 " + (tab === t ? "bg-accent text-white" : "text-muted hover:text-white")}>
              {t === "trending" ? "Trending" : "New"}
            </button>
          ))}
        </div>
        <button onClick={() => { setRefreshing(true); setTimeout(() => { setCoins(c => [...c].sort(() => Math.random() - 0.5)); setRefreshing(false) }, 1000) }} className="p-2 bg-surface border border-border rounded-xl text-muted hover:text-white transition-all">
          <RefreshCw size={16} className={refreshing ? "animate-spin" : ""} />
        </button>
      </div>

      {!connected && (
        <div className="mb-6 flex items-center gap-4 p-4 bg-orange/5 border border-orange/20 rounded-xl">
          <Zap size={18} className="text-orange shrink-0" />
          <div className="flex-1">
            <p className="text-white text-sm font-semibold">Connect wallet to copy coins</p>
            <p className="text-muted text-xs">You need a connected wallet to deploy tokens</p>
          </div>
          <WalletMultiButton />
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {coins.map(coin => <CoinCard key={coin.id} coin={coin} />)}
      </div>

      <div className="mt-12 p-5 bg-surface border border-border rounded-xl">
        <p className="text-muted text-xs text-center">This is a non-custodial interface. All actions are performed on-chain and approved by your wallet.</p>
      </div>
    </div>
  )
}
