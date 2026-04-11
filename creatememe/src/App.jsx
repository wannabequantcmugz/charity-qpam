import { Routes, Route, Navigate } from "react-router-dom"
import Navbar from "./components/Navbar"
import AnnouncementBar from "./components/AnnouncementBar"
import CreateCoin from "./pages/CreateCoin"
import ManageLiquidity from "./pages/ManageLiquidity"
import TrendingCoins from "./pages/TrendingCoins"
import PocResults from "./pages/PocResults"

export default function App() {
  return (
    <div className="min-h-screen mesh-bg">
      <AnnouncementBar />
      <Navbar />
      <main>
        <Routes>
          <Route path="/" element={<Navigate to="/create" replace />} />
          <Route path="/create" element={<CreateCoin />} />
          <Route path="/liquidity" element={<ManageLiquidity />} />
          <Route path="/trending" element={<TrendingCoins />} /> 
          <Route path="/poc" element={<PocResults />} /> 
        </Routes>
      </main>
    </div>
  )
}
