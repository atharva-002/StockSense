import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import TopNav from "@/components/stocksense/TopNav";
import WakeBanner from "@/components/stocksense/WakeBanner";
import OverviewPage from "@/pages/Overview";
import ForecastPage from "@/pages/Forecast";
import ModelsPage from "@/pages/Models";
import InventoryPage from "@/pages/Inventory";
import MonitoringPage from "@/pages/Monitoring";
import ArchitecturePage from "@/pages/Architecture";
import "@/App.css";

function App() {
  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 font-body">
      <BrowserRouter>
        <TopNav />
        <WakeBanner />
        <main className="pt-24 pb-16 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
          <Routes>
            <Route path="/" element={<OverviewPage />} />
            <Route path="/forecast" element={<ForecastPage />} />
            <Route path="/models" element={<ModelsPage />} />
            <Route path="/inventory" element={<InventoryPage />} />
            <Route path="/monitoring" element={<MonitoringPage />} />
            <Route path="/architecture" element={<ArchitecturePage />} />
          </Routes>
        </main>
        <Toaster position="bottom-right" richColors />
      </BrowserRouter>
    </div>
  );
}

export default App;
