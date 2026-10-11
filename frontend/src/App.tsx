import { NavLink, Route, Routes } from "react-router-dom";
import ClusterCleanupPage from "./pages/ClusterCleanup";
import CoverArtPage from "./pages/CoverArt";
import DuplicateFinderPage from "./pages/DuplicateFinder";
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

export default function App() {
  return (
    <div className="app-shell">
      <nav className="sidebar">
        <h1>Music Toolkit</h1>
        {LINKS.map((l) => (
          <NavLink key={l.to} to={l.to} end className={({ isActive }) => (isActive ? "active" : "")}>
            {l.label}
          </NavLink>
        ))}
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
