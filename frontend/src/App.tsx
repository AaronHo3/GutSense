
import { BrowserRouter, Routes, Route, Navigate, NavLink } from 'react-router-dom';
import { PatientDashboard } from './pages/PatientDashboard';
import { PhysicianPortal } from './pages/PhysicianPortal';
import { PatientDetail } from './pages/PatientDetail';
import { IrisDashboard } from './pages/IrisDashboard';
import { Activity, Stethoscope, Database } from 'lucide-react';

function Nav() {
  return (
    <nav className="px-6 py-3 flex items-center justify-between sticky top-0 z-10" style={{ background: 'rgba(6,12,26,0.85)', backdropFilter: 'blur(16px)', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
      <div className="flex items-center gap-2.5">
        <div className="w-7 h-7 rounded-lg bg-emerald-500 flex items-center justify-center shadow-lg shadow-emerald-500/30">
          <Activity className="w-4 h-4 text-white" />
        </div>
        <span className="font-bold text-white text-sm tracking-tight">GutSense</span>
        <span className="text-xs text-slate-500 hidden sm:inline">CRC Screening Platform</span>
      </div>
      <div className="flex gap-1 p-1 rounded-lg" style={{ background: 'rgba(255,255,255,0.06)' }}>
        <NavLink
          to="/patient/1"
          className={({ isActive }) =>
            `flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              isActive
                ? 'bg-white/15 text-white shadow-sm'
                : 'text-slate-400 hover:text-white'
            }`
          }
        >
          <Activity className="w-3.5 h-3.5" />
          Patient
        </NavLink>
        <NavLink
          to="/physician"
          className={({ isActive }) =>
            `flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              isActive
                ? 'bg-white/15 text-white shadow-sm'
                : 'text-slate-400 hover:text-white'
            }`
          }
        >
          <Stethoscope className="w-3.5 h-3.5" />
          Physician
        </NavLink>
        <NavLink
          to="/iris"
          className={({ isActive }) =>
            `flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              isActive
                ? 'bg-white/15 text-white shadow-sm'
                : 'text-slate-400 hover:text-white'
            }`
          }
        >
          <Database className="w-3.5 h-3.5" />
          IRIS
        </NavLink>
      </div>
    </nav>
  );
}

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen" style={{ background: 'linear-gradient(135deg, #0a0f1e 0%, #0d1b3e 50%, #0a1628 100%)' }}>
        <Nav />
        <Routes>
          <Route path="/" element={<Navigate to="/patient/1" replace />} />
          <Route path="/patient/:patientId" element={<PatientDashboard />} />
          <Route path="/physician" element={<PhysicianPortal />} />
          <Route path="/physician/patient/:patientId" element={<PatientDetail />} />
          <Route path="/iris" element={<IrisDashboard />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
