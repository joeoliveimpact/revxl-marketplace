"""One process-shared lock for editor renders, including nested trial renders."""
import contextlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path

import runtime as rt

_local = threading.local()


class HeavyJobError(Exception):
    """A single plain refusal line for the command's normal error handler."""


def free_ram_mb():
    """Available physical RAM in MB, or None if the OS cannot report it."""
    try:
        if sys.platform == "win32":
            import ctypes

            class MemoryStatus(ctypes.Structure):
                _fields_ = [("length", ctypes.c_uint32), ("load", ctypes.c_uint32)] + [
                    (name, ctypes.c_ulonglong) for name in (
                        "total_phys", "avail_phys", "total_page", "avail_page",
                        "total_virtual", "avail_virtual", "avail_extended")]

            status = MemoryStatus()
            status.length = ctypes.sizeof(status)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return status.avail_phys // (1024 * 1024)
        elif sys.platform.startswith("linux"):
            return os.sysconf("SC_AVPHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") // (1024 * 1024)
        elif sys.platform == "darwin":
            output = subprocess.check_output(["vm_stat"], text=True, timeout=5)
            page_size = int(re.search(r"page size of (\d+) bytes", output).group(1))
            pages = dict(re.findall(r"^Pages (free|inactive):\s+(\d+)\.\s*$", output, re.MULTILINE))
            return (int(pages["free"]) + int(pages["inactive"])) * page_size // (1024 * 1024)
    except Exception:
        pass
    return None


def _resources(min_ram_gb, min_disk_gb):
    ram = free_ram_mb()
    if ram is None:
        if not getattr(_local, "warned_unknown", False):
            print("Couldn't read free memory; going ahead.", flush=True)
            _local.warned_unknown = True
    elif ram < min_ram_gb * 1024:
        raise HeavyJobError(f"This editor job needs {min_ram_gb:g} GB free RAM; close other apps and run again.")
    if min(shutil.disk_usage(folder).free for folder in
           (Path.cwd(), Path(tempfile.gettempdir()), rt.state_dir())) < min_disk_gb * 2**30:
        raise HeavyJobError(f"This editor job needs {min_disk_gb:g} GB free disk; free some space and run again.")


def pid_alive(pid):
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return ctypes.get_last_error() != 87  # Access denied is not proof of a dead process.
        try:
            code = wintypes.DWORD()
            return not kernel.GetExitCodeProcess(handle, ctypes.byref(code)) or code.value == 259
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _open_lock(path, create):
    """Open this one lock; Windows handles must allow rename while they are open."""
    if os.name == "nt":
        import ctypes
        import msvcrt
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                      ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        kernel.CreateFileW.restype = wintypes.HANDLE
        # CREATE_NEW is the Windows equivalent of O_CREAT | O_EXCL; share delete permits atomic retirement.
        handle = kernel.CreateFileW(str(path), 0xC0000000, 7, None, 1 if create else 3, 0x80, None)
        if handle == wintypes.HANDLE(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            fd = msvcrt.open_osfhandle(handle, os.O_RDWR | os.O_BINARY)
        except BaseException:
            kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel.CloseHandle(handle)
            raise
    else:
        fd = os.open(path, os.O_RDWR | (os.O_CREAT | os.O_EXCL if create else 0), 0o600)
    return os.fdopen(fd, "r+b", buffering=0)


def _try_guard(stream):
    """Guard the opened inode itself, never a second lock file.

    A stale waiter must own this guard AND still name the current inode before
    renaming it. A waiter with an old handle therefore cannot retire a fresh lock.
    """
    try:
        if os.name == "nt":
            import msvcrt
            # Keep the locked byte away from metadata reads (Windows locks are mandatory).
            stream.seek(2**31 - 1)
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            finally:
                stream.seek(0)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


def _current(path, stream):
    try:
        return os.path.samestat(path.stat(), os.fstat(stream.fileno()))
    except FileNotFoundError:
        return False


def _owner(stream):
    stream.seek(0)
    raw = stream.read()
    try:
        data = json.loads(raw)
        if type(data) is int and data > 0:  # MB5 wrote only a PID and a newline.
            return data, "another editor job"
        pid = data["pid"]
        if type(pid) is int and pid > 0:
            return pid, " ".join(str(data["label"]).split())
    except (ValueError, KeyError, TypeError):
        pass
    return None, "another editor job"


@contextlib.contextmanager
def heavy_job(label, min_ram_gb=3, min_disk_gb=10):
    path = rt.state_dir() / "locks" / "heavy.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    nested = getattr(_local, "owner", None) == (os.getpid(), path)
    if not nested:
        _local.warned_unknown = False
    _resources(min_ram_gb, min_disk_gb)
    if nested:
        yield  # Trials may call compose in this thread; keep the same lock and label.
        return
    deadline, waiting = time.monotonic() + 2 * 60 * 60, False
    owned = None
    try:
        while owned is None:
            try:
                stream = _open_lock(path, create=True)
            except FileExistsError:
                try:
                    with _open_lock(path, create=False) as stale:
                        pid, owner_label = _owner(stale)
                        if _try_guard(stale) and _current(path, stale):
                            # An empty file may still be getting its metadata; allow that small window.
                            abandoned = pid is None and time.time() - path.stat().st_mtime >= 5
                            if abandoned or pid is not None and not pid_alive(pid):
                                retired = path.with_name(path.name + "." + uuid.uuid4().hex + ".stale")
                                path.rename(retired)
                                retired.unlink()
                                continue
                except FileNotFoundError:
                    continue
                if pid is not None and not waiting:
                    print(f"Another editor job is running ({owner_label}); yours is queued and starts when it finishes.", flush=True)
                    waiting = True
                if time.monotonic() >= deadline:
                    raise HeavyJobError("Waited 2 hours for another editor job to finish; run this job again.")
                time.sleep(.1)
                continue
            try:
                while not _try_guard(stream):
                    time.sleep(.1)
                if not _current(path, stream):
                    stream.close()
                    continue
                owned = stream
                stream.write((json.dumps(dict(pid=os.getpid(), label=" ".join(str(label).split()),
                                              started=time.time())) + "\n").encode("utf-8"))
                _resources(min_ram_gb, min_disk_gb)  # Waiting can change the available budget.
                _local.owner = (os.getpid(), path)
            except BaseException:
                if owned is None:
                    stream.close()
                raise
        yield
    finally:
        if owned is not None:
            _local.owner = None
            try:
                if _current(path, owned):
                    path.unlink()
            finally:
                owned.close()  # Releases the inode guard even on render failure or interruption.
