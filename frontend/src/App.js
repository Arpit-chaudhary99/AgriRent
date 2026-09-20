import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import "@/App.css";

import LoginPage from "./pages/LoginPage";
import AuthCallback from "./pages/AuthCallback";
import UserLayout from "./layouts/UserLayout";
import BrowsePage from "./pages/BrowsePage";
import RentalsPage from "./pages/RentalsPage";
import ProfilePage from "./pages/ProfilePage";
import AdminLayout from "./layouts/AdminLayout";
import AdminDashboard from "./pages/admin/AdminDashboard";
import AdminTools from "./pages/admin/AdminTools";
import AdminUsers from "./pages/admin/AdminUsers";
import AdminRentals from "./pages/admin/AdminRentals";
import AdminPayments from "./pages/admin/AdminPayments";

function PrivateRoute({ children, adminOnly = false }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="page-loader" data-testid="page-loader">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (adminOnly && user.role !== "ADMIN") return <Navigate to="/browse" replace />;
  return children;
}

function AppRouter() {
  const location = useLocation();
  // Detect callback synchronously during render (see auth playbook)
  if (location.hash?.includes("session_id=")) return <AuthCallback />;
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/dashboard" element={<AuthCallback />} />
      <Route element={<PrivateRoute><UserLayout /></PrivateRoute>}>
        <Route path="/browse" element={<BrowsePage />} />
        <Route path="/rentals" element={<RentalsPage />} />
        <Route path="/profile" element={<ProfilePage />} />
      </Route>
      <Route element={<PrivateRoute adminOnly><AdminLayout /></PrivateRoute>}>
        <Route path="/admin" element={<AdminDashboard />} />
        <Route path="/admin/tools" element={<AdminTools />} />
        <Route path="/admin/users" element={<AdminUsers />} />
        <Route path="/admin/rentals" element={<AdminRentals />} />
        <Route path="/admin/payments" element={<AdminPayments />} />
      </Route>
      <Route path="*" element={<Navigate to="/browse" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRouter />
      </BrowserRouter>
    </AuthProvider>
  );
}
