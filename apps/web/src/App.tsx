import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./hooks/useAuth";
import Layout from "./components/Layout";

// Onboarding
import SetupBusiness from "./routes/onboarding/SetupBusiness";
import BrandVoice from "./routes/onboarding/BrandVoice";

// App routes
import Dashboard from "./routes/Dashboard";
import Missions from "./routes/Missions";
import MissionDetail from "./routes/MissionDetail";
import MissionContent from "./routes/MissionContent";
import Competitors from "./routes/Competitors";
import Analytics from "./routes/Analytics";
import DimensionDetail from "./routes/DimensionDetail";
import BrandIdentity from "./routes/settings/BrandIdentity";
import Outlets from "./routes/settings/Outlets";
import Billing from "./routes/settings/Billing";

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { session, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-surface">
        <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!session) {
    return <Navigate to="/onboarding" replace />;
  }

  return <>{children}</>;
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  const { session, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-surface">
        <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (session) {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      {/* Public / onboarding */}
      <Route
        path="/onboarding"
        element={<SetupBusiness />}
      />
      <Route path="/onboarding/brand-voice" element={<BrandVoice />} />

      {/* Authenticated app */}
      <Route
        path="/"
        element={
          <PrivateRoute>
            <Layout />
          </PrivateRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="missions" element={<Missions />} />
        <Route path="missions/:id" element={<MissionDetail />} />
        <Route path="missions/:id/content" element={<MissionContent />} />
        <Route path="dimensions/:key" element={<DimensionDetail />} />
        <Route path="competitors" element={<Competitors />} />
        <Route path="analytics" element={<Analytics />} />
        <Route path="settings/organization" element={<BrandIdentity />} />
        <Route path="settings/outlets" element={<Outlets />} />
        <Route path="settings/billing" element={<Billing />} />
        {/* Legacy redirect */}
        <Route
          path="settings/brand-identity"
          element={<Navigate to="/settings/organization" replace />}
        />
      </Route>

      {/* Catch-all */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
