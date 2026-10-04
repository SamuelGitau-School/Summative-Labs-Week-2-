import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

// Only signed-in users may see the children; everyone else goes to /signin.
export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <p className="loading">Checking your session…</p>;
  if (!user) return <Navigate to="/signin" replace state={{ from: location }} />;
  return children;
}
