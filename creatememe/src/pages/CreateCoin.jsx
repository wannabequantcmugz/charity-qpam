import { useState, useCallback } from "react"
import { useWallet } from "@solana/wallet-adapter-react"
import { WalletMultiButton } from "@solana/wallet-adapter-react-ui"
import { Upload, ChevronRight, ChevronLeft, Check, Zap, Globe, MessageCircle, AlertCircle } from "lucide-react"

const STEPS = ["Token Info", "Details", "Review & Launch"]

export default function CreateCoin() {
  const { connected } = useWallet()
  const [step, setStep] = useState(0)
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(null)
  const [error, setError] = useState(null)
  const [imagePreview, setImagePreview] = useState(null)
  const [form, setForm] = useState({ name: "", symbol: "", image: null, description: "", website: "", twitter: "", telegram: "", decimals: 9, supply: "1000000000" })

  const update = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handleImage = useCallback((e) => {
    const file = e.target.files?.[0]
    if (!file) return
    update("image", file)
    const reader = new FileReader()
    reader.onloadend = () => setImagePreview(reader.result)
    reader.readAsDataURL(file)
  }, [])

  const canNext = () => {
    if (step === 0) return form.name.trim() && form.symbol.trim() && form.image
    return true
  }

  const launchToken = async () => {
    setLoading(true)
    setError(null)
    try {
      await new Promise(r => setTimeout(r, 2000))
      setSuccess({ signature: "devnet_demo_" + Date.now(), mint: "DemoMint" + Date.now() })
    } catch (err) {
      setError(err.message || "Transaction failed")
    } finally {
      setLoading(false)
    }
  }

  if (success) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center px-4">
        <div className="card max-w-lg w-full text-center animate-fade-up">
          <div className="w-16 h-16 bg-green/10 rounded-full flex items-center justify-center mx-auto mb-6">
            <Check size={32} className="text-green" />
          </div>
          <h2 className="font-display text-2xl font-bold mb-2">Token Launched!</h2>
          <p className="text-muted text-sm mb-6">Your token has been deployed on Solana devnet</p>
          <div className="bg-surface rounded-lg p-4 mb-6 text-left space-y-3">
            <div>
              <p className="text-muted text-xs mb-1 font-mono">MINT ADDRESS</p>
              <p className="text-accent-light text-xs font-mono break-all">{success.mint}</p>
            </div>
            <div>
              <p className="text-muted text-xs mb-1 font-mono">TRANSACTION</p>
              <p className="text-accent-light text-xs font-mono break-all">{success.signature}</p>
            </div>
          </div>
          <button onClick={() => { setSuccess(null); setStep(0); setImagePreview(null) }} className="btn-primary w-full">
            Launch Another Token
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-16">
      <div className="text-center mb-12">
        <h1 className="font-display text-5xl font-extrabold mb-3">Launch Your Own Coin <span className="text-orange">⚡</span></h1>
        <p className="text-muted">Deploy your own token on Solana in seconds. No coding required.</p>
      </div>

      <div className="flex items-center justify-center gap-0 mb-10">
        {STEPS.map((label, i) => (
          <div key={i} className="flex items-center">
            <div className="flex flex-col items-center gap-1">
              <div className={"w-9 h-9 rounded-full flex items-center justify-center font-display font-bold text-sm " + (i < step ? "bg-green text-bg" : i === step ? "bg-accent text-white" : "bg-surface border border-border text-muted")}>
                {i < step ? <Check size={16} /> : i + 1}
              </div>
              <span className={"text-[10px] font-mono whitespace-nowrap " + (i === step ? "text-accent-light" : "text-muted")}>{label}</span>
            </div>
            {i < STEPS.length - 1 && <div className={"w-24 h-px mx-2 mb-4 " + (i < step ? "bg-green/40" : "bg-border")} />}
          </div>
        ))}
      </div>

      <div className="card animate-fade-up">
        {step === 0 && (
          <div className="space-y-5">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-muted font-mono mb-2 block">TOKEN NAME</label>
                <input className="input-field" placeholder="Meme Coin" value={form.name} onChange={e => update("name", e.target.value)} />
              </div>
              <div>
                <label className="text-xs text-muted font-mono mb-2 block">TOKEN SYMBOL</label>
                <input className="input-field" placeholder="MEME" value={form.symbol} onChange={e => update("symbol", e.target.value.toUpperCase().slice(0, 10))} />
              </div>
            </div>
            <div>
              <label className="text-xs text-muted font-mono mb-2 block">TOKEN IMAGE</label>
              <label htmlFor="token-image" className="block w-full border-2 border-dashed border-border hover:border-accent rounded-xl p-8 cursor-pointer transition-colors text-center">
                {imagePreview ? (
                  <div className="flex flex-col items-center gap-3">
                    <img src={imagePreview} alt="Token" className="w-24 h-24 rounded-full object-cover ring-2 ring-accent" />
                    <span className="text-muted text-xs font-mono">{form.image?.name}</span>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-3">
                    <div className="w-12 h-12 bg-surface rounded-full flex items-center justify-center">
                      <Upload size={20} className="text-muted" />
                    </div>
                    <p className="text-sm"><span className="text-accent-light">Click to upload</span> or drag and drop</p>
                    <p className="text-xs text-muted">PNG or JPG, Max 5MB</p>
                  </div>
                )}
                <input id="token-image" type="file" accept="image/*" className="hidden" onChange={handleImage} />
              </label>
            </div>
          </div>
        )}

        {step === 1 && (
          <div className="space-y-5">
            <div>
              <label className="text-xs text-muted font-mono mb-2 block">DESCRIPTION</label>
              <textarea className="input-field resize-none h-24" placeholder="Tell the world about your token..." value={form.description} onChange={e => update("description", e.target.value)} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-muted font-mono mb-2 block">DECIMALS</label>
                <select className="input-field" value={form.decimals} onChange={e => update("decimals", Number(e.target.value))}>
                  <option value={0}>0 (NFT-style)</option>
                  <option value={6}>6 (USDC-style)</option>
                  <option value={9}>9 (SOL-style)</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-muted font-mono mb-2 block">TOTAL SUPPLY</label>
                <input className="input-field" type="number" value={form.supply} onChange={e => update("supply", e.target.value)} />
              </div>
            </div>
            <div className="space-y-3">
              <label className="text-xs text-muted font-mono block">SOCIAL LINKS</label>
              <div className="flex items-center gap-3"><Globe size={16} className="text-muted shrink-0" /><input className="input-field" placeholder="https://yourwebsite.com" value={form.website} onChange={e => update("website", e.target.value)} /></div>
              <div className="flex items-center gap-3"><span className="text-muted text-xs shrink-0 font-mono">X</span><input className="input-field" placeholder="https://x.com/..." value={form.twitter} onChange={e => update("twitter", e.target.value)} /></div>
              <div className="flex items-center gap-3"><MessageCircle size={16} className="text-muted shrink-0" /><input className="input-field" placeholder="https://t.me/..." value={form.telegram} onChange={e => update("telegram", e.target.value)} /></div>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-5">
            <div className="flex items-center gap-4 p-4 bg-surface rounded-xl">
              {imagePreview && <img src={imagePreview} alt="Token" className="w-16 h-16 rounded-full object-cover ring-2 ring-accent" />}
              <div>
                <p className="font-display font-bold text-xl">{form.name}</p>
                <p className="text-accent-light font-mono text-sm">${form.symbol}</p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              {[["Supply", Number(form.supply).toLocaleString()], ["Decimals", form.decimals], ["Network", "Solana Devnet"], ["Fee", "0.1 SOL"]].map(([k, v]) => (
                <div key={k} className="bg-surface rounded-lg p-3">
                  <p className="text-muted text-xs font-mono mb-1">{k}</p>
                  <p className="text-white text-sm font-medium">{v}</p>
                </div>
              ))}
            </div>
            {!connected && (
              <div className="flex items-center gap-3 p-4 bg-orange/10 border border-orange/20 rounded-xl">
                <AlertCircle size={18} className="text-orange shrink-0" />
                <p className="text-orange text-sm font-medium">Connect your wallet to deploy</p>
              </div>
            )}
          </div>
        )}

        {error && <div className="mt-4 flex items-center gap-2 text-red-400 text-xs font-mono bg-red-400/10 px-3 py-2 rounded-lg"><AlertCircle size={14} />{error}</div>}

        <div className="flex justify-between mt-8 pt-6 border-t border-border">
          <button onClick={() => setStep(s => s - 1)} className={"btn-ghost flex items-center gap-2 " + (step === 0 ? "invisible" : "")}>
            <ChevronLeft size={16} /> Back
          </button>
          {step < 2 ? (
            <button onClick={() => setStep(s => s + 1)} disabled={!canNext()} className="btn-primary flex items-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed">
              Next <ChevronRight size={16} />
            </button>
          ) : (
            <button onClick={launchToken} disabled={loading || !connected} className="btn-primary flex items-center gap-2 disabled:opacity-60">
              {loading ? <><span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Deploying...</> : <><Zap size={16} /> Launch Token</>}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
