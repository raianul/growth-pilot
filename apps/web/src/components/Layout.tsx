import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useUIStore } from "../store/uiStore";
import { useAuth } from "../hooks/useAuth";
import OutletSwitcher from "./OutletSwitcher";

interface NavItem {
  label: string;
  icon: string;
  to: string;
}

const NAV_ITEMS: NavItem[] = [
  { label: "Dashboard", icon: "dashboard", to: "/dashboard" },
  { label: "Missions", icon: "checklist", to: "/missions" },
  { label: "Competitors", icon: "groups", to: "/competitors" },
  { label: "Analytics", icon: "bar_chart", to: "/analytics" },
  { label: "Organization", icon: "tune", to: "/settings/organization" },
  { label: "Outlets", icon: "store", to: "/settings/outlets" },
  { label: "Billing", icon: "credit_card", to: "/settings/billing" },
];

export default function Layout() {
  const { sidebarOpen, toggleSidebar } = useUIStore();
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  async function handleSignOut() {
    await signOut();
    navigate("/onboarding");
  }

  return (
    <div className="flex min-h-screen bg-surface">
      {/* Sidebar */}
      <aside
        className={`flex flex-col bg-surface-container-lowest shadow-ambient transition-all duration-300 ${
          sidebarOpen ? "w-64" : "w-16"
        }`}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-4 py-6">
          <div className="w-8 h-8 rounded-md bg-gradient-to-br from-primary to-primary-container flex items-center justify-center flex-shrink-0">
            <span className="material-symbols-outlined text-white text-base">
              rocket_launch
            </span>
          </div>
          {sidebarOpen && (
            <span className="font-headline font-extrabold text-on-surface text-lg leading-none">
              GrowthPilot
            </span>
          )}
        </div>

        {/* Outlet Switcher */}
        <div className="px-2 pb-4">
          <OutletSwitcher collapsed={!sidebarOpen} />
        </div>

        {/* Nav */}
        <nav className="flex-1 px-2 space-y-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${
                  isActive
                    ? "bg-primary/10 text-primary"
                    : "text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface"
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <span
                    className="material-symbols-outlined text-xl flex-shrink-0"
                    style={{ fontVariationSettings: isActive ? "'FILL' 1" : "'FILL' 0" }}
                  >
                    {item.icon}
                  </span>
                  {sidebarOpen && (
                    <span className="font-body text-sm font-medium">
                      {item.label}
                    </span>
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* User / sign out */}
        <div className="px-2 pb-4 space-y-1">
          <button
            onClick={handleSignOut}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface transition-colors"
          >
            <span className="material-symbols-outlined text-xl flex-shrink-0">
              logout
            </span>
            {sidebarOpen && (
              <span className="font-body text-sm font-medium">Sign out</span>
            )}
          </button>
          {sidebarOpen && user && (
            <p className="px-3 text-xs text-on-surface-variant truncate">
              {user.email}
            </p>
          )}
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="h-14 bg-surface-container-lowest shadow-ambient flex items-center px-4 gap-4">
          <button
            onClick={toggleSidebar}
            className="p-2 rounded-lg text-on-surface-variant hover:bg-surface-container-low transition-colors"
            aria-label="Toggle sidebar"
          >
            <span className="material-symbols-outlined text-xl">menu</span>
          </button>
        </header>

        {/* Content */}
        <main className="flex-1 p-6 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
