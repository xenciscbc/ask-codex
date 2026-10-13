"""Windows primitives of the exercise's own processes (plan I8, guard part; I7's listener checks). Windows only.

- `Job`: a named kill-on-close Job Object (unguessable name, ERROR_ALREADY_EXISTS refuses, breakaway not allowed).
  The creating process holds the only handle and is never a member: closing the handle (or dying) ends every
  process in it.
- `start_suspended(job, argv, cwd, env)`: CreateProcessW with CREATE_SUSPENDED, assigned to the job, then
  ResumeThread on the returned thread handle (subprocess.Popen closes that handle), so no descendant can start
  outside the job. The child inherits only its three stdio pipe ends (PROC_THREAD_ATTRIBUTE_HANDLE_LIST): never a
  job handle, a listener socket or any other handle of the caller.
- `tcp_listeners()`: the IPv4 and IPv6 TCP listener table with owning PIDs (GetExtendedTcpTable).
- `image_path(pid)`, `named_streams(path)`, `short_path(path)`: small queries used by the guard.
"""
import ctypes
from ctypes import wintypes
import os
import secrets
import socket
import struct
import subprocess
import time

# Loaded only on Windows, so the module imports elsewhere (the platform gate refuses at use).
_k32 = ctypes.WinDLL("kernel32", use_last_error=True) if os.name == "nt" else None
_iphlp = ctypes.WinDLL("iphlpapi") if os.name == "nt" else None

ERROR_ALREADY_EXISTS = 183
CREATE_SUSPENDED = 0x4
CREATE_UNICODE_ENVIRONMENT = 0x400
EXTENDED_STARTUPINFO_PRESENT = 0x80000
CREATE_NO_WINDOW = 0x08000000
STARTF_USESTDHANDLES = 0x100
HANDLE_FLAG_INHERIT = 0x1
PROC_THREAD_ATTRIBUTE_HANDLE_LIST = 0x20002
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
JobObjectBasicAccountingInformation, JobObjectBasicProcessIdList, JobObjectExtendedLimitInformation = 1, 3, 9
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
SYNCHRONIZE = 0x100000
INFINITE = 0xFFFFFFFF
WAIT_OBJECT_0 = 0
STILL_ACTIVE = 259
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


class _SecurityAttributes(ctypes.Structure):
    _fields_ = [("nLength", wintypes.DWORD), ("lpSecurityDescriptor", ctypes.c_void_p),
                ("bInheritHandle", wintypes.BOOL)]


class _StartupInfo(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("lpReserved", wintypes.LPWSTR), ("lpDesktop", wintypes.LPWSTR),
                ("lpTitle", wintypes.LPWSTR), ("dwX", wintypes.DWORD), ("dwY", wintypes.DWORD),
                ("dwXSize", wintypes.DWORD), ("dwYSize", wintypes.DWORD), ("dwXCountChars", wintypes.DWORD),
                ("dwYCountChars", wintypes.DWORD), ("dwFillAttribute", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                ("wShowWindow", wintypes.WORD), ("cbReserved2", wintypes.WORD), ("lpReserved2", ctypes.c_void_p),
                ("hStdInput", wintypes.HANDLE), ("hStdOutput", wintypes.HANDLE), ("hStdError", wintypes.HANDLE)]


class _StartupInfoEx(ctypes.Structure):
    _fields_ = [("StartupInfo", _StartupInfo), ("lpAttributeList", ctypes.c_void_p)]


class _ProcessInformation(ctypes.Structure):
    _fields_ = [("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE), ("dwProcessId", wintypes.DWORD),
                ("dwThreadId", wintypes.DWORD)]


class _BasicLimit(ctypes.Structure):
    _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD)]


class _IoCounters(ctypes.Structure):
    _fields_ = [(name, ctypes.c_uint64) for name in ("ReadOperationCount", "WriteOperationCount",
                                                    "OtherOperationCount", "ReadTransferCount",
                                                    "WriteTransferCount", "OtherTransferCount")]


class _ExtendedLimit(ctypes.Structure):
    _fields_ = [("BasicLimitInformation", _BasicLimit), ("IoInfo", _IoCounters),
                ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]


class _Accounting(ctypes.Structure):
    _fields_ = [("TotalUserTime", ctypes.c_int64), ("TotalKernelTime", ctypes.c_int64),
                ("ThisPeriodTotalUserTime", ctypes.c_int64), ("ThisPeriodTotalKernelTime", ctypes.c_int64),
                ("TotalPageFaultCount", wintypes.DWORD), ("TotalProcesses", wintypes.DWORD),
                ("ActiveProcesses", wintypes.DWORD), ("TotalTerminatedProcesses", wintypes.DWORD)]


def _signatures():
    k = _k32
    k.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    k.CreateJobObjectW.restype = wintypes.HANDLE
    k.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    k.QueryInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
                                            ctypes.POINTER(wintypes.DWORD)]
    k.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    k.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    k.CloseHandle.argtypes = [wintypes.HANDLE]
    k.CreatePipe.argtypes = [ctypes.POINTER(wintypes.HANDLE), ctypes.POINTER(wintypes.HANDLE),
                             ctypes.POINTER(_SecurityAttributes), wintypes.DWORD]
    k.SetHandleInformation.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD]
    k.InitializeProcThreadAttributeList.argtypes = [ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
                                                    ctypes.POINTER(ctypes.c_size_t)]
    k.UpdateProcThreadAttribute.argtypes = [ctypes.c_void_p, wintypes.DWORD, ctypes.c_size_t, ctypes.c_void_p,
                                            ctypes.c_size_t, ctypes.c_void_p, ctypes.c_void_p]
    k.DeleteProcThreadAttributeList.argtypes = [ctypes.c_void_p]
    k.CreateProcessW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, ctypes.c_void_p, ctypes.c_void_p,
                                 wintypes.BOOL, wintypes.DWORD, ctypes.c_void_p, wintypes.LPCWSTR,
                                 ctypes.POINTER(_StartupInfoEx), ctypes.POINTER(_ProcessInformation)]
    k.ResumeThread.argtypes = [wintypes.HANDLE]
    k.ResumeThread.restype = wintypes.DWORD
    k.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    k.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    k.WaitForSingleObject.restype = wintypes.DWORD
    k.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k.OpenProcess.restype = wintypes.HANDLE
    k.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                             ctypes.POINTER(wintypes.DWORD)]
    k.GetShortPathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
    k.GetShortPathNameW.restype = wintypes.DWORD
    k.FindFirstStreamW.argtypes = [wintypes.LPCWSTR, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    k.FindFirstStreamW.restype = wintypes.HANDLE
    k.FindNextStreamW.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    k.FindClose.argtypes = [wintypes.HANDLE]
    _iphlp.GetExtendedTcpTable.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD), wintypes.BOOL,
                                           wintypes.ULONG, ctypes.c_int, wintypes.ULONG]
    _iphlp.GetExtendedTcpTable.restype = wintypes.DWORD


if os.name == "nt":
    _signatures()


def _fail(what):
    raise OSError(f"{what} failed (Windows error {ctypes.get_last_error()})")


class Job:
    """A named kill-on-close job; the creator holds the only handle and is not a member."""

    def __init__(self, prefix):
        self.name = f"{prefix}-{secrets.token_hex(16)}"
        handle = _k32.CreateJobObjectW(None, self.name)
        error = ctypes.get_last_error()
        if not handle:
            _fail("CreateJobObjectW")
        if error == ERROR_ALREADY_EXISTS:
            _k32.CloseHandle(handle)
            raise OSError("A job with the exercise's job name already exists; refused")
        self.handle = handle
        info = _ExtendedLimit()
        info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE  # no BREAKAWAY_OK
        if not _k32.SetInformationJobObject(handle, JobObjectExtendedLimitInformation, ctypes.byref(info),
                                            ctypes.sizeof(info)):
            self.close()
            _fail("SetInformationJobObject")

    def active_processes(self):
        info = _Accounting()
        if not _k32.QueryInformationJobObject(self.handle, JobObjectBasicAccountingInformation, ctypes.byref(info),
                                              ctypes.sizeof(info), None):
            _fail("QueryInformationJobObject")
        return info.ActiveProcesses

    def pids(self):
        count = 256
        while True:
            class _List(ctypes.Structure):
                _fields_ = [("Assigned", wintypes.DWORD), ("Listed", wintypes.DWORD),
                            ("Ids", ctypes.c_size_t * count)]
            data = _List()
            if _k32.QueryInformationJobObject(self.handle, JobObjectBasicProcessIdList, ctypes.byref(data),
                                              ctypes.sizeof(data), None):
                return [int(data.Ids[i]) for i in range(data.Listed)]
            if ctypes.get_last_error() != 234 or count > 65536:  # ERROR_MORE_DATA
                _fail("QueryInformationJobObject")
            count *= 4

    def terminate(self, patience=10.0):
        """End every process in the job; True when the job reports no active process within `patience`."""
        _k32.TerminateJobObject(self.handle, 1)
        deadline = time.monotonic() + patience
        while time.monotonic() < deadline:
            if self.active_processes() == 0:
                return True
            time.sleep(0.1)
        return self.active_processes() == 0

    def close(self):
        if getattr(self, "handle", None):
            _k32.CloseHandle(self.handle)
            self.handle = None


class Process:
    """A process started by start_suspended: handle, pid and the parent ends of its stdio pipes."""

    def __init__(self, handle, pid, stdin, stdout, stderr):
        self.handle, self.pid, self.stdin, self.stdout, self.stderr = handle, pid, stdin, stdout, stderr

    def poll(self):
        code = wintypes.DWORD()
        if not _k32.GetExitCodeProcess(self.handle, ctypes.byref(code)):
            _fail("GetExitCodeProcess")
        return None if code.value == STILL_ACTIVE else code.value

    def wait(self, timeout):
        return _k32.WaitForSingleObject(self.handle, int(timeout * 1000)) == WAIT_OBJECT_0

    def close(self):
        for stream in (self.stdin, self.stdout, self.stderr):
            try:
                stream.close()
            except OSError:
                pass
        if self.handle:
            _k32.CloseHandle(self.handle)
            self.handle = None


def _pipe():
    read, write = wintypes.HANDLE(), wintypes.HANDLE()
    attributes = _SecurityAttributes(ctypes.sizeof(_SecurityAttributes), None, False)
    if not _k32.CreatePipe(ctypes.byref(read), ctypes.byref(write), ctypes.byref(attributes), 0):
        _fail("CreatePipe")
    return read.value, write.value


def _environment_block(env):
    # Sorted case-insensitively, as Windows expects; every name once (case-insensitive).
    seen = {}
    for key, value in env.items():
        if "=" in key[1:] or "\0" in key or "\0" in value:
            raise ValueError("Invalid environment entry")
        seen[key.upper()] = (key, value)
    items = sorted(seen.values(), key=lambda kv: kv[0].upper())
    return "".join(f"{k}={v}\0" for k, v in items) + "\0"


def start_suspended(job, argv, cwd, env):
    """Create argv[0] suspended with piped stdio, assign it to `job`, then resume it."""
    child_ends, parent_ends = [], []
    try:
        for parent_writes in (True, False, False):  # stdin, stdout, stderr
            read, write = _pipe()
            child, parent = (read, write) if parent_writes else (write, read)
            child_ends.append(child)
            parent_ends.append(parent)
            if not _k32.SetHandleInformation(child, HANDLE_FLAG_INHERIT, HANDLE_FLAG_INHERIT):
                _fail("SetHandleInformation")
        size = ctypes.c_size_t()
        _k32.InitializeProcThreadAttributeList(None, 1, 0, ctypes.byref(size))
        attribute_list = ctypes.create_string_buffer(size.value)
        if not _k32.InitializeProcThreadAttributeList(attribute_list, 1, 0, ctypes.byref(size)):
            _fail("InitializeProcThreadAttributeList")
        handles = (wintypes.HANDLE * 3)(*child_ends)
        try:
            if not _k32.UpdateProcThreadAttribute(attribute_list, 0, PROC_THREAD_ATTRIBUTE_HANDLE_LIST, handles,
                                                  ctypes.sizeof(handles), None, None):
                _fail("UpdateProcThreadAttribute")
            startup = _StartupInfoEx()
            startup.StartupInfo.cb = ctypes.sizeof(_StartupInfoEx)
            startup.StartupInfo.dwFlags = STARTF_USESTDHANDLES
            startup.StartupInfo.hStdInput, startup.StartupInfo.hStdOutput, startup.StartupInfo.hStdError = child_ends
            startup.lpAttributeList = ctypes.cast(attribute_list, ctypes.c_void_p)
            info = _ProcessInformation()
            command_line = ctypes.create_unicode_buffer(subprocess.list2cmdline(argv))
            block = ctypes.create_unicode_buffer(_environment_block(env))
            flags = CREATE_SUSPENDED | CREATE_UNICODE_ENVIRONMENT | EXTENDED_STARTUPINFO_PRESENT | CREATE_NO_WINDOW
            if not _k32.CreateProcessW(str(argv[0]).replace("/", "\\"), command_line, None, None, True, flags,
                                       ctypes.cast(block, ctypes.c_void_p), str(cwd).replace("/", "\\"),
                                       ctypes.byref(startup), ctypes.byref(info)):
                _fail("CreateProcessW")
        finally:
            _k32.DeleteProcThreadAttributeList(attribute_list)
        try:
            if not _k32.AssignProcessToJobObject(job.handle, info.hProcess):
                _fail("AssignProcessToJobObject")
            if _k32.ResumeThread(info.hThread) == 0xFFFFFFFF:
                _fail("ResumeThread")
        except BaseException:
            _k32.TerminateProcess(info.hProcess, 1)
            _k32.CloseHandle(info.hProcess)
            raise
        finally:
            _k32.CloseHandle(info.hThread)
    except BaseException:
        for handle in parent_ends:
            _k32.CloseHandle(handle)
        raise
    finally:
        for handle in child_ends:
            _k32.CloseHandle(handle)
    import msvcrt
    files = [os.fdopen(msvcrt.open_osfhandle(handle, os.O_WRONLY if index == 0 else os.O_RDONLY),
                       "wb" if index == 0 else "rb", buffering=0) for index, handle in enumerate(parent_ends)]
    return Process(info.hProcess, info.dwProcessId, *files)


# --- queries ---

def image_path(pid):
    handle = _k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return None
    try:
        size = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        if not _k32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return None
        return buffer.value
    finally:
        _k32.CloseHandle(handle)


def tcp_listeners():
    """[(address, port, pid)] for every listening TCP socket, IPv4 and IPv6."""
    found = []
    for family, row_size in ((socket.AF_INET, 24), (socket.AF_INET6, 56)):
        size = wintypes.DWORD(0)
        _iphlp.GetExtendedTcpTable(None, ctypes.byref(size), False, family, 3, 0)  # TCP_TABLE_OWNER_PID_LISTENER
        for _ in range(5):
            buffer = ctypes.create_string_buffer(size.value + 4096)
            size = wintypes.DWORD(len(buffer))
            result = _iphlp.GetExtendedTcpTable(buffer, ctypes.byref(size), False, family, 3, 0)
            if result == 0:
                break
            if result != 122:  # ERROR_INSUFFICIENT_BUFFER
                raise OSError(f"GetExtendedTcpTable failed ({result})")
        else:
            raise OSError("GetExtendedTcpTable kept growing")
        raw = buffer.raw
        count = struct.unpack_from("<I", raw, 0)[0]
        for index in range(count):
            offset = 4 + index * row_size
            if family == socket.AF_INET:
                _state, address, port, _ra, _rp, pid = struct.unpack_from("<IIIIII", raw, offset)
                text = socket.inet_ntop(socket.AF_INET, struct.pack("<I", address))
            else:
                address = raw[offset:offset + 16]
                _scope, port = struct.unpack_from("<II", raw, offset + 16)
                pid = struct.unpack_from("<I", raw, offset + 52)[0]
                text = socket.inet_ntop(socket.AF_INET6, address)
            found.append((text, socket.ntohs(port & 0xFFFF), pid))
    return found


def short_path(path):
    buffer = ctypes.create_unicode_buffer(32768)
    length = _k32.GetShortPathNameW(str(path), buffer, len(buffer))
    return buffer.value if 0 < length < len(buffer) else None


class _StreamData(ctypes.Structure):
    _fields_ = [("StreamSize", ctypes.c_int64), ("cStreamName", ctypes.c_wchar * (260 + 36))]


def named_streams(path):
    """Names of the alternate data streams of a file (empty for none)."""
    data = _StreamData()
    handle = _k32.FindFirstStreamW(str(path), 0, ctypes.byref(data), 0)
    if handle == INVALID_HANDLE_VALUE or handle is None:
        return []
    names = []
    try:
        while True:
            if data.cStreamName not in ("::$DATA",):
                names.append(data.cStreamName)
            if not _k32.FindNextStreamW(handle, ctypes.byref(data)):
                break
    finally:
        _k32.FindClose(handle)
    return names
