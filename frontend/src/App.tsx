import { BrowserRouter, Routes, Route } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import SubmitClaim from "./pages/SubmitClaim";
import ClaimDetail from "./pages/ClaimDetail";

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        {/* Top Nav */}
        <nav className="bg-white border-b border-gray-200 px-6 py-3">
          <div className="max-w-6xl mx-auto flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">P</span>
            </div>
            <a href="/" className="font-semibold text-gray-900 hover:text-blue-600 transition-colors">
              Plum Claims
            </a>
            <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
              AI Processing Pipeline
            </span>
          </div>
        </nav>

        {/* Main Content */}
        <main className="max-w-6xl mx-auto px-6 py-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/submit" element={<SubmitClaim />} />
            <Route path="/claims/:id" element={<ClaimDetail />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
