import { useEffect, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { api, setUnauthorizedHandler } from "./api/client";
import ClusterCleanupPage from "./pages/ClusterCleanup";
import CoverArtPage from "./pages/CoverArt";
import DuplicateFinderPage from "./pages/DuplicateFinder";
import LoginPage from "./pages/Login";
import M3uFixPage from "./pages/M3uFix";
import PlaylistFoldersPage from "./pages/PlaylistFolders";
import PlaylistStudioPage from "./pages/PlaylistStudio";
import PromptsLibraryPage from "./pages/PromptsLibrary";
import SchedulerPage from "./pages/Scheduler";
import StatusPage from "./pages/Status";
import TidarrImportsPage from "./pages/TidarrImports";

const LINKS = [
  { to: "/", label: "Status" },
  { to: "/duplicates", label: "Duplicate finder" },
  { to: "/cluster-cleanup", label: "Cluster cleanup" },
  { to: "/tidarr-imports", label: "Tidarr imports" },
  { to: "/playlist-folders", label: "Playlist folders" },
  { to: "/m3u-fix", label: "Fix m3u paths" },
  { to: "/cover-art", label: "Cover art" },
  { to: "/prompts", label: "Prompts library" },
  { to: "/playlist-studio", label: "Playlist Studio" },
  { to: "/scheduler", label: "Scheduler" },
];

type AuthState = "loading" | "in" | "out";

export default function App() {
  const [auth, setAuth] = useState<AuthState>("loading");

  useEffect(() => {
    setUnauthorizedHandler(() => setAuth("out"));
    api
      .get<{ authenticated: boolean }>("/api/auth/whoami")
      .then((r) => setAuth(r.authenticated ? "in" : "out"))
      .catch(() => setAuth("out"));
    return () => setUnauthorizedHandler(null);
  }, []);

  const logout = () => {
    api.post("/api/auth/logout").finally(() => setAuth("out"));
  };

  if (auth === "loading") return null;
  if (auth === "out") return <LoginPage onSuccess={() => setAuth("in")} />;

  return (
    <div className="app-shell">
      <nav className="sidebar">
        <h1>Music Toolkit</h1>
        {LINKS.map((l) => (
          <NavLink key={l.to} to={l.to} end className={({ isActive }) => (isActive ? "active" : "")}>
            {l.label}
          </NavLink>
        ))}
        <div style={{ flex: 1 }} />
        <button onClick={logout} style={{ margin: "8px 10px" }}>
          Log out
        </button>
      </nav>
      <main className="content">
        <Routes>
          <Route path="/" element={<StatusPage />} />
          <Route path="/duplicates" element={<DuplicateFinderPage />} />
          <Route path="/cluster-cleanup" element={<ClusterCleanupPage />} />
          <Route path="/tidarr-imports" element={<TidarrImportsPage />} />
          <Route path="/playlist-folders" element={<PlaylistFoldersPage />} />
          <Route path="/m3u-fix" element={<M3uFixPage />} />
          <Route path="/cover-art" element={<CoverArtPage />} />
          <Route path="/prompts" element={<PromptsLibraryPage />} />
          <Route path="/playlist-studio" element={<PlaylistStudioPage />} />
          <Route path="/scheduler" element={<SchedulerPage />} />
        </Routes>
      </main>
    </div>
  );
}
