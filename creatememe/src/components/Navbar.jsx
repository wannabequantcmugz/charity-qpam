import { NavLink } from "react-router-dom"
import { WalletMultiButton } from "@solana/wallet-adapter-react-ui"
import { Rocket, Droplets, TrendingUp } from "lucide-react"

export default function Navbar() {
  return (
    <nav className="sticky top-0 z-50 border-b border-border bg-bg/80 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 flex items-center justify-between h-14">
        <NavLink to="/create" className="flex items-center gap-2">
          <div className="w-8 h-8 bg-accent rounded-lg flex items-center justify-center">
            <Rocket size={16} className="text-white" />
          </div>
          <span className="font-display font-bold text-lg">
            Create<span className="text-accent-light">Meme</span>
          </span>
        </NavLink>

        <div className="flex items-center gap-1">
          <NavLink to="/create" className={({ isActive }) => `nav-link ${isActive ? "text-white bg-surface" : ""}`}>
            <Rocket size={15} /> Create Coin
          </NavLink>
          <NavLink to="/liquidity" className={({ isActive }) => `nav-link ${isActive ? "text-white bg-surface" : ""}`}>
            <Droplets size={15} /> Manage Liquidity
          </NavLink>
          <NavLink to="/trending" className={({ isActive }) => `nav-link ${isActive ? "text-white bg-surface" : ""}`}>
            <TrendingUp size={15} /> Copy Trending Coins
            <span className="bg-green text-bg text-[10px] font-bold px-1.5 py-0.5 rounded">NEW</span>
          </NavLink>
        </div>

        <WalletMultiButton />
      </div>
    </nav>
  )
}
