
import { BrowserRouter, Routes, Route, Navigate, NavLink } from 'react-router-dom';
import { PatientDashboard } from './pages/PatientDashboard';
import { PhysicianPortal } from './pages/PhysicianPortal';
import { PatientDetail } from './pages/PatientDetail';
import { IrisDashboard } from './pages/IrisDashboard';
import { AnalyticsDashboard } from './pages/AnalyticsDashboard';

const NAV = [
  { to: '/patient/1', label: 'Patient' },
  { to: '/physician', label: 'Physician' },
  { to: '/iris', label: 'IRIS' },
  { to: '/analytics', label: 'Analytics' },
];

function Nav() {
  return (
    <nav
      className="sticky top-0 z-20 px-4 sm:px-8 h-16 flex items-center justify-between gap-3"
      style={{ background: 'rgba(244,241,234,0.82)', backdropFilter: 'blur(12px)', borderBottom: '1px solid var(--line)' }}
    >
      <NavLink to="/patient/1" className="flex items-baseline gap-2.5 group flex-shrink-0">
        <span className="font-serif text-ink leading-none text-xl sm:text-[1.35rem]" style={{ fontWeight: 500, letterSpacing: '-0.01em' }}>
          GutSense
        </span>
        <span className="eyebrow hidden md:inline" style={{ fontSize: '0.625rem' }}>
          Continuous CRC Screening
        </span>
      </NavLink>

      <div className="flex items-center gap-4 sm:gap-7">
        {NAV.map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `relative pb-1 transition-colors text-[0.7rem] sm:text-xs ${isActive ? 'text-ink' : 'text-faint hover:text-muted'}`
            }
            style={{
              fontFamily: "'Spline Sans Mono', monospace",
              letterSpacing: '0.05em',
            }}
          >
            {({ isActive }) => (
              <>
                {item.label}
                {isActive && (
                  <span
                    className="absolute left-0 right-0 -bottom-px h-px"
                    style={{ background: 'var(--ink)' }}
                  />
                )}
              </>
            )}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-paper">
        <Nav />
        <Routes>
          <Route path="/" element={<Navigate to="/patient/1" replace />} />
          <Route path="/patient/:patientId" element={<PatientDashboard />} />
          <Route path="/physician" element={<PhysicianPortal />} />
          <Route path="/physician/patient/:patientId" element={<PatientDetail />} />
          <Route path="/iris" element={<IrisDashboard />} />
          <Route path="/analytics" element={<AnalyticsDashboard />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
