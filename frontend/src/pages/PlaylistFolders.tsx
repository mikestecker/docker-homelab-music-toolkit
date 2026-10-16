import { useMemo, useRef, useState, type DragEvent, type ReactNode } from "react";
import { useEffect } from "react";
import { api } from "../api/client";
import Drawer from "../components/Drawer";
import ErrorBanner from "../components/ErrorBanner";
import ToastView from "../components/Toast";
import { useApiError } from "../hooks/useApiError";
import { useToast } from "../hooks/useToast";

interface FolderNode {
  id: string;
  name: string;
  parent_id: string | null;
}

interface PlaylistLeaf {
  id: string;
  name: string;
  leaf_name: string;
  owner: string | null;
  folder_id: string | null;
}

interface TreeResponse {
  folders: FolderNode[];
  playlists: PlaylistLeaf[];
  error: string | null;
}

interface RenameResult {
  old_name: string | null;
  new_name: string | null;
  ok: boolean;
  error: string | null;
}

interface FolderMutationResult {
  folder?: FolderNode;
  renames: RenameResult[];
}

interface MoveResult {
  ok: boolean;
  new_name: string | null;
  error: string | null;
}

type DragPayload = { type: "playlist" | "folder"; id: string };

type Modal =
  | { kind: "none" }
  | { kind: "create-folder"; parentId: string | null }
  | { kind: "rename-folder"; folder: FolderNode }
  | { kind: "move-folder"; folder: FolderNode }
  | { kind: "move-playlist"; playlist: PlaylistLeaf };

const API = "/api/playlist-folders";

function renameFailures(result: FolderMutationResult | undefined) {
  return (result?.renames ?? [])
    .filter((r) => !r.ok)
    .map((r) => `Couldn't rename "${r.old_name}": ${r.error}`);
}

export default function PlaylistFoldersPage() {
  const { error, run } = useApiError();
  const toast = useToast();

  const [tree, setTree] = useState<TreeResponse | null>(null);
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [menuFor, setMenuFor] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState<string | null>(null);
  const [modal, setModal] = useState<Modal>({ kind: "none" });

  const loadTree = () => run(() => api.get<TreeResponse>(`${API}/tree`)).then((r) => r && setTree(r));

  useEffect(() => {
    loadTree();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const folders = tree?.folders ?? [];
  const playlists = tree?.playlists ?? [];

  const foldersById = useMemo(() => new Map(folders.map((f) => [f.id, f])), [folders]);
  const playlistsById = useMemo(() => new Map(playlists.map((p) => [p.id, p])), [playlists]);

  const childFolders = useMemo(() => {
    const m = new Map<string | null, FolderNode[]>();
    for (const f of folders) {
      const arr = m.get(f.parent_id) ?? [];
      arr.push(f);
      m.set(f.parent_id, arr);
    }
    for (const arr of m.values()) arr.sort((a, b) => a.name.localeCompare(b.name));
    return m;
  }, [folders]);

  const childPlaylists = useMemo(() => {
    const m = new Map<string | null, PlaylistLeaf[]>();
    for (const p of playlists) {
      const arr = m.get(p.folder_id) ?? [];
      arr.push(p);
      m.set(p.folder_id, arr);
    }
    for (const arr of m.values()) arr.sort((a, b) => a.leaf_name.localeCompare(b.leaf_name));
    return m;
  }, [playlists]);

  const flatFolders = useMemo(() => {
    const out: { folder: FolderNode; depth: number }[] = [];
    const walk = (parentId: string | null, depth: number) => {
      for (const f of childFolders.get(parentId) ?? []) {
        out.push({ folder: f, depth });
        walk(f.id, depth + 1);
      }
    };
    walk(null, 0);
    return out;
  }, [childFolders]);

  const descendantIds = (id: string) => {
    const out = new Set<string>();
    const walk = (pid: string) => {
      for (const f of childFolders.get(pid) ?? []) {
        out.add(f.id);
        walk(f.id);
      }
    };
    walk(id);
    return out;
  };

  // --- Mutations --------------------------------------------------------

  const createFolder = async (name: string, parentId: string | null) => {
    const res = await run(() => api.post<FolderNode>(`${API}/folders`, { name, parent_id: parentId }));
    if (!res) return;
    toast.show({ tone: "good", message: `Created folder "${name}".` });
    setModal({ kind: "none" });
    loadTree();
  };

  const renameFolder = async (folder: FolderNode, name: string) => {
    const res = await run(() => api.put<FolderMutationResult>(`${API}/folders/${folder.id}`, { name }));
    if (!res) return;
    toast.show({ tone: "good", message: `Renamed to "${name}".`, detail: renameFailures(res) });
    setModal({ kind: "none" });
    loadTree();
  };

  const moveFolderTo = async (folder: FolderNode, parentId: string | null) => {
    const prevParentId = folder.parent_id;
    const res = await run(() => api.put<FolderMutationResult>(`${API}/folders/${folder.id}`, { parent_id: parentId }));
    if (!res) return;
    toast.show({
      tone: "good",
      message: `Moved "${folder.name}" to ${parentId ? foldersById.get(parentId)?.name ?? "folder" : "Root"}.`,
      detail: renameFailures(res),
      action: { label: "Undo", onClick: () => void moveFolderTo(folder, prevParentId) },
    });
    setModal({ kind: "none" });
    loadTree();
  };

  const deleteFolder = async (folder: FolderNode) => {
    if (!window.confirm(`Delete folder "${folder.name}"? Its playlists and subfolders move up a level.`)) return;
    const res = await run(() => api.post<FolderMutationResult>(`${API}/folders/${folder.id}/delete`));
    if (!res) return;
    toast.show({ tone: "good", message: `Deleted "${folder.name}".`, detail: renameFailures(res) });
    loadTree();
  };

  const movePlaylistTo = async (playlist: PlaylistLeaf, folderId: string | null) => {
    const prevFolderId = playlist.folder_id;
    const res = await run(() => api.post<MoveResult>(`${API}/move-playlist`, { playlist_id: playlist.id, folder_id: folderId }));
    if (!res) return;
    if (!res.ok) {
      toast.show({ tone: "bad", message: res.error ?? "Couldn't move that playlist." });
      return;
    }
    toast.show({
      tone: "good",
      message: `Moved "${playlist.leaf_name}" to ${folderId ? foldersById.get(folderId)?.name ?? "folder" : "Root"}.`,
      action: { label: "Undo", onClick: () => void movePlaylistTo(playlist, prevFolderId) },
    });
    setModal({ kind: "none" });
    loadTree();
  };

  const resync = async () => {
    if (!window.confirm("Rebuild the folder tree from current Navidrome playlist names? Folders you created here that don't match a playlist name will be replaced.")) return;
    const res = await run(() => api.post<TreeResponse>(`${API}/resync`));
    if (!res) return;
    setTree(res);
    toast.show({ tone: "good", message: "Resynced from Navidrome." });
  };

  // --- Drag and drop ------------------------------------------------------

  const startDrag = (e: DragEvent, payload: DragPayload) => {
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("application/json", JSON.stringify(payload));
  };

  const dragOverTarget = (e: DragEvent, key: string) => {
    e.preventDefault();
    e.stopPropagation();
    e.dataTransfer.dropEffect = "move";
    if (dragOver !== key) setDragOver(key);
  };

  const dropOnFolder = (e: DragEvent, folderId: string | null) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(null);
    const raw = e.dataTransfer.getData("application/json");
    if (!raw) return;
    const payload = JSON.parse(raw) as DragPayload;
    if (payload.type === "playlist") {
      const playlist = playlistsById.get(payload.id);
      if (!playlist || playlist.folder_id === folderId) return;
      movePlaylistTo(playlist, folderId);
    } else {
      if (payload.id === folderId) return;
      const folder = foldersById.get(payload.id);
      if (!folder || folder.parent_id === folderId) return;
      if (folderId !== null && descendantIds(payload.id).has(folderId)) {
        toast.show({ tone: "bad", message: "Can't move a folder into one of its own subfolders." });
        return;
      }
      moveFolderTo(folder, folderId);
    }
  };

  // --- Rendering -----------------------------------------------------------

  const toggle = (id: string) => {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const renderLevel = (parentId: string | null, depth: number): ReactNode => (
    <>
      {(childFolders.get(parentId) ?? []).map((f) => (
        <div key={f.id}>
          <div
            className={`tree-row${dragOver === f.id ? " drag-over" : ""}`}
            style={{ paddingLeft: depth * 20 }}
            draggable
            onDragStart={(e) => startDrag(e, { type: "folder", id: f.id })}
            onDragOver={(e) => dragOverTarget(e, f.id)}
            onDragLeave={() => setDragOver((cur) => (cur === f.id ? null : cur))}
            onDrop={(e) => dropOnFolder(e, f.id)}
          >
            <button className="tree-chevron" onClick={() => toggle(f.id)} aria-label={collapsed.has(f.id) ? "Expand" : "Collapse"}>
              {collapsed.has(f.id) ? "▸" : "▾"}
            </button>
            <span className="tree-icon">📁</span>
            <span className="tree-name">{f.name}</span>
            <RowMenu
              open={menuFor === f.id}
              onToggle={() => setMenuFor((cur) => (cur === f.id ? null : f.id))}
              onClose={() => setMenuFor(null)}
            >
              <button onClick={() => { setModal({ kind: "rename-folder", folder: f }); setMenuFor(null); }}>Rename</button>
              <button onClick={() => { setModal({ kind: "create-folder", parentId: f.id }); setMenuFor(null); }}>Create subfolder</button>
              <button onClick={() => { setModal({ kind: "move-folder", folder: f }); setMenuFor(null); }}>Move to folder…</button>
              <button onClick={() => { setMenuFor(null); deleteFolder(f); }}>Delete</button>
            </RowMenu>
          </div>
          {!collapsed.has(f.id) && renderLevel(f.id, depth + 1)}
        </div>
      ))}
      {(childPlaylists.get(parentId) ?? []).map((p) => (
        <div
          key={p.id}
          className="tree-row"
          style={{ paddingLeft: depth * 20 + 20 }}
          draggable
          onDragStart={(e) => startDrag(e, { type: "playlist", id: p.id })}
        >
          <span className="tree-icon">🎵</span>
          <span className="tree-name">{p.leaf_name}</span>
          <RowMenu
            open={menuFor === p.id}
            onToggle={() => setMenuFor((cur) => (cur === p.id ? null : p.id))}
            onClose={() => setMenuFor(null)}
          >
            <button onClick={() => { setModal({ kind: "move-playlist", playlist: p }); setMenuFor(null); }}>Move to folder…</button>
          </RowMenu>
        </div>
      ))}
    </>
  );

  return (
    <div>
      <h2>Playlist folders</h2>
      <p className="muted">
        Drag playlists and folders to reorganize. Moves rename the playlist in Navidrome right away
        (<code>Folder/Subfolder/Name</code>), the same way it's exposed to clients like Feishin.
      </p>
      <ErrorBanner message={error} />

      <div className="panel">
        <div className="row">
          <button className="primary" onClick={() => setModal({ kind: "create-folder", parentId: null })}>
            + Create folder
          </button>
          <button onClick={resync}>Resync from Navidrome</button>
        </div>

        {!tree && <p className="muted">Loading…</p>}

        {tree && (
          <div className="tree">
            <div
              className={`tree-row tree-root${dragOver === "__root__" ? " drag-over" : ""}`}
              onDragOver={(e) => dragOverTarget(e, "__root__")}
              onDragLeave={() => setDragOver((cur) => (cur === "__root__" ? null : cur))}
              onDrop={(e) => dropOnFolder(e, null)}
            >
              <span className="tree-icon">🏠</span>
              <span className="tree-name muted">Root (drop here to un-file)</span>
            </div>
            {renderLevel(null, 0)}
          </div>
        )}
      </div>

      {(modal.kind === "create-folder" || modal.kind === "rename-folder") && (
        <NameDrawer
          title={modal.kind === "create-folder" ? "Create folder" : "Rename folder"}
          initialValue={modal.kind === "rename-folder" ? modal.folder.name : ""}
          onCancel={() => setModal({ kind: "none" })}
          onSave={(name) =>
            modal.kind === "create-folder" ? createFolder(name, modal.parentId) : renameFolder(modal.folder, name)
          }
        />
      )}

      {(modal.kind === "move-folder" || modal.kind === "move-playlist") && (
        <FolderPicker
          flatFolders={
            modal.kind === "move-folder"
              ? flatFolders.filter(
                  ({ folder }) => folder.id !== modal.folder.id && !descendantIds(modal.folder.id).has(folder.id)
                )
              : flatFolders
          }
          onCancel={() => setModal({ kind: "none" })}
          onPick={(folderId) =>
            modal.kind === "move-folder" ? moveFolderTo(modal.folder, folderId) : movePlaylistTo(modal.playlist, folderId)
          }
        />
      )}

      <div className="dock">
        <ToastView toast={toast.toast} onDismiss={toast.dismiss} />
      </div>
    </div>
  );
}

function RowMenu({ open, onToggle, onClose, children }: { open: boolean; onToggle: () => void; onClose: () => void; children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDocClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("mousedown", onDocClick);
    window.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      window.removeEventListener("keydown", onKey);
    };
  }, [open, onClose]);

  return (
    <div className="tree-menu-wrap" ref={ref}>
      <button className="tree-menu-trigger" onClick={onToggle} aria-label="More actions">
        ⋮
      </button>
      {open && <div className="tree-menu">{children}</div>}
    </div>
  );
}

function NameDrawer({ title, initialValue, onCancel, onSave }: { title: string; initialValue: string; onCancel: () => void; onSave: (name: string) => void }) {
  const [value, setValue] = useState(initialValue);
  return (
    <Drawer open onClose={onCancel}>
      <h3 style={{ marginTop: 0 }}>{title}</h3>
      <div className="row">
        <input type="text" autoFocus value={value} onChange={(e) => setValue(e.target.value)} placeholder="Folder name" />
      </div>
      <div className="row">
        <button className="primary" disabled={!value.trim()} onClick={() => onSave(value.trim())}>
          Save
        </button>
        <button onClick={onCancel}>Cancel</button>
      </div>
    </Drawer>
  );
}

function FolderPicker({ flatFolders, onCancel, onPick }: { flatFolders: { folder: FolderNode; depth: number }[]; onCancel: () => void; onPick: (folderId: string | null) => void }) {
  return (
    <Drawer open onClose={onCancel}>
      <h3 style={{ marginTop: 0 }}>Move to folder</h3>
      <div className="folder-picker">
        <button className="folder-picker-item" onClick={() => onPick(null)}>
          🏠 Root
        </button>
        {flatFolders.map(({ folder, depth }) => (
          <button key={folder.id} className="folder-picker-item" style={{ paddingLeft: 14 + depth * 16 }} onClick={() => onPick(folder.id)}>
            📁 {folder.name}
          </button>
        ))}
      </div>
      <div className="row" style={{ marginTop: 10 }}>
        <button onClick={onCancel}>Cancel</button>
      </div>
    </Drawer>
  );
}
