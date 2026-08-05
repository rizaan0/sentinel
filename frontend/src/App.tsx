import { Routes, Route, Navigate } from "react-router-dom";

import LandingPage from "./pages/marketing/LandingPage";
import LoginPage from "./pages/auth/LoginPage";
import SignupPage from "./pages/auth/SignupPage";
import PinSetupPage from "./pages/auth/PinSetupPage";
import DashboardPage from "./pages/user/DashboardPage";
import SendMoneyPage from "./pages/user/SendMoneyPage";
import AdminDashboardPage from "./pages/admin/AdminDashboardPage";
import RequireAuth, { RequireAdmin } from "./routes/RequireAuth";

/**
 * Top-level route groups: marketing (public), auth, user app, admin app.
 */
function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />

      <Route element={<RequireAuth />}>
        <Route path="/pin-setup" element={<PinSetupPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/send" element={<SendMoneyPage />} />
      </Route>

      <Route element={<RequireAdmin />}>
        <Route path="/admin" element={<AdminDashboardPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
