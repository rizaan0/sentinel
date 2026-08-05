import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../lib/useAuth";

/**
 * Gate: user must be authenticated. If they are, but haven't set a
 * Transaction PIN yet, they are forced to /pin-setup before anything else
 * (idea.md: PIN creation is required before first use of the app).
 */
export default function RequireAuth() {
  const { user, token, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <FullScreenLoader />;
  }

  if (!token || !user) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  if (!user.pin_is_set && location.pathname !== "/pin-setup") {
    return <Navigate to="/pin-setup" replace />;
  }

  return <Outlet />;
}

export function RequireAdmin() {
  const { user, token, isLoading } = useAuth();

  if (isLoading) {
    return <FullScreenLoader />;
  }

  if (!token || !user) {
    return <Navigate to="/login" replace />;
  }

  if (user.role !== "admin") {
    return <Navigate to="/dashboard" replace />;
  }

  return <Outlet />;
}

function FullScreenLoader() {
  return (
    <div className="min-h-screen flex items-center justify-center text-neutral-500">
      Loading...
    </div>
  );
}
