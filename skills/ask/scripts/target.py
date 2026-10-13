"""Disposable target of an exercise: create a copy, remove only what was created.

Plan `.scratch/exercise-skills/plan.md` claim C1 (invariants I1, I2 copy part, I3, I13). Windows only:
every operation refuses on another platform, and no environment variable skips or substitutes a check
(the OneDrive variables are read only as one more source of sync roots to refuse).

CLI (wired into consult.py, JSON on stdout like the other actions):

    consult.py target-create <request.json> [--base <scratch base>]
    consult.py target-remove <run directory>

Create request (unknown keys are refused):

    {"project": "<absolute project directory>",
     "target_root": {"path": "<absolute directory>", "confirmed_by_user": true},
     "target_name": "<optional single name; default ask-codex-target-<random>>",
     "env_files": ["<relative path inside the project the user named>", ...],
     "exclude_names": ["<extra name never copied>", ...],
     "limits": {"max_entries": <int>, "max_bytes": <int>}}

All checks run before anything is written. Then target-create makes a run directory
`<base>/ask-codex/run.*` (the ownership convention of consult.py's plan_at) and writes the record
there, never in the project. The base is resolved to its final path (the base itself may be a link;
what counts is where it resolves), and a resolved base inside the project is refused before any
directory is created. `ask-codex` and `run.*` are opened or exclusively created relative to the base
handle and must not be links or junctions; the final path of the base and of the new run directory is
checked against the project (on a volume that reports no final path, such as a RAM disk, the volume
serial must differ from the project's), and a refused new run directory is deleted at once. Fail
closed: the project, the base and every run directory must be in local drive form (`X:\\...` and a
final path `\\\\?\\X:\\...`); UNC (including an admin share such as `\\\\localhost\\D$`), volume-GUID
and device paths are refused, because they cannot be compared with the project's path. In-process
callers (the exercise lifecycle, C2) call create() with their own run-directory factory
make_run_directory(project final path) -> (run directory, owns it), e.g. a prepared run directory, and
create_sibling() for a recorded MCP TEMP directory (I5); create() verifies any factory's directory the
same way (it and its parent no link, not inside the project) before writing the record.

remove() takes the run directory only through the ownership check (record_at). A directory that fails
it is reported as the retained location itself: its record is not read, because a record outside the
owned layout is not trusted, and a path taken from it could steer manual cleanup to the wrong place.

Cloud-file placeholders: python.exe runs in placeholder compatibility mode PHCM_DISGUISE_PLACEHOLDER,
under which a placeholder (e.g. OneDrive, tag 0x9000601A) shows no reparse attribute or tag. create(),
create_sibling() and remove() therefore run with PHCM_EXPOSE_PLACEHOLDERS set for the calling thread
(RtlSetThreadPlaceholderCompatibilityMode, restored afterwards; the process-level call only where the
thread call does not exist), so the root, ancestor, copy and removal checks see placeholders as the
reparse points they are. As defence in depth, the copy also skips and lists, without opening it for
reading, any entry with FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS, RECALL_ON_OPEN or OFFLINE.

Record `<run directory>/target.json`, always written by atomic replace, and each entry written before
its directory is created:

    {"version": 1, "directory": "<run directory>", "owns_run_directory": bool,
     "project": "<final path>", "root": {"path": "<final path>", "volume_serial": "..", "file_id": ".."},
     "entries": [{"kind": "target" | "temp", "path": "<root>\\<name>", "state": "pending" | "created",
                  "volume_serial": "..", "file_id": ".."}],
     "copy": "pending" | "done"}

Copy: the project is walked handle-relative (NtCreateFile with a parent directory handle and
FILE_OPEN_REPARSE_POINT), so no path is re-resolved and no reparse point of any tag is followed or
recreated; links and recall-on-access entries are skipped and listed in `skipped_links`. Files are
first opened for attributes only and reopened for reading after these checks. Only the unnamed data stream is read and written, so no
alternate data stream (e.g. a downloaded file's Zone.Identifier) is ever copied; entries that carry
one are copied without it and listed in `streams_not_copied`. The read-only attribute is kept. Never
copied, in any case and at any depth: FIXED_NAMES, the request's extra names, and SECRET_PATTERNS
(files or directories) unless the request names the file. A directory under any name that meets
Git's repository-directory criterion (_git_layout, a superset: a HEAD file with objects and refs
entries of any type, or a HEAD file with commondir; names in any case) is VCS metadata too: nested, it is skipped without opening its contents
and listed in `excluded` and `git_layouts_excluded`; as the project directory itself, the create is
refused before anything is written. Reserved device names and invalid names
(including a name that designates a stream, i.e. holds ':'), paths longer than MAX_PATH_CHARS, the
limits and any copy error fail the create and remove the partial target through the removal routine;
nothing falls back to the working tree. Postcondition: no reparse point, no recall-on-access entry
and no Git repository layout (the target itself included) inside the target.

Removal: paths come only from the record. The root is opened by its recorded path without following
its last component and must match its recorded identity (volume serial + file ID); each entry is
opened relative to that root handle, must be a directory, not a reparse point, and match its recorded
identity. Contents are removed handle-relative, depth first; a reparse point inside is deleted as a
link, never followed. Every deletion is a delete disposition on an open handle
(FILE_DISPOSITION_INFO_EX with DELETE | POSIX_SEMANTICS | IGNORE_READONLY_ATTRIBUTE): attributes are
never changed, so a hard link to a read-only file elsewhere keeps its attributes. A file system
without that class gets the classic disposition, under which a read-only file fails and is reported.
Any mismatch or failure keeps the entry in the record and reports its location.
"""
import contextlib
import ctypes
import fnmatch
import json
import ntpath
import os
from pathlib import Path
import re
import secrets
import struct
import sys
import time

RECORD = "target.json"
VERSION = 1
FIXED_NAMES = frozenset({".git", ".hg", ".svn", ".jj", ".codex", ".claude",
                         "node_modules", ".venv", "venv", "__pycache__", ".pnpm-store"})
SECRET_PATTERNS = (".env*", "*.pem", "*.key", "*.pfx", "*.p12", "id_*", "credentials*")
DEFAULT_LIMITS = {"max_entries": 100_000, "max_bytes": 2 * 1024 ** 3}
MAX_PATH_CHARS = 259  # Win32 MAX_PATH less the terminating NUL; longer target paths fail the copy.
REMOVAL_PATIENCE_S = 10  # bounded wait for transient sharing violations during removal
SYNC_ENV = ("OneDrive", "OneDriveConsumer", "OneDriveCommercial")
SYNC_ROOT_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\SyncRootManager"
RESERVED = frozenset({"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$",
                      *(f"{p}{d}" for p in ("COM", "LPT") for d in "0123456789¹²³")})
TARGET_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$")
PURPOSE = re.compile(r"^[a-z0-9][a-z0-9-]{0,19}$")

# Win32 / NT constants
DELETE, SYNCHRONIZE = 0x10000, 0x100000
LIST_DIRECTORY, READ_DATA, ADD_FILE, WRITE_DATA, ADD_SUBDIRECTORY, TRAVERSE = 0x1, 0x1, 0x2, 0x2, 0x4, 0x20
READ_ATTRIBUTES = 0x80
SHARE_ALL = 0x7
FILE_OPEN, FILE_CREATE = 1, 2
DIRECTORY_FILE, NON_DIRECTORY_FILE, SYNCHRONOUS_IO = 0x1, 0x40, 0x20
OPEN_REPARSE_POINT = 0x200000
OBJ_CASE_INSENSITIVE = 0x40
FLAG_BACKUP_SEMANTICS, FLAG_OPEN_REPARSE_POINT = 0x02000000, 0x00200000
OPEN_EXISTING = 3
ATTR_READONLY, ATTR_DIRECTORY, ATTR_NORMAL, ATTR_REPARSE = 0x1, 0x10, 0x80, 0x400
CLOUD_ATTRIBUTES = 0x1000 | 0x40000 | 0x80000 | 0x100000 | 0x400000  # offline, recall, pinned, unpinned
RECALL_ATTRIBUTES = 0x1000 | 0x40000 | 0x400000  # offline, recall on open, recall on data access
PHCM_EXPOSE_PLACEHOLDERS = 2
DRIVE_FIXED = 3
STATUS_NAME_NOT_FOUND, STATUS_PATH_NOT_FOUND = 0xC0000034, 0xC000003A
STATUS_NAME_COLLISION, STATUS_SHARING_VIOLATION = 0xC0000035, 0xC0000043
ERROR_SHARING_VIOLATION, ERROR_NO_MORE_FILES, ERROR_HANDLE_EOF, ERROR_MORE_DATA = 32, 18, 38, 234
INFO_ATTRIBUTE_TAG, INFO_STREAM, INFO_FULL_DIR, INFO_FULL_DIR_RESTART, INFO_ID = 9, 7, 14, 15, 18
INFO_DISPOSITION, INFO_DISPOSITION_EX = 4, 21
DISPOSITION_FLAGS = 0x1 | 0x2 | 0x10  # DELETE | POSIX_SEMANTICS | IGNORE_READONLY_ATTRIBUTE


class TargetError(ValueError):
    """A refusal or failure reported as JSON; details are merged into the result."""

    def __init__(self, reason, **details):
        super().__init__(reason)
        self.details = details


class CopyFailure(Exception):
    pass


def require_windows():
    if sys.platform != "win32":
        raise TargetError("Exercise operations are supported on Windows only")


def _placeholder_functions():
    """The ntdll placeholder-compatibility calls this Windows has, by name."""
    ntdll, found = ctypes.WinDLL("ntdll"), {}
    for name, restype, argtypes in (
            ("RtlSetThreadPlaceholderCompatibilityMode", ctypes.c_byte, [ctypes.c_byte]),
            ("RtlQueryThreadPlaceholderCompatibilityMode", ctypes.c_byte, []),
            ("RtlSetProcessPlaceholderCompatibilityMode", ctypes.c_byte, [ctypes.c_byte]),
            ("RtlQueryProcessPlaceholderCompatibilityMode", ctypes.c_byte, [])):
        try:
            function = getattr(ntdll, name)
        except AttributeError:
            continue
        function.restype, function.argtypes = restype, argtypes
        found[name] = function
    return found


@contextlib.contextmanager
def _placeholders_exposed():
    """Run the body with cloud-file placeholders exposed as reparse points; restore the mode after."""
    require_windows()
    functions = _placeholder_functions()
    set_thread = functions.get("RtlSetThreadPlaceholderCompatibilityMode")
    set_process = functions.get("RtlSetProcessPlaceholderCompatibilityMode")
    if set_thread is not None:
        previous = set_thread(PHCM_EXPOSE_PLACEHOLDERS)
        if previous < 0:
            raise TargetError("Cloud-file placeholders cannot be exposed on this thread; nothing is done")
        try:
            yield
        finally:
            set_thread(previous)
    elif set_process is not None:
        previous = set_process(PHCM_EXPOSE_PLACEHOLDERS)  # both set calls return the previous mode, < 0 on error
        if previous < 0:
            raise TargetError("Cloud-file placeholders cannot be exposed; nothing is done")
        try:
            yield
        finally:
            set_process(previous)
    else:
        yield  # no placeholder API: this Windows has no cloud-files placeholders to disguise


# --- Windows API (loaded lazily so that importing this module works on every platform) ---

class _UnicodeString(ctypes.Structure):
    _fields_ = [("Length", ctypes.c_ushort), ("MaximumLength", ctypes.c_ushort), ("Buffer", ctypes.c_void_p)]


class _ObjectAttributes(ctypes.Structure):
    _fields_ = [("Length", ctypes.c_uint32), ("RootDirectory", ctypes.c_void_p),
                ("ObjectName", ctypes.POINTER(_UnicodeString)), ("Attributes", ctypes.c_uint32),
                ("SecurityDescriptor", ctypes.c_void_p), ("SecurityQualityOfService", ctypes.c_void_p)]


class _IoStatusBlock(ctypes.Structure):
    _fields_ = [("Status", ctypes.c_void_p), ("Information", ctypes.c_size_t)]


_API = None


def _api():
    global _API
    if _API is None:
        require_windows()
        k = ctypes.WinDLL("kernel32", use_last_error=True)
        n = ctypes.WinDLL("ntdll")
        H, D, P = ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p
        k.CreateFileW.argtypes = [ctypes.c_wchar_p, D, D, P, D, D, H]
        k.CreateFileW.restype = H
        k.CloseHandle.argtypes = [H]
        k.GetFileInformationByHandleEx.argtypes = [H, ctypes.c_int, P, D]
        k.GetFileInformationByHandle.argtypes = [H, P]
        k.SetFileInformationByHandle.argtypes = [H, ctypes.c_int, P, D]
        k.GetFinalPathNameByHandleW.argtypes = [H, ctypes.c_wchar_p, D, D]
        k.GetFinalPathNameByHandleW.restype = D
        k.GetVolumePathNameW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, D]
        k.GetDriveTypeW.argtypes = [ctypes.c_wchar_p]
        k.GetDriveTypeW.restype = ctypes.c_uint
        n.NtCreateFile.argtypes = [ctypes.POINTER(H), D, ctypes.POINTER(_ObjectAttributes),
                                   ctypes.POINTER(_IoStatusBlock), P, D, D, D, D, P, D]
        n.NtCreateFile.restype = ctypes.c_long
        _API = (k, n)
    return _API


class NtError(OSError):
    def __init__(self, status, what):
        self.status = status
        super().__init__(f"{what} failed (NTSTATUS 0x{status:08X})")


def _win_error(what, code=None):
    code = ctypes.get_last_error() if code is None else code
    error = OSError(f"{what} failed (Windows error {code})")
    error.winerror = code
    return error


def _close(handle):
    if handle:
        _api()[0].CloseHandle(handle)


def _nt_open(parent, name, access, options, disposition=FILE_OPEN, attributes=0):
    """Open or create `name` relative to the directory handle `parent` (an empty name reopens it)."""
    raw = name.encode("utf-16-le", "surrogatepass")
    buffer = ctypes.create_string_buffer(raw + b"\0\0")
    text = _UnicodeString(len(raw), len(raw) + 2, ctypes.cast(buffer, ctypes.c_void_p))
    objects = _ObjectAttributes(ctypes.sizeof(_ObjectAttributes), parent, ctypes.pointer(text),
                                OBJ_CASE_INSENSITIVE, None, None)
    handle, status_block = ctypes.c_void_p(), _IoStatusBlock()
    status = _api()[1].NtCreateFile(ctypes.byref(handle), access | SYNCHRONIZE, ctypes.byref(objects),
                                    ctypes.byref(status_block), None, attributes, SHARE_ALL, disposition,
                                    options | SYNCHRONOUS_IO, None, 0) & 0xFFFFFFFF
    if status & 0x80000000:
        raise NtError(status, f"Opening {name!r}")
    return handle.value


def _win_open(path, access, flags):
    handle = _api()[0].CreateFileW(path, access | SYNCHRONIZE, SHARE_ALL, None, OPEN_EXISTING, flags, None)
    if handle in (None, ctypes.c_void_p(-1).value):
        raise _win_error("Opening the directory")
    return handle


def _attribute_tag(handle):
    info = (ctypes.c_uint32 * 2)()
    if not _api()[0].GetFileInformationByHandleEx(handle, INFO_ATTRIBUTE_TAG, info, ctypes.sizeof(info)):
        raise _win_error("Reading attributes")
    return info[0], info[1]


def _identity(handle):
    k = _api()[0]
    info = ctypes.create_string_buffer(24)
    if k.GetFileInformationByHandleEx(handle, INFO_ID, info, 24):
        return {"volume_serial": info.raw[:8][::-1].hex(), "file_id": info.raw[8:24][::-1].hex()}
    info = ctypes.create_string_buffer(52)  # BY_HANDLE_FILE_INFORMATION
    if not k.GetFileInformationByHandle(handle, info):
        raise _win_error("Reading the file identity")
    serial, high, low = struct.unpack_from("<I", info.raw, 28)[0], *struct.unpack_from("<II", info.raw, 44)
    return {"volume_serial": f"{serial:08x}", "file_id": f"{high:08x}{low:08x}"}


def _final_path(handle):
    buffer = ctypes.create_unicode_buffer(32768)
    if not _api()[0].GetFinalPathNameByHandleW(handle, buffer, 32768, 0):
        raise _win_error("Resolving the final path")
    return buffer.value


def _drive_type(path):
    buffer = ctypes.create_unicode_buffer(32768)
    k = _api()[0]
    if not k.GetVolumePathNameW(path, buffer, 32768):
        raise _win_error("Resolving the volume")
    return k.GetDriveTypeW(buffer.value)


def _list(handle):
    """Every entry of an open directory as (name, attributes, reparse tag, size), read in full first."""
    buffer = ctypes.create_string_buffer(65536)
    info_class, entries = INFO_FULL_DIR_RESTART, []
    while True:
        if not _api()[0].GetFileInformationByHandleEx(handle, info_class, buffer, len(buffer)):
            code = ctypes.get_last_error()
            if code == ERROR_NO_MORE_FILES:
                return entries
            raise _win_error("Listing a directory", code)
        info_class, raw, offset = INFO_FULL_DIR, buffer.raw, 0
        while True:
            following = struct.unpack_from("<I", raw, offset)[0]
            size = struct.unpack_from("<q", raw, offset + 40)[0]
            attributes, length, tag = struct.unpack_from("<III", raw, offset + 56)
            name = raw[offset + 68:offset + 68 + length].decode("utf-16-le", "surrogatepass")
            if name not in (".", ".."):
                entries.append((name, attributes, tag if attributes & ATTR_REPARSE else 0, size))
            if not following:
                break
            offset += following


def _has_named_stream(handle):
    size = 4096
    while True:
        buffer = ctypes.create_string_buffer(size)
        if _api()[0].GetFileInformationByHandleEx(handle, INFO_STREAM, buffer, size):
            break
        code = ctypes.get_last_error()
        if code == ERROR_HANDLE_EOF:
            return False  # no stream at all (a directory)
        if code == ERROR_MORE_DATA and size < 1 << 22:
            size *= 4
            continue
        raise _win_error("Reading data streams", code)
    raw, offset = buffer.raw, 0
    while True:
        following, length = struct.unpack_from("<II", raw, offset)
        if raw[offset + 24:offset + 24 + length].decode("utf-16-le", "surrogatepass").upper() != "::$DATA":
            return True
        if not following:
            return False
        offset += following


def _dispose(handle):
    k = _api()[0]
    flags = ctypes.c_uint32(DISPOSITION_FLAGS)
    if k.SetFileInformationByHandle(handle, INFO_DISPOSITION_EX, ctypes.byref(flags), 4):
        return
    code = ctypes.get_last_error()
    if code in (1, 50, 87):  # the file system lacks the extended class; never fall back to chmod
        delete = ctypes.c_ubyte(1)
        if k.SetFileInformationByHandle(handle, INFO_DISPOSITION, ctypes.byref(delete), 1):
            return
        code = ctypes.get_last_error()
    raise _win_error("Deleting", code)


def _adopt(handle, flags):
    """A file descriptor that owns `handle`; on failure the handle is closed here, exactly once."""
    import msvcrt
    try:
        return msvcrt.open_osfhandle(handle, flags | os.O_BINARY)
    except BaseException:
        _close(handle)
        raise


# --- names and request validation ---

def _valid_component(name):
    if not name or len(name) > 255 or name in (".", "..") or name[-1] in ". ":
        return False
    if any(c in '<>:"/\\|?*' or ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in name):
        return False
    return name.split(".")[0].rstrip(" ").upper() not in RESERVED


def _secret(folded):
    return any(fnmatch.fnmatchcase(folded, pattern) for pattern in SECRET_PATTERNS)


def _absolute_drive_path(value, what):
    if not isinstance(value, str) or "\0" in value or not re.fullmatch(r"[A-Za-z]:[\\/].*", value, re.S):
        raise TargetError(f"The {what} must be an absolute path on a drive letter (no UNC or device path)")
    if any(part in (".", "..") for part in re.split(r"[\\/]+", value)[1:]):
        raise TargetError(f"The {what} must not contain '.' or '..' components")
    return value


def _validate(request):
    if not isinstance(request, dict):
        raise TargetError("A target request must be a JSON object")
    unknown = set(request) - {"project", "target_root", "target_name", "env_files", "exclude_names", "limits"}
    if unknown:
        raise TargetError(f"Unknown target request fields: {', '.join(sorted(unknown))}")
    root = request.get("target_root")
    if not isinstance(root, dict) or root.get("confirmed_by_user") is not True:
        raise TargetError("The target root must be confirmed by the user (target_root.confirmed_by_user = true)")
    if set(root) - {"path", "confirmed_by_user"}:
        raise TargetError("Unknown target_root fields")
    root_path = _absolute_drive_path(root.get("path"), "target root")
    project = _absolute_drive_path(request.get("project"), "project")
    name = request.get("target_name")
    if name is None:
        name = f"ask-codex-target-{secrets.token_hex(6)}"
    elif not isinstance(name, str) or not TARGET_NAME.fullmatch(name) or not _valid_component(name):
        raise TargetError("The target name must be one plain directory name")
    extra = request.get("exclude_names", [])
    if not isinstance(extra, list) or any(not isinstance(n, str) or not _valid_component(n) for n in extra):
        raise TargetError("Each extra excluded name must be one plain file or directory name")
    extra = frozenset(n.casefold() for n in extra)
    fixed = FIXED_NAMES | extra
    named = {}
    files = request.get("env_files", [])
    if not isinstance(files, list):
        raise TargetError("env_files must be a list of paths relative to the project")
    for item in files:
        parts = re.split(r"[\\/]", item) if isinstance(item, str) else None
        if not parts or ntpath.isabs(item) or ntpath.splitdrive(item)[0] or not all(map(_valid_component, parts)):
            raise TargetError(f"Invalid env file path {item!r}: a relative path inside the project is required")
        folded = tuple(p.casefold() for p in parts)
        if any(p in fixed for p in folded) or any(_secret(p) for p in folded[:-1]):
            raise TargetError(f"Env file {item!r} lies in or is a path that is never copied")
        named[folded] = item
    limits = dict(DEFAULT_LIMITS)
    given = request.get("limits", {})
    if not isinstance(given, dict) or set(given) - set(DEFAULT_LIMITS):
        raise TargetError("limits takes max_entries and max_bytes only")
    for key, value in given.items():
        if type(value) is not int or not 1 <= value <= DEFAULT_LIMITS[key]:
            raise TargetError(f"limits.{key} must be an integer between 1 and {DEFAULT_LIMITS[key]}")
        limits[key] = value
    return {"project": project, "root": root_path, "name": name, "fixed": fixed, "named": named, "limits": limits}


# --- I1: root placement ---

def _strip_final(path, what):
    if path.startswith("\\\\?\\") and re.fullmatch(r"[A-Za-z]:\\.*", path[4:], re.S):
        return path[4:]
    raise TargetError(f"The {what} must resolve to a local drive-letter path (not UNC)")


def _inside(child, parent):
    c, p = child.casefold().rstrip("\\").split("\\"), parent.casefold().rstrip("\\").split("\\")
    return c[:len(p)] == p


def _sync_roots():
    roots = [os.environ.get(name) for name in SYNC_ENV]
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, SYNC_ROOT_KEY) as manager:
            for i in range(winreg.QueryInfoKey(manager)[0]):
                try:
                    with winreg.OpenKey(manager, winreg.EnumKey(manager, i) + r"\UserSyncRoots") as users:
                        roots += [winreg.EnumValue(users, j)[1] for j in range(winreg.QueryInfoKey(users)[1])]
                except OSError:
                    continue
    except OSError:
        pass
    found = []
    for root in roots:
        if isinstance(root, str) and ntpath.isabs(root):
            found.append(ntpath.normpath(root))
            try:
                handle = _win_open(root, READ_ATTRIBUTES, FLAG_BACKUP_SEMANTICS)
                try:
                    found.append(_strip_final(_final_path(handle), "sync root"))
                finally:
                    _close(handle)
            except (OSError, TargetError):
                pass
    return found


def _open_root(path):
    try:
        handle = _win_open(path, LIST_DIRECTORY | ADD_SUBDIRECTORY | TRAVERSE | READ_ATTRIBUTES,
                           FLAG_BACKUP_SEMANTICS | FLAG_OPEN_REPARSE_POINT)
    except OSError:
        raise TargetError("The target root does not exist or cannot be opened") from None
    try:
        attributes, _ = _attribute_tag(handle)
        if attributes & ATTR_REPARSE:
            raise TargetError("The target root is a link or junction")
        if not attributes & ATTR_DIRECTORY:
            raise TargetError("The target root is not a directory")
        try:
            final = _strip_final(_final_path(handle), "target root")
            fixed = _drive_type(final) == DRIVE_FIXED
        except OSError:
            raise TargetError("The target root's volume cannot be determined") from None
        if not fixed:
            raise TargetError("The target root must be on a local fixed drive")
        return handle, final, _identity(handle)
    except BaseException:
        _close(handle)
        raise


def _check_ancestors(root):
    for sync in _sync_roots():
        if _inside(root, sync):
            raise TargetError("The target root is inside a cloud-sync folder")
    path = root
    while True:
        try:
            status = os.lstat(path)
        except OSError:
            raise TargetError(f"Cannot inspect {path}") from None
        tag = getattr(status, "st_reparse_tag", 0)
        if status.st_file_attributes & CLOUD_ATTRIBUTES or (tag & 0xFFFF0FFF) == 0x9000001A:
            raise TargetError("The target root is inside a cloud-sync folder")
        for marker in (".git", ".codex"):
            if os.path.lexists(ntpath.join(path, marker)):
                raise TargetError(f"An ancestor of the target ({path}) holds {marker}")
        parent = ntpath.dirname(path)
        if parent == path:
            return
        path = parent


def _open_project(path):
    try:
        handle = _win_open(path, LIST_DIRECTORY | TRAVERSE | READ_ATTRIBUTES, FLAG_BACKUP_SEMANTICS)
    except OSError:
        raise TargetError("The project does not exist or cannot be opened") from None
    try:
        if not _attribute_tag(handle)[0] & ATTR_DIRECTORY:
            raise TargetError("The project is not a directory")
        try:
            final = _final_path(handle)
        except OSError:
            raise TargetError("The project's final path cannot be determined") from None
        return handle, _strip_final(final, "project")  # local drive form only; UNC and volume paths refused
    except BaseException:
        _close(handle)
        raise


# --- record ---

def _write_record(directory, record):
    path = Path(directory) / RECORD
    temporary = path.with_name(RECORD + ".tmp")
    temporary.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, path)


def record_at(directory):
    """The run directory and its target record; refuses anything not owned by the CLI convention."""
    directory = Path(directory).resolve()  # non-strict, like plan_at (RAM disk)
    if directory.parent.name != "ask-codex" or not directory.name.startswith("run."):
        raise TargetError("Not an owned run directory")
    try:
        record = json.loads((directory / RECORD).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise TargetError("No target record in this run directory; nothing is removed") from None
    if not isinstance(record, dict) or record.get("version") != VERSION or record.get("directory") != str(directory):
        raise TargetError("Invalid target record; nothing is removed")
    return directory, record


def _create_directory(parent, name):
    """Exclusive create relative to a verified parent handle; never opens an existing entry."""
    return _nt_open(parent, name, LIST_DIRECTORY | ADD_FILE | ADD_SUBDIRECTORY | TRAVERSE | READ_ATTRIBUTES | DELETE,
                    DIRECTORY_FILE | OPEN_REPARSE_POINT, FILE_CREATE)


# --- the run directory that holds the record (never in the project) ---

def _outside_project(handle, shown, project):
    """Refuse when the open directory is, or cannot be shown not to be, inside the project."""
    try:
        final = _final_path(handle)
    except OSError:
        final = None
    if final is not None:
        # Fail closed: only a local drive-letter final path can be compared with the project's.
        if not re.fullmatch(r"\\\\\?\\[A-Za-z]:\\.*", final, re.S):
            raise TargetError("The run directory must be on a local drive (not UNC, a volume or a device path)")
        if _inside(final[4:], project):
            raise TargetError("The run directory must not be inside the project")
        return
    # A volume that reports no final path (e.g. a RAM disk). The project's volume always reports one
    # (_open_project requires it), so a different volume serial is a different volume.
    if not re.fullmatch(r"[A-Za-z]:\\.*", shown, re.S):
        raise TargetError("The run directory must be on a local drive (not UNC, a volume or a device path)")
    project_handle = _win_open(project, READ_ATTRIBUTES, FLAG_BACKUP_SEMANTICS)
    try:
        same_volume = _identity(project_handle)["volume_serial"] == _identity(handle)["volume_serial"]
    finally:
        _close(project_handle)
    if same_volume or _inside(shown, project):
        raise TargetError("The run directory cannot be shown to be outside the project")


def _new_run_directory(base, project):
    """Create <base>/ask-codex/run.* through handles; neither component may be a link or junction."""
    base_handle = _win_open(str(base), LIST_DIRECTORY | ADD_SUBDIRECTORY | TRAVERSE | READ_ATTRIBUTES,
                            FLAG_BACKUP_SEMANTICS)
    parent = run = None
    try:
        _outside_project(base_handle, str(base), project)
        try:
            parent = _nt_open(base_handle, "ask-codex", LIST_DIRECTORY | ADD_SUBDIRECTORY | TRAVERSE | READ_ATTRIBUTES,
                              OPEN_REPARSE_POINT)
        except NtError as error:
            if error.status not in (STATUS_NAME_NOT_FOUND, STATUS_PATH_NOT_FOUND):
                raise
            parent = _create_directory(base_handle, "ask-codex")
        attributes, _ = _attribute_tag(parent)
        if attributes & ATTR_REPARSE or not attributes & ATTR_DIRECTORY:
            raise TargetError(f"{base / 'ask-codex'} is a link, a junction or not a directory; nothing is created there")
        for _ in range(100):
            name = f"run.{secrets.token_hex(4)}"
            try:
                run = _create_directory(parent, name)
                break
            except NtError as error:
                if error.status != STATUS_NAME_COLLISION:
                    raise
        else:
            raise TargetError("No free run directory name")
        try:
            _outside_project(run, str(base / "ask-codex" / name), project)
        except BaseException:
            _dispose(run)  # the empty directory just created; nothing else is touched
            raise
        return base / "ask-codex" / name, True
    finally:
        for handle in (run, parent, base_handle):
            _close(handle)


def _verify_run_directory(directory, project):
    """Any factory's run directory: it and its parent are no links, and it is not inside the project."""
    for path in (directory, directory.parent):
        if os.lstat(path).st_file_attributes & ATTR_REPARSE:
            raise TargetError(f"{path} is a link or junction; the record is not written there")
    handle = _win_open(str(directory), READ_ATTRIBUTES, FLAG_BACKUP_SEMANTICS)
    try:
        _outside_project(handle, str(directory), project)
    finally:
        _close(handle)


def _exists(parent, name):
    try:
        _close(_nt_open(parent, name, READ_ATTRIBUTES, OPEN_REPARSE_POINT))
        return True
    except NtError as error:
        if error.status in (STATUS_NAME_NOT_FOUND, STATUS_PATH_NOT_FOUND):
            return False
        raise


# --- I2: copy ---

class _Copy:
    def __init__(self, spec, target):
        self.spec, self.target = spec, target
        self.entries = self.bytes = self.files = self.directories = 0
        self.skipped, self.excluded, self.streams, self.named_copied = [], [], [], set()
        self.git_layouts = []  # directories excluded as Git repository directories (also in `excluded`)

    def run(self, source, destination, parts=(), listing=None):
        for name, attributes, tag, size in _list(source) if listing is None else listing:
            rel = parts + (name,)
            shown = "/".join(rel)
            if not _valid_component(name):
                raise CopyFailure(f"reserved or invalid file name: {shown}")
            if attributes & (ATTR_REPARSE | RECALL_ATTRIBUTES):
                # Links and cloud placeholders are neither followed, recreated nor opened for reading.
                self.skipped.append({"path": shown, "reparse_tag": f"0x{tag:08X}", "attributes": f"0x{attributes:08X}"})
                continue
            folded = tuple(p.casefold() for p in rel)
            if folded[-1] in self.spec["fixed"] or (_secret(folded[-1]) and
                                                    (folded not in self.spec["named"] or attributes & ATTR_DIRECTORY)):
                self.excluded.append(shown)
                continue
            if len(self.target) + 1 + len(shown) > MAX_PATH_CHARS:
                raise CopyFailure(f"path too long in the target (over {MAX_PATH_CHARS} characters): {shown}")
            self.entries += 1
            if self.entries > self.spec["limits"]["max_entries"]:
                raise CopyFailure(f"more than {self.spec['limits']['max_entries']} entries")
            kind = DIRECTORY_FILE if attributes & ATTR_DIRECTORY else NON_DIRECTORY_FILE
            # Opened for attributes only; reopened for listing or reading only after the checks.
            meta = _nt_open(source, name, READ_ATTRIBUTES, kind | OPEN_REPARSE_POINT)
            try:
                current, current_tag = _attribute_tag(meta)
                if current & (ATTR_REPARSE | RECALL_ATTRIBUTES):
                    self.skipped.append({"path": shown, "reparse_tag": f"0x{current_tag:08X}",
                                         "attributes": f"0x{current:08X}", "changed_during_copy": True})
                    continue
                streams = _has_named_stream(meta)
                if attributes & ATTR_DIRECTORY:
                    copied = self.directory(meta, destination, name, rel, shown)
                else:
                    self.file(meta, destination, name, size, current)
                    self.named_copied.add(folded)
                    copied = True
                if streams and copied:
                    self.streams.append(shown)  # only the unnamed data stream is ever read and written
            finally:
                _close(meta)

    def directory(self, meta, destination, name, rel, shown):
        child = _nt_open(meta, "", LIST_DIRECTORY | READ_ATTRIBUTES, DIRECTORY_FILE | OPEN_REPARSE_POINT)
        try:
            listing = _list(child)
            if _git_layout(listing):  # VCS metadata under any name: never copied, contents never opened
                self.entries -= 1
                self.excluded.append(shown)
                self.git_layouts.append(shown)
                return False
            created = _create_directory(destination, name)
            self.directories += 1
            try:
                self.run(child, created, rel, listing)
            finally:
                _close(created)
            return True
        finally:
            _close(child)

    def file(self, meta, destination, name, size, attributes):
        limit = self.spec["limits"]["max_bytes"]
        if self.bytes + max(size, 0) > limit:
            raise CopyFailure(f"more than {limit} bytes")
        reader = _adopt(_nt_open(meta, "", READ_DATA | READ_ATTRIBUTES, NON_DIRECTORY_FILE | OPEN_REPARSE_POINT),
                        os.O_RDONLY)
        try:
            writer = _adopt(_nt_open(destination, name, WRITE_DATA | READ_ATTRIBUTES,
                                     NON_DIRECTORY_FILE | OPEN_REPARSE_POINT, FILE_CREATE,
                                     ATTR_READONLY if attributes & ATTR_READONLY else ATTR_NORMAL), os.O_WRONLY)
            try:
                while chunk := os.read(reader, 1 << 20):
                    self.bytes += len(chunk)
                    if self.bytes > limit:
                        raise CopyFailure(f"more than {limit} bytes")
                    view = memoryview(chunk)
                    while view:
                        view = view[os.write(writer, view):]
            finally:
                os.close(writer)
            self.files += 1
        finally:
            os.close(reader)


def _git_layout(listing):
    """Git's repository-directory criterion on a directory listing, as a superset, names compared
    case-insensitively: HEAD (not a directory; its content is not checked) with objects and refs entries of
    any type (Git on Windows accepts files there too, checked with git rev-parse), or HEAD with commondir
    (a linked worktree's administrative directory). Links count, since Git follows them."""
    kinds = {}
    for name, attributes, _, _ in listing:
        kinds[name.casefold()] = bool(attributes & ATTR_DIRECTORY)
    if kinds.get("head") is not False:
        return False
    return ("objects" in kinds and "refs" in kinds) or "commondir" in kinds


def _reparse_points(handle, parts=()):
    """Postcondition: links, recall-on-access entries and Git repository layouts found in the target."""
    found = []
    listing = _list(handle)
    if _git_layout(listing):
        found.append(f"{'/'.join(parts) or '.'} (Git repository layout)")
    for name, attributes, _, _ in listing:
        rel = parts + (name,)
        if attributes & (ATTR_REPARSE | RECALL_ATTRIBUTES):
            found.append("/".join(rel))
        elif attributes & ATTR_DIRECTORY:
            child = _nt_open(handle, name, LIST_DIRECTORY | READ_ATTRIBUTES, DIRECTORY_FILE | OPEN_REPARSE_POINT)
            try:
                if _attribute_tag(child)[0] & (ATTR_REPARSE | RECALL_ATTRIBUTES):
                    found.append("/".join(rel))
                else:
                    found += _reparse_points(child, rel)
            finally:
                _close(child)
    return found


# --- create ---

def create(request, make_run_directory):
    """Check everything, then call make_run_directory(project) -> (run directory, owns it), record, create, copy."""
    require_windows()
    with _placeholders_exposed():
        return _create(request, make_run_directory)


def _create(request, make_run_directory):
    spec = _validate(request)
    root_handle, root, root_identity = _open_root(spec["root"])
    project_handle = None
    try:
        _check_ancestors(root)
        project_handle, project = _open_project(spec["project"])
        if _inside(root, project) or _inside(project, root):
            raise TargetError("The target root must be neither inside the project nor contain it")
        if _git_layout(_list(project_handle)):
            raise TargetError("The project directory itself has a Git repository layout (HEAD with objects and "
                              "refs, or with commondir); it is VCS metadata and is never copied")
        target = root + ("" if root.endswith("\\") else "\\") + spec["name"]
        if len(target) > MAX_PATH_CHARS:
            raise TargetError("The target path is too long")
        try:
            if _exists(root_handle, spec["name"]):
                raise TargetError("The target path already exists; an existing path is never used")
        except OSError:
            raise TargetError("The target path cannot be checked") from None
        directory, owns = make_run_directory(project)
        directory = Path(directory)
        try:
            _verify_run_directory(directory, project)
            if (directory / RECORD).exists():
                raise TargetError("This run directory already has a target record")
        except BaseException:
            if owns:
                try:
                    directory.rmdir()  # only when empty; a link is removed as a link
                except OSError:
                    pass
            raise
        entry = {"kind": "target", "path": target, "state": "pending"}
        record = {"version": VERSION, "directory": str(directory), "owns_run_directory": owns, "project": project,
                  "root": {"path": root, **root_identity}, "entries": [entry], "copy": "pending"}
        try:
            _write_record(directory, record)
        except BaseException:
            _discard_record(directory, owns)
            raise
        try:
            target_handle = _create_directory(root_handle, spec["name"])
        except OSError as error:
            _discard_record(directory, owns)
            if isinstance(error, NtError) and error.status == STATUS_NAME_COLLISION:
                raise TargetError("The target path already exists; an existing path is never used") from None
            raise TargetError(f"The target directory could not be created: {error}") from None
        try:
            entry.update(state="created", **_identity(target_handle))
            _write_record(directory, record)
        except Exception as error:
            _close(target_handle)
            return {"state": "failed", "reason": f"The target's identity could not be recorded ({error}); "
                    "it is kept for removal by hand", "retained_location": target, "record": str(directory)}
        copy = _Copy(spec, target)
        try:
            try:
                copy.run(project_handle, target_handle)
                missing = [shown for folded, shown in spec["named"].items() if folded not in copy.named_copied]
                if missing:
                    raise CopyFailure(f"named file not found as a regular file in the project: {', '.join(missing)}")
                links = _reparse_points(target_handle)
                if links:
                    raise CopyFailure(f"reparse point or Git repository layout inside the target after the copy: "
                                      f"{', '.join(links)}")
            finally:
                _close(target_handle)
            record["copy"] = "done"
            _write_record(directory, record)
        except Exception as error:
            reason = str(error) if isinstance(error, CopyFailure) else f"{type(error).__name__}: {error}"
            try:
                removal = remove(directory)
            except Exception as failure:  # the record stays; report where the partial target is
                removal = {"state": "failed", "reason": f"{type(failure).__name__}: {failure}"}
            if removal["state"] == "removed":
                return {"state": "failed", "reason": f"Copy failed ({reason}); the partial target was removed",
                        "target_removed": True}
            return {"state": "failed", "reason": f"Copy failed ({reason}); the partial target could not be removed",
                    "target_removed": False, "retained_location": target, "record": str(directory),
                    "removal": removal}
        return {"state": "created", "directory": str(directory), "target": target, "root": root,
                "skipped_links": copy.skipped, "excluded": copy.excluded, "git_layouts_excluded": copy.git_layouts,
                "streams_not_copied": copy.streams,
                "env_files": sorted(spec["named"].values()),
                "copied": {"files": copy.files, "directories": copy.directories, "bytes": copy.bytes}}
    finally:
        _close(project_handle)
        _close(root_handle)


def _discard_record(directory, owns):
    (directory / RECORD).unlink(missing_ok=True)
    if owns:
        try:
            directory.rmdir()
        except OSError:
            pass


def create_sibling(run_directory, purpose):
    """Create a recorded directory beside the target under the root (an MCP TEMP directory, I5)."""
    require_windows()
    with _placeholders_exposed():
        return _create_sibling(run_directory, purpose)


def _create_sibling(run_directory, purpose):
    if not isinstance(purpose, str) or not PURPOSE.fullmatch(purpose):
        raise TargetError("Invalid sibling purpose")
    directory, record = record_at(run_directory)
    targets = [e for e in record["entries"] if e.get("kind") == "target" and e.get("state") == "created"]
    if len(targets) != 1:
        raise TargetError("No created target in this record")
    root = record["root"]["path"]
    name = f"{ntpath.basename(targets[0]['path'])}.{purpose}-{secrets.token_hex(4)}"
    handle = _verified_root(record)
    try:
        entry = {"kind": "temp", "purpose": purpose, "path": ntpath.join(root, name), "state": "pending"}
        record["entries"].append(entry)
        _write_record(directory, record)
        created = _create_directory(handle, name)
        try:
            entry.update(state="created", **_identity(created))
        finally:
            _close(created)
        _write_record(directory, record)
        return entry["path"]
    finally:
        _close(handle)


# --- I3: removal ---

def _verified_root(record):
    root = record.get("root") or {}
    try:
        handle = _win_open(root.get("path"), TRAVERSE | READ_ATTRIBUTES, FLAG_BACKUP_SEMANTICS | FLAG_OPEN_REPARSE_POINT)
    except (OSError, ctypes.ArgumentError):
        raise TargetError("The recorded target root cannot be opened") from None
    try:
        attributes, _ = _attribute_tag(handle)
        identity = _identity(handle)
        if attributes & ATTR_REPARSE or not attributes & ATTR_DIRECTORY or \
                identity != {"volume_serial": root.get("volume_serial"), "file_id": root.get("file_id")}:
            raise TargetError("The target root no longer matches the record")
        return handle
    except BaseException:
        _close(handle)
        raise


def _patiently(operation, deadline):
    while True:
        try:
            return operation()
        except OSError as error:
            busy = getattr(error, "status", None) == STATUS_SHARING_VIOLATION or \
                getattr(error, "winerror", None) == ERROR_SHARING_VIOLATION
            if not busy or time.monotonic() >= deadline:
                raise
            time.sleep(0.25)


def _remove_open(handle, deadline):
    """Delete the object behind an open handle; directories are emptied first, links are not followed."""
    attributes, _ = _attribute_tag(handle)
    if attributes & ATTR_DIRECTORY and not attributes & ATTR_REPARSE:
        listing = _nt_open(handle, "", LIST_DIRECTORY | READ_ATTRIBUTES, DIRECTORY_FILE | OPEN_REPARSE_POINT)
        try:
            names = [entry[0] for entry in _list(listing)]
        finally:
            _close(listing)
        for name in names:
            child = _patiently(lambda: _nt_open(handle, name, DELETE | READ_ATTRIBUTES, OPEN_REPARSE_POINT), deadline)
            try:
                _remove_open(child, deadline)
            finally:
                _close(child)
    _patiently(lambda: _dispose(handle), deadline)


def remove(run_directory):
    """Remove every recorded entry that still matches the record; report what is kept and where."""
    require_windows()
    with _placeholders_exposed():
        return _remove(run_directory)


def _remove(run_directory):
    directory, record = record_at(run_directory)
    root = record.get("root", {}).get("path")
    if not isinstance(root, str) or not isinstance(record.get("entries"), list):
        raise TargetError("Invalid target record; nothing is removed")
    try:
        root_handle = _verified_root(record)
    except TargetError as error:
        return _kept(directory, record, [{"path": e.get("path"), "reason": str(error)} for e in record["entries"]])
    deadline = time.monotonic() + REMOVAL_PATIENCE_S
    removed, absent, failures = [], [], []
    try:
        for entry in reversed(list(record["entries"])):
            path = entry.get("path") if isinstance(entry, dict) else None
            reason = _remove_entry(root_handle, root, entry, deadline) if isinstance(path, str) else "invalid entry"
            if reason in ("removed", "absent"):
                (removed if reason == "removed" else absent).append(path)
                record["entries"].remove(entry)
                _write_record(directory, record)
            else:
                failures.append({"path": path, "reason": reason})
    finally:
        _close(root_handle)
    if failures:
        return _kept(directory, record, failures)
    if record.get("owns_run_directory"):
        (directory / RECORD).unlink()
        try:
            directory.rmdir()
        except OSError:
            return {"state": "removed", "removed": removed, "absent": absent, "retained_location": str(directory),
                    "reason": "The target is removed; the run directory holds other files and is kept"}
    return {"state": "removed", "removed": removed, "absent": absent}


def _remove_entry(root_handle, root, entry, deadline):
    path = entry["path"]
    parent, name = ntpath.split(path)
    if parent.rstrip("\\").casefold() != root.rstrip("\\").casefold() or not _valid_component(name):
        return "the recorded path is outside the recorded root; nothing is deleted"
    try:
        handle = _nt_open(root_handle, name, DELETE | READ_ATTRIBUTES, OPEN_REPARSE_POINT)
    except NtError as error:
        if error.status in (STATUS_NAME_NOT_FOUND, STATUS_PATH_NOT_FOUND):
            return "absent"
        return f"cannot be opened: {error}"
    try:
        return _remove_checked(handle, entry, deadline)
    except OSError as error:
        return f"cannot be checked: {error}"
    finally:
        _close(handle)


def _remove_checked(handle, entry, deadline):
    if entry.get("state") != "created":
        return "created without a recorded identity; nothing is deleted"
    attributes, _ = _attribute_tag(handle)
    if attributes & ATTR_REPARSE:
        return "is now a link or junction; it is not followed and nothing is deleted"
    if not attributes & ATTR_DIRECTORY:
        return "is no longer a directory; nothing is deleted"
    if _identity(handle) != {"volume_serial": entry.get("volume_serial"), "file_id": entry.get("file_id")}:
        return "identity does not match the record (replaced after creation); nothing is deleted"
    try:
        _remove_open(handle, deadline)
    except OSError as error:
        return f"removal failed: {error}"
    return "removed"


def _kept(directory, record, failures):
    _write_record(directory, record)
    return {"state": "failed", "reason": "Some recorded paths were kept: " +
            "; ".join(f"{f['path']}: {f['reason']}" for f in failures),
            "retained_location": failures[0]["path"], "failures": failures, "record": str(directory)}


# --- CLI ---

def create_command(request_path, base):
    try:
        request = json.loads(Path(request_path).read_text(encoding="utf-8-sig"))

        def make_run_directory(project):
            # The base itself may be a link: its resolved (final) path is what is checked, here and again
            # on its handle. <base>\ask-codex and run.* are opened or created through handles, never followed.
            resolved = Path(base).resolve()
            # Before anything is created (refusal leaves nothing behind): local drive form only, outside the project.
            if not re.fullmatch(r"[A-Za-z]:\\.*", str(resolved), re.S):
                raise TargetError("The base must be on a local drive (not UNC, a volume or a device path)")
            if _inside(str(resolved), project):
                raise TargetError("The run directory must not be inside the project")
            resolved.mkdir(parents=True, exist_ok=True)
            return _new_run_directory(resolved, project)

        return create(request, make_run_directory)
    except TargetError as error:
        return {"state": "failed", "reason": str(error), **error.details}
    except Exception as error:  # fail closed with a report; never a traceback past the CLI
        return {"state": "failed", "reason": f"{type(error).__name__}: target creation failed"}


def remove_command(run_directory):
    try:
        return remove(run_directory)
    except TargetError as error:
        return {"state": "failed", "reason": str(error), "retained_location": str(run_directory), **error.details}
    except Exception as error:  # fail closed with a report; never a traceback past the CLI
        return {"state": "failed", "reason": f"{type(error).__name__}: target removal failed",
                "retained_location": str(run_directory)}
