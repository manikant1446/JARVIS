import os
import shutil
import platform
import zipfile
import subprocess
from pathlib import Path
from datetime import datetime

try:
    import send2trash
    _SEND2TRASH = True
except ImportError:
    _SEND2TRASH = False

try:
    import pypdf
    _HAS_PYPDF = True
except ImportError:
    _HAS_PYPDF = False

from core.undo import push_undo
from core.permissions import PermissionLevel, execute_with_permission
from core.verification import verify_file_exists, verify_file_moved

_OS = platform.system()  # "Windows" | "Darwin" | "Linux"

_UNDO_CONTENT_LIMIT = 1_000_000


def _undo_move(src: Path, dst: Path):
    """Reverse of a move: put it back where it came from."""
    def _fn():
        if not dst.exists():
            return f"'{dst.name}' is no longer there — nothing moved back."
        src.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(dst), str(src))
        return f"'{src.name}' is back in {src.parent.name}/."
    return _fn


def _undo_create(target: Path):
    """Reverse of a create: remove what we made."""
    def _fn():
        if not target.exists():
            return f"'{target.name}' is already gone."
        if target.is_dir():
            if any(target.iterdir()):
                return f"'{target.name}' is not empty any more — leaving it alone."
            target.rmdir()
        else:
            target.unlink()
        return f"Removed '{target.name}'."
    return _fn


def _undo_write(target: Path, previous: str | None):
    """Reverse of a write: restore old contents or remove created file."""
    def _fn():
        if previous is None:
            if target.exists():
                target.unlink()
                return f"Removed '{target.name}' — it did not exist before."
            return f"'{target.name}' is already gone."
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(previous, encoding="utf-8")
        return f"Restored the previous contents of '{target.name}'."
    return _fn


def _restore_from_trash(original: Path) -> str:
    """Best-effort undelete."""
    return f"'{original.name}' was moved to Trash and can be restored from the Trash folder."


_SAFE_ROOTS: list[Path] = [
    Path.home(),
]


def _is_safe_path(target: Path) -> bool:
    try:
        resolved = target.resolve()
        return any(
            resolved == root.resolve() or resolved.is_relative_to(root.resolve())
            for root in _SAFE_ROOTS
        )
    except Exception:
        return False


def _get_desktop() -> Path:
    return Path.home() / "Desktop"


def _get_downloads() -> Path:
    return Path.home() / "Downloads"


def _get_documents() -> Path:
    return Path.home() / "Documents"


def _get_pictures() -> Path:
    return Path.home() / "Pictures"


def _get_music() -> Path:
    return Path.home() / "Music"


def _get_videos() -> Path:
    return Path.home() / "Videos"


def _resolve_path(raw: str) -> Path:
    shortcuts: dict[str, Path] = {
        "desktop":   _get_desktop(),
        "downloads": _get_downloads(),
        "documents": _get_documents(),
        "pictures":  _get_pictures(),
        "music":     _get_music(),
        "videos":    _get_videos(),
        "home":      Path.home(),
    }
    lower = raw.strip().lower()
    if lower in shortcuts:
        return shortcuts[lower]
    return Path(raw).expanduser()


def _format_size(b: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} TB"


def _safe_trash(target: Path) -> str:
    if not _SEND2TRASH:
        return "send2trash is not available. Permanent deletion is disabled for safety."
    send2trash.send2trash(str(target))
    return f"Moved to Trash: {target.name}"


def list_files(path: str = "desktop", show_hidden: bool = False) -> str:
    try:
        target = _resolve_path(path)
        if not _is_safe_path(target):
            return f"Access denied: {target}"
        if not target.exists():
            return f"Path not found: {target}"
        if not target.is_dir():
            return f"Not a directory: {target}"

        items = []
        for item in sorted(target.iterdir()):
            if not show_hidden and item.name.startswith("."):
                continue
            if item.is_dir():
                items.append(f"📁 {item.name}/")
            else:
                size = _format_size(item.stat().st_size)
                items.append(f"📄 {item.name} ({size})")

        if not items:
            return f"Directory is empty: {target.name}/"

        return f"Contents of {target.name}/ ({len(items)} items):\n" + "\n".join(items)
    except PermissionError:
        return f"Permission denied: {path}"
    except Exception as e:
        return f"Error listing files: {e}"


def create_file(path: str, name: str = "", content: str = "") -> str:
    try:
        base   = _resolve_path(path)
        target = (base / name) if name else base
        if not _is_safe_path(target):
            return f"Access denied: {target}"
        target.parent.mkdir(parents=True, exist_ok=True)
        existed = target.exists()
        previous = None
        if existed:
            try:
                previous = target.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                previous = None
        target.write_text(content, encoding="utf-8")

        # Verification
        v_ok, v_msg = verify_file_exists(target)
        if not v_ok:
            return f"Error: {v_msg}"

        push_undo(f"created {target.name}",
                  _undo_write(target, previous) if existed else _undo_create(target))
        return f"File created: {target.name}"
    except Exception as e:
        return f"Could not create file: {e}"


def create_folder(path: str, name: str = "") -> str:
    try:
        base   = _resolve_path(path)
        target = (base / name) if name else base
        if not _is_safe_path(target):
            return f"Access denied: {target}"
        already = target.exists()
        target.mkdir(parents=True, exist_ok=True)
        if not already:
            push_undo(f"created folder {target.name}", _undo_create(target))
        return f"Folder created: {target.name}"
    except Exception as e:
        return f"Could not create folder: {e}"


def open_file(path: str, name: str = "") -> str:
    """Opens a file using macOS default application."""
    try:
        base = _resolve_path(path)
        target = (base / name) if name else base
        if not target.exists():
            return f"File not found: {target.name}"
        if _OS == "Darwin":
            subprocess.run(["open", str(target)])
            return f"Opened: {target.name}"
        return f"File exists at {target}."
    except Exception as e:
        return f"Could not open file: {e}"


def delete_file(path: str, name: str = "") -> str:
    """Deletes a file or directory by moving it to Trash. Requires Level 3 confirmation."""
    base   = _resolve_path(path)
    target = (base / name) if name else base
    if not _is_safe_path(target):
        return f"Access denied: {target}"
    if not target.exists():
        return f"Not found: {target.name}"

    protected = {
        _get_desktop(), _get_downloads(), _get_documents(),
        _get_pictures(), _get_music(), _get_videos(), Path.home()
    }
    if target.resolve() in {p.resolve() for p in protected}:
        return f"Protected system directory, cannot delete: {target.name}"

    def _do_delete():
        original = target.resolve()
        res = _safe_trash(target)
        if res.startswith("Moved to Trash"):
            push_undo(f"deleted {original.name}", lambda p=original: _restore_from_trash(p))
        return res

    return execute_with_permission(
        level=PermissionLevel.LEVEL_3_DESTRUCTIVE,
        title=f"Delete '{target.name}'",
        detail=f"Move '{target.name}' to Trash ({str(target.resolve())})",
        action_fn=_do_delete
    )


def move_file(path: str, name: str = "", destination: str = "") -> str:
    try:
        base   = _resolve_path(path)
        src    = (base / name) if name else base
        dst    = _resolve_path(destination) if destination else None

        if not src.exists():
            return f"Source not found: {src.name}"
        if dst is None:
            return "No destination specified."
        if not _is_safe_path(src):
            return f"Access denied (source): {src}"
        if not _is_safe_path(dst):
            return f"Access denied (destination): {dst}"

        if dst.is_dir():
            dst = dst / src.name

        dst.parent.mkdir(parents=True, exist_ok=True)
        origin = src.resolve()
        dest = dst.resolve()
        shutil.move(str(src), str(dst))

        # Verification
        v_ok, v_msg = verify_file_moved(origin, dest)
        if not v_ok:
            return f"Warning: {v_msg}"

        push_undo(f"moved {origin.name} to {dst.parent.name}/",
                  _undo_move(origin, dest))
        return f"Moved: {src.name} → {dst.parent.name}/"
    except Exception as e:
        return f"Could not move: {e}"


def copy_file(path: str, name: str = "", destination: str = "") -> str:
    try:
        base = _resolve_path(path)
        src  = (base / name) if name else base
        dst  = _resolve_path(destination) if destination else None

        if not src.exists():
            return f"Source not found: {src.name}"
        if dst is None:
            return "No destination specified."
        if not _is_safe_path(src):
            return f"Access denied (source): {src}"
        if not _is_safe_path(dst):
            return f"Access denied (destination): {dst}"

        if dst.is_dir():
            dst = dst / src.name

        dst.parent.mkdir(parents=True, exist_ok=True)

        if src.is_dir():
            shutil.copytree(str(src), str(dst))
        else:
            shutil.copy2(str(src), str(dst))

        _copy = dst.resolve()
        def _undo_copy():
            if not _copy.exists():
                return f"The copy '{_copy.name}' is already gone."
            if _copy.is_dir():
                shutil.rmtree(_copy)
            else:
                _copy.unlink()
            return f"Removed the copy in {_copy.parent.name}/."
        push_undo(f"copied {src.name} to {dst.parent.name}/", _undo_copy)

        return f"Copied: {src.name} → {dst.parent.name}/"
    except Exception as e:
        return f"Could not copy: {e}"


def rename_file(path: str, name: str = "", new_name: str = "") -> str:
    try:
        base     = _resolve_path(path)
        target   = (base / name) if name else base
        if not _is_safe_path(target):
            return f"Access denied: {target}"
        if not target.exists():
            return f"Not found: {target.name}"
        if not new_name:
            return "No new name provided."

        new_path = target.parent / new_name
        if new_path.exists():
            return f"A file named '{new_name}' already exists here."

        old_path = target.resolve()
        target.rename(new_path)
        push_undo(f"renamed {old_path.name} to {new_name}",
                  _undo_move(old_path, new_path.resolve()))
        return f"Renamed: {target.name} → {new_name}"
    except Exception as e:
        return f"Could not rename: {e}"


def read_file(path: str, name: str = "", max_chars: int = 4000) -> str:
    try:
        base   = _resolve_path(path)
        target = (base / name) if name else base
        if not _is_safe_path(target):
            return f"Access denied: {target}"
        if not target.exists():
            return f"File not found: {target.name}"
        if not target.is_file():
            return f"Not a file: {target.name}"

        # If PDF
        if target.suffix.lower() == ".pdf":
            return extract_pdf_text(str(target.parent), name=target.name)

        content = target.read_text(encoding="utf-8", errors="ignore")
        if len(content) > max_chars:
            content = content[:max_chars] + f"\n\n[Truncated — {len(content)} total chars]"
        return content
    except Exception as e:
        return f"Could not read file: {e}"


def write_file(path: str, name: str = "", content: str = "", append: bool = False) -> str:
    try:
        base   = _resolve_path(path)
        target = (base / name) if name else base
        if not _is_safe_path(target):
            return f"Access denied: {target}"
        target.parent.mkdir(parents=True, exist_ok=True)

        previous: str | None = None
        undoable = True
        if target.exists():
            try:
                if target.stat().st_size > _UNDO_CONTENT_LIMIT:
                    undoable = False
                else:
                    previous = target.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                undoable = False

        mode = "a" if append else "w"
        with open(target, mode, encoding="utf-8") as f:
            f.write(content)

        action = "Appended to" if append else "Written to"
        if undoable:
            push_undo(f"wrote to {target.name}", _undo_write(target, previous))
            return f"{action}: {target.name}"
        return f"{action}: {target.name}."
    except Exception as e:
        return f"Could not write file: {e}"


def find_files(name: str = "", extension: str = "", path: str = "home", max_results: int = 20) -> str:
    try:
        search_path = _resolve_path(path)
        if not _is_safe_path(search_path):
            return f"Access denied: {search_path}"
        if not search_path.exists():
            return f"Search path not found: {path}"

        results = []
        dir_count = 0
        max_dirs = 500

        for item in search_path.rglob("*"):
            if item.is_dir():
                dir_count += 1
                if dir_count > max_dirs:
                    break
                continue
            if not item.is_file():
                continue
            if extension and item.suffix.lower() != extension.lower():
                continue
            if name and name.lower() not in item.name.lower():
                continue
            size = _format_size(item.stat().st_size)
            results.append(f"📄 {item.name} ({size}) — {item.parent}")
            if len(results) >= max_results:
                break

        if not results:
            query = name or extension or "files"
            return f"No {query} found in {search_path.name}/"

        return f"Found {len(results)} file(s):\n" + "\n".join(results)
    except Exception as e:
        return f"Search error: {e}"


def find_folders(name: str = "", path: str = "home", max_results: int = 15) -> str:
    """Searches for directories matching a name."""
    try:
        search_path = _resolve_path(path)
        if not search_path.exists():
            return f"Search path not found: {path}"

        results = []
        for item in search_path.rglob("*"):
            if item.is_dir() and (not name or name.lower() in item.name.lower()):
                results.append(f"📁 {item.name}/ — {item.parent}")
                if len(results) >= max_results:
                    break

        if not results:
            return f"No folders matching '{name}' found."
        return f"Found {len(results)} folder(s):\n" + "\n".join(results)
    except Exception as e:
        return f"Folder search error: {e}"


def compress_files(path: str, name: str = "", destination: str = "") -> str:
    """Compresses a file or folder into a .zip archive."""
    try:
        base = _resolve_path(path)
        src = (base / name) if name else base
        if not src.exists():
            return f"Source not found: {src}"

        dst_dir = _resolve_path(destination) if destination else src.parent
        zip_path = dst_dir / f"{src.stem}.zip"

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            if src.is_file():
                zf.write(src, arcname=src.name)
            else:
                for root, _, files in os.walk(src):
                    for f in files:
                        full_p = Path(root) / f
                        arcname = full_p.relative_to(src.parent)
                        zf.write(full_p, arcname=str(arcname))

        return f"📦 Compressed '{src.name}' into '{zip_path.name}' ({_format_size(zip_path.stat().st_size)})."
    except Exception as e:
        return f"Compression failed: {e}"


def extract_archive(path: str, name: str = "", destination: str = "") -> str:
    """Extracts a .zip or archive into a destination directory."""
    try:
        base = _resolve_path(path)
        src = (base / name) if name else base
        if not src.exists():
            return f"Archive not found: {src}"

        dst = _resolve_path(destination) if destination else src.parent / src.stem
        dst.mkdir(parents=True, exist_ok=True)
        shutil.unpack_archive(str(src), str(dst))
        return f"📂 Extracted '{src.name}' into '{dst.name}/'."
    except Exception as e:
        return f"Extraction failed: {e}"


def extract_pdf_text(path: str, name: str = "", max_pages: int = 10) -> str:
    """Extracts readable text from a PDF file."""
    base = _resolve_path(path)
    target = (base / name) if name else base
    if not target.exists() or not target.is_file():
        return f"PDF not found: {target.name}"

    try:
        import pypdf
        reader = pypdf.PdfReader(str(target))
        total_pages = len(reader.pages)
        pages_to_read = min(total_pages, max_pages)
        texts = []
        for i in range(pages_to_read):
            t = reader.pages[i].extract_text()
            if t:
                texts.append(f"[Page {i+1}]\n{t.strip()}")
        if not texts:
            return f"No readable text extracted from '{target.name}'."
        out = f"📄 PDF '{target.name}' ({total_pages} total pages, extracted first {pages_to_read}):\n\n" + "\n\n".join(texts)
        if len(out) > 4000:
            out = out[:4000] + f"\n\n[Truncated — full length {len(out)} chars]"
        return out
    except Exception as e:
        return f"Could not extract PDF text from '{target.name}': {e}"


def organize_directory(path: str = "downloads") -> str:
    """Organizes any directory (desktop, downloads, etc.) into categorized subfolders."""
    type_map = {
        "Images":    {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico", ".heic"},
        "Documents": {".pdf", ".doc", ".docx", ".txt", ".xls", ".xlsx",
                      ".ppt", ".pptx", ".csv", ".odt", ".ods", ".odp"},
        "Videos":    {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v"},
        "Music":     {".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"},
        "Archives":  {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"},
        "Code":      {".py", ".js", ".ts", ".html", ".css", ".json", ".xml",
                      ".cpp", ".java", ".cs", ".go", ".rs", ".sh"},
    }

    target_dir = _resolve_path(path)
    if not target_dir.exists() or not target_dir.is_dir():
        return f"Directory '{path}' not found."

    moved, skipped = [], []
    journal: list[tuple[Path, Path]] = []

    try:
        for item in target_dir.iterdir():
            if item.is_dir() or item.name.startswith("."):
                continue
            if item.name in {k for k in type_map}:
                continue

            ext = item.suffix.lower()
            subfolder = target_dir / "Others"
            for folder, exts in type_map.items():
                if ext in exts:
                    subfolder = target_dir / folder
                    break

            subfolder.mkdir(exist_ok=True)
            new_path = subfolder / item.name

            if new_path.exists():
                skipped.append(item.name)
                continue

            origin = item.resolve()
            shutil.move(str(item), str(new_path))
            journal.append((origin, new_path.resolve()))
            moved.append(f"{item.name} → {subfolder.name}/")

        if journal:
            def _undo_organize(entries=tuple(journal)):
                restored = 0
                for origin, moved_to in entries:
                    try:
                        if moved_to.exists():
                            origin.parent.mkdir(parents=True, exist_ok=True)
                            shutil.move(str(moved_to), str(origin))
                            restored += 1
                    except Exception as e:
                        pass
                return f"{restored} file(s) restored."
            push_undo(f"organized {target_dir.name} ({len(journal)} files)", _undo_organize)

        result = f"Organized {target_dir.name}/: {len(moved)} files organized."
        if moved:
            preview = moved[:8]
            result += "\n" + "\n".join(preview)
            if len(moved) > 8:
                result += f"\n... and {len(moved) - 8} more."
        return result
    except Exception as e:
        return f"Could not organize directory: {e}"


def get_file_info(path: str, name: str = "") -> str:
    try:
        base   = _resolve_path(path)
        target = (base / name) if name else base
        if not _is_safe_path(target):
            return f"Access denied: {target}"
        if not target.exists():
            return f"Not found: {target.name}"

        stat = target.stat()
        info = {
            "Name":      target.name,
            "Type":      "Folder" if target.is_dir() else "File",
            "Size":      _format_size(stat.st_size),
            "Location":  str(target.parent),
            "Created":   datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M"),
            "Modified":  datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
            "Extension": target.suffix or "—",
        }
        return "\n".join(f"  {k}: {v}" for k, v in info.items())
    except Exception as e:
        return f"Could not get file info: {e}"


def file_controller(
    parameters: dict = None,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    params = parameters or {}
    action = params.get("action", "").lower().strip()
    path   = params.get("path", "desktop")
    name   = params.get("name", "")

    if player:
        player.write_log(f"[file] {action} {name or path}")

    try:
        if action == "list":
            return list_files(path)
        elif action == "create_file":
            return create_file(path, name=name, content=params.get("content", ""))
        elif action == "create_folder":
            return create_folder(path, name=name)
        elif action == "open":
            return open_file(path, name=name)
        elif action == "delete":
            return delete_file(path, name=name)
        elif action == "move":
            return move_file(path, name=name, destination=params.get("destination", ""))
        elif action == "copy":
            return copy_file(path, name=name, destination=params.get("destination", ""))
        elif action == "rename":
            return rename_file(path, name=name, new_name=params.get("new_name", ""))
        elif action == "read":
            return read_file(path, name=name)
        elif action == "write":
            return write_file(
                path, name=name,
                content=params.get("content", ""),
                append=params.get("append", False)
            )
        elif action == "find":
            return find_files(
                name=name or params.get("name", ""),
                extension=params.get("extension", ""),
                path=path,
                max_results=min(int(params.get("max_results", 20)), 50),
            )
        elif action == "find_folders":
            return find_folders(name=name or params.get("name", ""), path=path)
        elif action == "compress":
            return compress_files(path, name=name, destination=params.get("destination", ""))
        elif action == "extract":
            return extract_archive(path, name=name, destination=params.get("destination", ""))
        elif action == "pdf_text":
            return extract_pdf_text(path, name=name)
        elif action == "organize":
            return organize_directory(path=path)
        elif action == "organize_desktop":
            return organize_directory(path="desktop")
        elif action == "info":
            return get_file_info(path, name=name)
        else:
            return f"Unknown action: '{action}'"
    except Exception as e:
        return f"File controller error ({action}): {e}"


# ── Tool declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "file_controller",
    "description": "Smart File Agent: search, open, create, delete (confirmed), move, copy, rename, read, write, compress, extract, PDF extraction, organize.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "list | create_file | create_folder | open | delete | move | copy | rename | read | write | find | find_folders | compress | extract | pdf_text | organize | info"
            },
            "path": {
                "type": "STRING",
                "description": "File/folder path or shortcut: desktop, downloads, documents, home"
            },
            "destination": {
                "type": "STRING",
                "description": "Destination path for move/copy/compress/extract"
            },
            "new_name": {
                "type": "STRING",
                "description": "New name for rename"
            },
            "content": {
                "type": "STRING",
                "description": "Content for create_file/write"
            },
            "name": {
                "type": "STRING",
                "description": "File or folder name"
            },
            "extension": {
                "type": "STRING",
                "description": "File extension to filter (e.g. .pdf)"
            }
        },
        "required": [
            "action"
        ]
    },
    "handler": file_controller,
}
