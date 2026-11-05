from __future__ import annotations

import ctypes
import logging
import os
import sys
import threading
import time
from datetime import datetime

from bot.runtime_stats import STATS, RecentEvent

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"
BLUE = "\033[34m"
WHITE = "\033[97m"
GRAY = "\033[90m"

_KIND_COLOR = {
    "message": CYAN,
    "media": GREEN,
    "deleted": YELLOW,
    "edit": MAGENTA,
    "error": RED,
    "connection": GREEN,
    "update": GRAY,
    "business_message": CYAN,
    "edited_business_message": MAGENTA,
    "deleted_business_messages": YELLOW,
    "business_connection": GREEN,
}

_KIND_RU = {
    "message": "сообщение",
    "media": "медиа",
    "deleted": "удаление",
    "edit": "правка",
    "error": "ошибка",
    "connection": "связь",
    "update": "апдейт",
    "business_message": "сообщение",
    "edited_business_message": "правка",
    "deleted_business_messages": "удаление",
    "business_connection": "связь",
}


class _PollHeartbeatFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        if "getUpdates" in msg:
            STATS.touch_poll()
        return True


def prepare_console() -> None:
    pass
    if os.name != "nt":
        return

    kernel32 = ctypes.windll.kernel32

    hout = kernel32.GetStdHandle(-11)
    mode = ctypes.c_uint32()
    if kernel32.GetConsoleMode(hout, ctypes.byref(mode)):
        kernel32.SetConsoleMode(hout, mode.value | 0x0004)

    hin = kernel32.GetStdHandle(-10)
    if kernel32.GetConsoleMode(hin, ctypes.byref(mode)):
        enable_extended = 0x0080
        quick_edit = 0x0040
        new_mode = (mode.value | enable_extended) & ~quick_edit
        kernel32.SetConsoleMode(hin, new_mode)

    try:
        ctypes.windll.kernel32.SetConsoleTitleW("Save Mod · Live Stats")
    except Exception:
        pass

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _fmt_uptime(seconds: float) -> str:
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def _fmt_ago(ts: float) -> str:
    if not ts:
        return "—"
    delta = max(0, int(time.time() - ts))
    if delta < 60:
        return f"{delta}с назад"
    if delta < 3600:
        return f"{delta // 60}м назад"
    return f"{delta // 3600}ч назад"


def _fmt_time(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%H:%M:%S") if ts else "--:--:--"


def _status_badge(status: str, last_poll_at: float) -> str:
    stale = last_poll_at and (time.time() - last_poll_at) > 45
    if status == "starting":
        return f"{YELLOW}{BOLD}● ЗАПУСК{RESET}"
    if status == "stopped":
        return f"{RED}{BOLD}● СТОП{RESET}"
    if stale:
        return f"{YELLOW}{BOLD}● ЗАСТОЙ{RESET}"
    return f"{GREEN}{BOLD}● ОНЛАЙН{RESET}"


def _metric(label: str, value: str, accent: str = WHITE) -> str:
    return f"{GRAY}{label}{RESET} {accent}{BOLD}{value}{RESET}"


def _bar(value: int, peak: int, width: int = 12, color: str = CYAN) -> str:
    if peak <= 0:
        filled = 0
    else:
        filled = min(width, max(0, round(width * value / peak)))
    empty = width - filled
    return f"{color}{'█' * filled}{GRAY}{'░' * empty}{RESET}"


def _kind_label(kind: str) -> str:
    primary = kind.split(",")[0].strip()
    return _KIND_RU.get(primary, primary)[:11]


def render_frame() -> str:
    snap = STATS.snapshot()
    uptime = _fmt_uptime(time.time() - snap["started_at"])
    width = 64

    session_vals = [
        snap["messages"],
        snap["media"],
        snap["deleted"],
        snap["edits"],
        snap["updates"],
        snap["errors"],
    ]
    peak = max(session_vals) if any(session_vals) else 1

    lines: list[str] = []
    title = " SAVE MOD "
    badge = _status_badge(snap["status"], snap["last_poll_at"])

    lines.append(f"{CYAN}╔{RESET}{BOLD}{WHITE}{title}{RESET}{CYAN}" + "═" * (width - len(title) - 1) + f"╗{RESET}")
    lines.append(
        f"{CYAN}║{RESET}  {badge}"
        f"   {_metric('аптайм', uptime, CYAN)}"
        f"   {_metric('poll', _fmt_ago(snap['last_poll_at']), GRAY)}"
    )
    lines.append(f"{CYAN}╟" + "─" * width + f"╢{RESET}")

    lines.append(f"{CYAN}║{RESET}  {DIM}сессия{RESET}")
    msg_n = f"{snap['messages']:,}"
    media_n = f"{snap['media']:,}"
    del_n = f"{snap['deleted']:,}"
    edit_n = f"{snap['edits']:,}"
    upd_n = f"{snap['updates']:,}"
    err_n = f"{snap['errors']:,}"
    db_n = f"{snap['db_messages']:,}"
    db_del_n = f"{snap['db_deleted']:,}"

    lines.append(
        f"{CYAN}║{RESET}  {_metric('сообщ.', msg_n, CYAN)}   "
        f"{_bar(snap['messages'], peak, color=CYAN)}   "
        f"{_metric('медиа', media_n, GREEN)}   "
        f"{_bar(snap['media'], peak, color=GREEN)}"
    )
    lines.append(
        f"{CYAN}║{RESET}  {_metric('удал.', del_n, YELLOW)}   "
        f"{_bar(snap['deleted'], peak, color=YELLOW)}   "
        f"{_metric('правки', edit_n, MAGENTA)}   "
        f"{_bar(snap['edits'], peak, color=MAGENTA)}"
    )
    lines.append(
        f"{CYAN}║{RESET}  {_metric('апдейты', upd_n, BLUE)}   "
        f"{_bar(snap['updates'], peak, color=BLUE)}   "
        f"{_metric('ошибки', err_n, RED)}   "
        f"{_bar(snap['errors'], peak, color=RED)}"
    )

    lines.append(f"{CYAN}╟" + "─" * width + f"╢{RESET}")
    lines.append(
        f"{CYAN}║{RESET}  {_metric('в БД', db_n, WHITE)}   "
        f"{_metric('удалено в БД', db_del_n, YELLOW)}   "
        f"{_metric('событие', _fmt_ago(snap['last_event_at']), GRAY)}"
    )

    lines.append(f"{CYAN}╟" + "─" * width + f"╢{RESET}")
    lines.append(f"{CYAN}║{RESET}  {DIM}недавние события{RESET}")

    recent: list[RecentEvent] = snap["recent"]
    for i in range(8):
        if i < len(recent):
            ev = recent[i]
            primary = ev.kind.split(",")[0].strip()
            color = _KIND_COLOR.get(primary, GRAY)
            label = _kind_label(ev.kind)
            detail = ev.detail.replace("\n", " ")
            if len(detail) > 36:
                detail = detail[:35] + "…"
            body = (
                f"{GRAY}{_fmt_time(ev.at)}{RESET}  "
                f"{color}{label:<11}{RESET} "
                f"{WHITE}{detail}{RESET}"
            )
            lines.append(f"{CYAN}║{RESET}  {body}")
        else:
            lines.append(f"{CYAN}║{RESET}  {DIM}·{RESET}")

    lines.append(f"{CYAN}╟" + "─" * width + f"╢{RESET}")
    footer = "Ctrl+C — стоп  ·  подробный лог → bot.log  ·  Quick Edit выкл."
    lines.append(f"{CYAN}║{RESET}  {DIM}{footer}{RESET}")
    lines.append(f"{CYAN}╚" + "═" * width + f"╝{RESET}")
    return "\n".join(lines)


def _dashboard_loop(
    stop_event: threading.Event,
    interval: float = 1.0,
    db_refresh=None,
) -> None:
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()
    ticks = 0
    try:
        while not stop_event.wait(interval):
            ticks += 1
            if db_refresh is not None and ticks % 15 == 0:
                try:
                    db_refresh()
                except Exception:
                    pass
            frame = render_frame()
            sys.stdout.write("\033[H\033[J")
            sys.stdout.write(frame)
            sys.stdout.write("\n")
            sys.stdout.flush()
    finally:
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()


def start_dashboard(
    *,
    interval: float = 1.0,
    db_refresh=None,
) -> tuple[threading.Event, threading.Thread]:
    logging.getLogger("httpx").addFilter(_PollHeartbeatFilter())
    stop_event = threading.Event()
    thread = threading.Thread(
        target=_dashboard_loop,
        args=(stop_event, interval, db_refresh),
        name="save-mod-dashboard",
        daemon=True,
    )
    sys.stdout.write("\033[H\033[J")
    sys.stdout.write(render_frame() + "\n")
    sys.stdout.flush()
    thread.start()
    return stop_event, thread


def stop_dashboard(stop_event: threading.Event | None) -> None:
    if stop_event is not None:
        stop_event.set()
    STATS.set_status("stopped")
    sys.stdout.write("\033[?25h\n")
    sys.stdout.flush()
