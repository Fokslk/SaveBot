from __future__ import annotations

import atexit
import os
import re
import sys
from pathlib import Path

from bot.config import BASE_DIR

LOCK_PATH = BASE_DIR / "data" / "save_mod.lock"

_BOT_MAIN_RE = re.compile(r"(?i)(?:^|[\\/\s\"'])-m\s+bot\.main(?:\s|$)")
_BOT_PANEL_RE = re.compile(r"(?i)(?:^|[\\/\s\"'])-m\s+bot\.panel(?:\s|$)")


def _iter_python_processes() -> list[tuple[int, str]]:
    if os.name != "nt":
        return []
    try:
        import subprocess

        cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            (
                "Get-CimInstance Win32_Process | "
                "Where-Object { $_.Name -match '^python(w)?\\.exe$' } | "
                "Select-Object ProcessId, CommandLine | ConvertTo-Json -Compress"
            ),
        ]
        raw = subprocess.check_output(
            cmd, text=True, stderr=subprocess.DEVNULL, timeout=15
        ).strip()
        if not raw:
            return []
        import json

        data = json.loads(raw)
        rows = data if isinstance(data, list) else [data]
        out: list[tuple[int, str]] = []
        for row in rows:
            pid = int(row.get("ProcessId") or 0)
            cmd_line = str(row.get("CommandLine") or "")
            if pid:
                out.append((pid, cmd_line))
        return out
    except Exception:
        return []


def kill_foreign_bots(*, keep_pid: int | None = None, include_panel: bool = False) -> list[int]:
    pass
    keep_pid = os.getpid() if keep_pid is None else keep_pid
    killed: list[int] = []

    for pid, cmd_line in _iter_python_processes():
        if pid == keep_pid:
            continue
        is_main = bool(_BOT_MAIN_RE.search(cmd_line))
        is_panel = bool(_BOT_PANEL_RE.search(cmd_line))
        if not is_main and not (include_panel and is_panel):
            continue
        try:
            if os.name == "nt":
                import subprocess

                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                    timeout=10,
                )
            else:
                os.kill(pid, 9)
            killed.append(pid)
        except Exception:
            pass
    return killed


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            import ctypes

            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = ctypes.windll.kernel32.OpenProcess(
                PROCESS_QUERY_LIMITED_INFORMATION, False, pid
            )
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)
                return True
            return False
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


class InstanceLock:
    pass

    def __init__(self, path: Path = LOCK_PATH) -> None:
        self.path = path
        self._fh = None

    def _read_owner_pid(self) -> int:
        try:
            text = self.path.read_text(encoding="utf-8").strip()
            return int(text) if text else 0
        except Exception:
            return 0

    def acquire(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        owner = self._read_owner_pid()
        if owner and owner != os.getpid() and not _pid_alive(owner):
            try:
                self.path.unlink(missing_ok=True)
            except OSError:
                pass

        self._fh = open(self.path, "a+", encoding="utf-8")
        try:
            if os.name == "nt":
                import msvcrt

                self._fh.seek(0)
                msvcrt.locking(self._fh.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self._fh.close()
            self._fh = None
            return False

        self._fh.seek(0)
        self._fh.truncate()
        self._fh.write(str(os.getpid()))
        self._fh.flush()
        atexit.register(self.release)
        return True

    def release(self) -> None:
        if self._fh is None:
            return
        try:
            if os.name == "nt":
                import msvcrt

                self._fh.seek(0)
                msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        try:
            self._fh.close()
        except OSError:
            pass
        self._fh = None


def already_running_message() -> str:
    return (
        "Save Mod уже запущен в другом окне.\n"
        "Закройте предыдущую панель или завершите лишние процессы python -m bot.main."
    )


def ensure_single_instance(*, kill_others: bool = True) -> InstanceLock:
    if kill_others:
        kill_foreign_bots(keep_pid=os.getpid(), include_panel=False)
    lock = InstanceLock()
    if not lock.acquire():
        print(already_running_message(), file=sys.stderr)
        raise SystemExit(1)
    return lock
