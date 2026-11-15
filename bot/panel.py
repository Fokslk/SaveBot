from __future__ import annotations

import logging
import os
import sys
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk

from bot.config import BASE_DIR, load_config
from bot.instance import InstanceLock, already_running_message, kill_foreign_bots
from bot.runtime_stats import RecentEvent, RecentMessage, STATS
from bot.runner import BotRunner, setup_logging

logger = logging.getLogger(__name__)

# ── palette ──────────────────────────────────────────────
BG = "#10151d"
BG2 = "#171f2a"
BG3 = "#1b2532"
CARD = "#1b2532"
LINE = "#354457"
TEXT = "#f0f4fa"
MUTED = "#aab8c9"
ACCENT = "#68d9bd"
ACCENT2 = "#8abfff"
WARN = "#edc878"
DANGER = "#ff9292"
OK = "#79dfb1"


KIND_LABELS = {
    "ru": {
        "save": "Сохранение:",
        "media": "Медиа:",
        "deleted": "Удаление:",
        "edit": "Правка:",
        "error": "Ошибка:",
        "connection": "Связь:",
        "update": "Апдейт:",
    },
    "en": {
        "save": "Saved:",
        "media": "Media:",
        "deleted": "Deleted:",
        "edit": "Edit:",
        "error": "Error:",
        "connection": "Connection:",
        "update": "Update:",
    },
}

UI_TEXT = {
    "ru": {
        "subtitle": "Панель управления", "overview": "ОБЗОР", "activity": "АКТИВНОСТЬ", "quick_access": "БЫСТРЫЙ ДОСТУП", "uptime": "Время работы", "language_button": "EN", "start": "▶  Запустить",
        "stop": "■  Остановить", "auto_off": "Автоперезапуск: выкл", "auto_on": "Автоперезапуск: вкл",
        "media_button": "📁 Медиа", "log_button": "📄 Лог", "data_button": "🏠 База",
        "poll": "poll", "event": "событие", "messages": "Сообщения", "media": "Медиа",
        "deleted": "Удаления", "edits": "Правки", "errors": "Ошибки", "database": "В базе",
        "tab_events": "Действия", "tab_messages": "Сообщения", "tab_errors": "Ошибки", "tab_logs": "Логи",
        "footer_default": "Один экземпляр · Подробности в bot.log", "status_starting": "ЗАПУСК",
        "status_stopped": "ОСТАНОВЛЕН", "status_conflict": "КОНФЛИКТ", "status_stale": "ЗАСТОЙ",
        "status_online": "ОНЛАЙН", "list_empty": "  пока пусто…", "messages_empty": "  пока пусто…",
        "no_name": "без имени", "auto_enabled": "Автоперезапуск включён: перезапуск после 45 секунд без polling.",
        "auto_disabled": "Автоперезапуск выключен.", "auto_restarting": "Застой polling: выполняется перезапуск бота…",
        "auto_waiting": "Поток запущен, ожидается восстановление polling.",
        "auto_restarted": "Бот автоматически перезапущен после застоя polling.",
        "auto_timeout": "Автоперезапуск отменён: поток бота не остановился за 30 секунд.",
        "auto_retry": "Автоперезапуск не удался. Повторная попытка через 60 секунд.",
        "auto_error": "Ошибка автоперезапуска: {error}", "foreign_processes": "Остановлены другие процессы: {pids}",
        "already_running_title": "Save Mod", "already_running_footer": "Уже запущено в другом окне — закройте его и нажмите «Запустить»",
        "config_error_title": "Конфигурация", "start_error_title": "Запуск", "startup_error_title": "Save Mod",
        "config_error_footer": "Ошибка .env: {error}", "close_title": "Выход",
        "close_question": "Остановить бота и закрыть панель?",
        "startup_error": "Ошибка запуска:\n{error}", "folder_missing_title": "Папка не найдена",
        "folder_missing": "Для этой переписки пока нет папки с сохранёнными медиа.",
        "folder_open_error": "Не удалось открыть папку",
    },
    "en": {
        "subtitle": "Control panel", "overview": "OVERVIEW", "activity": "ACTIVITY", "quick_access": "QUICK ACCESS", "uptime": "Uptime", "language_button": "RU", "start": "▶  Start",
        "stop": "■  Stop", "auto_off": "Auto-restart: off", "auto_on": "Auto-restart: on",
        "media_button": "📁 Media", "log_button": "📄 Log", "data_button": "🏠 Database",
        "poll": "poll", "event": "event", "messages": "Messages", "media": "Media",
        "deleted": "Deleted", "edits": "Edits", "errors": "Errors", "database": "In database",
        "tab_events": "Activity", "tab_messages": "Messages", "tab_errors": "Errors", "tab_logs": "Logs",
        "footer_default": "Single instance · Details in bot.log", "status_starting": "STARTING",
        "status_stopped": "STOPPED", "status_conflict": "CONFLICT", "status_stale": "STALE",
        "status_online": "ONLINE", "list_empty": "  nothing yet…", "messages_empty": "  no messages yet…",
        "no_name": "unknown", "auto_enabled": "Auto-restart enabled: restarts after 45 seconds without polling.",
        "auto_disabled": "Auto-restart disabled.", "auto_restarting": "Polling stalled: restarting the bot…",
        "auto_waiting": "Bot thread started; waiting for polling to recover.",
        "auto_restarted": "Bot automatically restarted after polling stalled.",
        "auto_timeout": "Auto-restart cancelled: bot thread did not stop within 30 seconds.",
        "auto_retry": "Auto-restart failed. Retrying in 60 seconds.",
        "auto_error": "Auto-restart error: {error}", "foreign_processes": "Stopped other processes: {pids}",
        "already_running_title": "Save Mod", "already_running_footer": "Already running in another window. Close it before starting again.",
        "config_error_title": "Configuration", "start_error_title": "Start", "startup_error_title": "Save Mod",
        "config_error_footer": "Configuration error: {error}", "close_title": "Exit",
        "close_question": "Stop the bot and close the panel?",
        "startup_error": "Startup error:\n{error}", "folder_missing_title": "Folder not found",
        "folder_missing": "No saved media folder exists for this conversation yet.",
        "folder_open_error": "Could not open folder",
    },
}


def _fmt_uptime(seconds: float) -> str:
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def _fmt_ago(ts: float, language: str = "ru") -> str:
    if not ts:
        return "—"
    delta = max(0, int(time.time() - ts))
    if delta < 60:
        return f"{delta}s" if language == "en" else f"{delta}с"
    if delta < 3600:
        return f"{delta // 60}m" if language == "en" else f"{delta // 60}м"
    return f"{delta // 3600}h" if language == "en" else f"{delta // 3600}ч"


def _fmt_time(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%H:%M:%S") if ts else "--:--:--"


def _kind_label(kind: str, language: str = "ru") -> str:
    primary = kind.split(",")[0].strip()
    return KIND_LABELS[language].get(primary, primary)


class MetricCard(tk.Frame):
    """A compact metric with a consistent accent and readable hierarchy."""

    def __init__(self, master, title: str, accent: str = ACCENT, **kw):
        super().__init__(master, bg=CARD, highlightthickness=1, highlightbackground=LINE, **kw)
        tk.Frame(self, bg=accent, height=3).pack(fill="x")
        inner = tk.Frame(self, bg=CARD)
        inner.pack(fill="both", expand=True, padx=14, pady=(10, 12))
        self.title_lbl = tk.Label(
            inner, text=title.upper(), bg=CARD, fg=MUTED,
            font=("Segoe UI", 9, "bold"), anchor="w",
        )
        self.title_lbl.pack(fill="x")
        self.value_lbl = tk.Label(
            inner, text="0", bg=CARD, fg=TEXT,
            font=("Segoe UI", 23, "bold"), anchor="w",
        )
        self.value_lbl.pack(fill="x", pady=(3, 0))

    def set(self, value: str) -> None:
        self.value_lbl.configure(text=value)


class SaveModPanel(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Save Mod")
        self.geometry("1100x760")
        self.minsize(860, 640)
        self.configure(bg=BG)
        self._language = "ru"
        self._runner = BotRunner()
        self._lock: InstanceLock | None = None
        self._auto_started = False
        self._auto_restart_enabled = True
        self._bot_should_run = False
        self._auto_restart_pending = False
        self._auto_restart_attempted = False
        self._auto_restart_result: str | None = None
        self._auto_restart_retry_at: float | None = None
        self._last_log_refresh_at = 0.0
        self._media_dir = BASE_DIR / "media"
        self._visible_messages: list[RecentMessage] = []

        try:
            self.iconbitmap(default="")  # ignore missing icon
        except Exception:
            pass

        self._build_style()
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(200, self._tick)
        self.after(400, self._bootstrap)

    def _build_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(0, 0, 0, 0))
        style.configure(
            "TNotebook.Tab", background=BG2, foreground=MUTED,
            padding=(18, 10), borderwidth=0, font=("Segoe UI", 10, "bold"),
        )
        style.map("TNotebook.Tab", background=[("selected", CARD), ("active", BG3)],
                  foreground=[("selected", TEXT), ("active", TEXT)])
        style.configure("Dark.Vertical.TScrollbar", background=LINE, troughcolor=BG3,
                        borderwidth=0, arrowsize=12)
        style.configure("Dark.Horizontal.TScrollbar", background=LINE, troughcolor=BG3,
                        borderwidth=0, arrowsize=12)

    def _button(self, parent, text, command, *, primary=False):
        bg = ACCENT if primary else BG3
        fg = "#09251e" if primary else TEXT
        return tk.Button(
            parent, text=text, command=command, bg=bg, fg=fg,
            activebackground="#8ae6d0" if primary else LINE,
            activeforeground=fg, disabledforeground="#8291a3",
            relief="flat", borderwidth=0, highlightthickness=1,
            highlightbackground=bg if primary else LINE, highlightcolor=ACCENT2,
            font=("Segoe UI", 10, "bold"), padx=14, pady=8, cursor="hand2",
            takefocus=True,
        )

    def _build_ui(self) -> None:
        # Header: brand on the left, live status and uptime on the right.
        header = tk.Frame(self, bg=BG2, highlightthickness=1, highlightbackground=LINE)
        header.pack(fill="x")
        brand = tk.Frame(header, bg=BG2)
        brand.pack(side="left", padx=24, pady=16)
        mark = tk.Label(brand, text="S", bg=ACCENT, fg="#09251e",
                        font=("Segoe UI", 16, "bold"), width=3, height=1)
        mark.pack(side="left", padx=(0, 12))
        brand_text = tk.Frame(brand, bg=BG2)
        brand_text.pack(side="left")
        tk.Label(brand_text, text="SAVE MOD", bg=BG2, fg=TEXT,
                 font=("Segoe UI", 17, "bold"), anchor="w").pack(anchor="w")
        self.subtitle = tk.Label(brand_text, text=self._tr("subtitle"), bg=BG2, fg=MUTED,
                                 font=("Segoe UI", 10), anchor="w")
        self.subtitle.pack(anchor="w")

        right = tk.Frame(header, bg=BG2)
        right.pack(side="right", padx=24)
        self.btn_language = self._button(right, self._tr("language_button"), self._toggle_language)
        self.btn_language.pack(side="right", padx=(18, 0))
        uptime_box = tk.Frame(right, bg=BG2)
        uptime_box.pack(side="right", padx=(20, 0))
        self.uptime_title = tk.Label(uptime_box, text=self._tr("uptime"), bg=BG2, fg=MUTED,
                                     font=("Segoe UI", 9), anchor="w")
        self.uptime_title.pack(anchor="w")
        self.uptime_lbl = tk.Label(uptime_box, text="—", bg=BG2, fg=TEXT,
                                   font=("Consolas", 11, "bold"), anchor="w")
        self.uptime_lbl.pack(anchor="w")
        status_box = tk.Frame(right, bg=BG2)
        status_box.pack(side="right")
        self.status_dot = tk.Label(status_box, text="●", bg=BG2, fg=MUTED, font=("Segoe UI", 13))
        self.status_dot.pack(side="left", padx=(0, 6))
        self.status_lbl = tk.Label(status_box, text=self._tr("status_stopped"), bg=BG2, fg=MUTED,
                                   font=("Segoe UI", 10, "bold"))
        self.status_lbl.pack(side="left")

        # The primary actions are separate from shortcuts so they remain easy to scan.
        actions = tk.Frame(self, bg=BG)
        actions.pack(fill="x", padx=24, pady=(18, 0))
        self.btn_start = self._button(actions, self._tr("start"), self._start_bot, primary=True)
        self.btn_start.pack(side="left", padx=(0, 8))
        self.btn_stop = self._button(actions, self._tr("stop"), self._stop_bot)
        self.btn_stop.configure(state="disabled")
        self.btn_stop.pack(side="left", padx=(0, 8))
        self.btn_auto_restart = self._button(actions, self._tr("auto_on"), self._toggle_auto_restart)
        self.btn_auto_restart.configure(bg=OK, fg="#062218", activebackground=ACCENT,
                                        activeforeground="#062218", highlightbackground=OK)
        self.btn_auto_restart.pack(side="left")
        self.poll_lbl = tk.Label(actions, text="", bg=BG, fg=MUTED, font=("Segoe UI", 10), anchor="e")
        self.poll_lbl.pack(side="right", padx=(8, 0))

        shortcuts = tk.Frame(self, bg=BG)
        shortcuts.pack(fill="x", padx=24, pady=(12, 0))
        self.quick_title = tk.Label(shortcuts, text=self._tr("quick_access"), bg=BG, fg=MUTED,
                                    font=("Segoe UI", 9, "bold"))
        self.quick_title.pack(side="left", padx=(0, 14))
        self.btn_media = self._button(shortcuts, self._tr("media_button"), self._open_media)
        self.btn_log = self._button(shortcuts, self._tr("log_button"), self._open_log)
        self.btn_data = self._button(shortcuts, self._tr("data_button"), self._open_data)
        for button in (self.btn_media, self.btn_log, self.btn_data):
            button.pack(side="left", padx=(0, 8))

        overview = tk.Frame(self, bg=BG)
        overview.pack(fill="x", padx=24, pady=(20, 8))
        self.overview_title = tk.Label(overview, text=self._tr("overview"), bg=BG, fg=MUTED,
                                       font=("Segoe UI", 9, "bold"), anchor="w")
        self.overview_title.pack(side="left")
        metrics = tk.Frame(self, bg=BG)
        metrics.pack(fill="x", padx=24)
        for i in range(6):
            metrics.columnconfigure(i, weight=1, uniform="metrics")
        self.card_msg = MetricCard(metrics, self._tr("messages"), ACCENT2)
        self.card_media = MetricCard(metrics, self._tr("media"), ACCENT)
        self.card_del = MetricCard(metrics, self._tr("deleted"), WARN)
        self.card_edit = MetricCard(metrics, self._tr("edits"), "#d4afff")
        self.card_err = MetricCard(metrics, self._tr("errors"), DANGER)
        self.card_db = MetricCard(metrics, self._tr("database"), "#9badc1")
        for i, card in enumerate((self.card_msg, self.card_media, self.card_del,
                                   self.card_edit, self.card_err, self.card_db)):
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0))

        section = tk.Frame(self, bg=BG)
        section.pack(fill="x", padx=24, pady=(20, 8))
        self.activity_title = tk.Label(section, text=self._tr("activity"), bg=BG, fg=MUTED,
                                      font=("Segoe UI", 9, "bold"), anchor="w")
        self.activity_title.pack(side="left")
        footer = tk.Frame(self, bg=BG2, height=34, highlightthickness=1, highlightbackground=LINE)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)
        self.footer_lbl = tk.Label(footer, text=self._tr("footer_default"), bg=BG2, fg=MUTED,
                                   font=("Segoe UI", 9), anchor="w")
        self.footer_lbl.pack(fill="both", expand=True, padx=24)
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=24, pady=(0, 16))
        self.nb = ttk.Notebook(body)
        self.nb.pack(fill="both", expand=True)
        self.events_list = self._make_list_tab(self._tr("tab_events"))
        self.messages_list = self._make_messages_tab(self._tr("tab_messages"))
        self.errors_list = self._make_list_tab(self._tr("tab_errors"))
        self.log_text = self._make_log_tab(self._tr("tab_logs"))
        self._update_poll_label(STATS.snapshot())

    def _tr(self, key: str, **values: str) -> str:
        return UI_TEXT[self._language][key].format(**values)

    def _update_poll_label(self, snap: dict) -> None:
        poll = _fmt_ago(snap["last_poll_at"], self._language)
        event = _fmt_ago(snap["last_event_at"], self._language)
        self.poll_lbl.configure(text=f"{self._tr('poll')}: {poll} · {self._tr('event')}: {event}")

    def _toggle_language(self) -> None:
        self._language = "en" if self._language == "ru" else "ru"
        self._refresh_language()

    def _refresh_language(self) -> None:
        self.subtitle.configure(text=self._tr("subtitle"))
        self.uptime_title.configure(text=self._tr("uptime"))
        self.quick_title.configure(text=self._tr("quick_access"))
        self.overview_title.configure(text=self._tr("overview"))
        self.activity_title.configure(text=self._tr("activity"))
        self.btn_language.configure(text=self._tr("language_button"))
        self.btn_start.configure(text=self._tr("start"))
        self.btn_stop.configure(text=self._tr("stop"))
        self.btn_media.configure(text=self._tr("media_button"))
        self.btn_auto_restart.configure(
            text=self._tr("auto_on" if self._auto_restart_enabled else "auto_off")
        )
        self.btn_log.configure(text=self._tr("log_button"))
        self.btn_data.configure(text=self._tr("data_button"))
        for card, key in (
            (self.card_msg, "messages"),
            (self.card_media, "media"),
            (self.card_del, "deleted"),
            (self.card_edit, "edits"),
            (self.card_err, "errors"),
            (self.card_db, "database"),
        ):
            card.title_lbl.configure(text=self._tr(key).upper())
        for widget, key in (
            (self.events_list, "tab_events"),
            (self.messages_list, "tab_messages"),
            (self.errors_list, "tab_errors"),
            (self.log_text, "tab_logs"),
        ):
            self.nb.tab(widget.master, text=f"  {self._tr(key)}  ")
        self.footer_lbl.configure(text=self._tr("footer_default"))
        self._update_poll_label(STATS.snapshot())

    def _make_list_tab(self, title: str) -> tk.Listbox:
        frame = tk.Frame(self.nb, bg=BG3)
        self.nb.add(frame, text=f"  {title}  ")
        lb = tk.Listbox(
            frame,
            bg=BG3,
            fg=TEXT,
            selectbackground=LINE,
            selectforeground=TEXT,
            activestyle="none",
            borderwidth=0,
            highlightthickness=0,
            font=("Consolas", 10),
        )
        scroll = ttk.Scrollbar(frame, orient="vertical", command=lb.yview, style="Dark.Vertical.TScrollbar")
        lb.configure(yscrollcommand=scroll.set)
        lb.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        scroll.pack(side="right", fill="y", pady=8, padx=(0, 8))
        return lb

    def _make_messages_tab(self, title: str) -> tk.Text:
        frame = tk.Frame(self.nb, bg=BG3)
        self.nb.add(frame, text=f"  {title}  ")
        text = tk.Text(
            frame,
            bg=BG3,
            fg=TEXT,
            insertbackground=TEXT,
            borderwidth=0,
            highlightthickness=0,
            font=("Consolas", 10),
            wrap="none",
            state="disabled",
        )
        scroll = ttk.Scrollbar(frame, orient="vertical", command=text.yview, style="Dark.Vertical.TScrollbar")
        xscroll = ttk.Scrollbar(frame, orient="horizontal", command=text.xview, style="Dark.Horizontal.TScrollbar")
        xscroll.pack(side="bottom", fill="x", padx=8, pady=(0, 8))
        text.configure(yscrollcommand=scroll.set, xscrollcommand=xscroll.set)
        text.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        scroll.pack(side="right", fill="y", pady=8, padx=(0, 8))
        text.tag_configure("user_id", foreground=ACCENT2, underline=True)
        text.tag_bind("user_id", "<Enter>", lambda event: event.widget.configure(cursor="hand2"))
        text.tag_bind("user_id", "<Leave>", lambda event: event.widget.configure(cursor="xterm"))
        text.tag_bind("user_id", "<Button-1>", self._open_message_folder_from_event)
        return text

    def _make_log_tab(self, title: str) -> tk.Text:
        frame = tk.Frame(self.nb, bg=BG3)
        self.nb.add(frame, text=f"  {title}  ")
        txt = tk.Text(
            frame,
            bg=BG3,
            fg=MUTED,
            insertbackground=TEXT,
            borderwidth=0,
            highlightthickness=0,
            font=("Consolas", 9),
            wrap="none",
            state="disabled",
        )
        scroll = ttk.Scrollbar(frame, orient="vertical", command=txt.yview, style="Dark.Vertical.TScrollbar")
        xscroll = ttk.Scrollbar(frame, orient="horizontal", command=txt.xview, style="Dark.Horizontal.TScrollbar")
        xscroll.pack(side="bottom", fill="x", padx=8, pady=(0, 8))
        txt.configure(yscrollcommand=scroll.set, xscrollcommand=xscroll.set)
        txt.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        scroll.pack(side="right", fill="y", pady=8, padx=(0, 8))
        txt.tag_configure("err", foreground=DANGER)
        txt.tag_configure("warn", foreground=WARN)
        txt.tag_configure("ok", foreground=OK)
        return txt

    def _bootstrap(self) -> None:
        try:
            killed = kill_foreign_bots(keep_pid=os.getpid(), include_panel=False)
            if killed:
                self.footer_lbl.configure(
                    text=self._tr("foreign_processes", pids=", ".join(map(str, killed)))
                )
            lock = InstanceLock()
            if not lock.acquire():
                messagebox.showerror(self._tr("already_running_title"), already_running_message())
                self.footer_lbl.configure(text=self._tr("already_running_footer"))
                return
            self._lock = lock

            try:
                config = load_config()
                self._media_dir = config.media_dir
            except Exception as exc:
                messagebox.showerror(self._tr("config_error_title"), str(exc))
                self.footer_lbl.configure(text=self._tr("config_error_footer", error=exc))
                return

            self._start_bot()
        except Exception as exc:
            _write_crash(exc)
            messagebox.showerror(self._tr("startup_error_title"), self._tr("startup_error", error=exc))
            self.footer_lbl.configure(text=self._tr("auto_error", error=exc))

    def _start_bot(self) -> None:
        if self._runner.is_running:
            return
        if self._lock is None:
            lock = InstanceLock()
            if not lock.acquire():
                messagebox.showerror(self._tr("already_running_title"), already_running_message())
                return
            self._lock = lock
        kill_foreign_bots(keep_pid=os.getpid(), include_panel=False)
        self._bot_should_run = True
        try:
            self._auto_restart_attempted = False
            self._auto_restart_retry_at = None
            self._runner.start()
        except Exception as exc:
            _write_crash(exc)
            messagebox.showerror(self._tr("start_error_title"), str(exc))
            return
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")

    def _toggle_auto_restart(self) -> None:
        if self._auto_restart_pending:
            return
        self._auto_restart_enabled = not self._auto_restart_enabled
        self._auto_restart_attempted = False
        if not self._auto_restart_enabled:
            self._auto_restart_retry_at = None
        enabled = self._auto_restart_enabled
        self.btn_auto_restart.configure(
            text=self._tr("auto_on" if enabled else "auto_off"),
            bg=OK if enabled else BG3,
            fg="#062218" if enabled else TEXT,
            activebackground=ACCENT if enabled else LINE,
            activeforeground="#062218" if enabled else TEXT,
            highlightbackground=OK if enabled else LINE,
        )
        self.footer_lbl.configure(text=self._tr("auto_enabled" if enabled else "auto_disabled"))

    def _begin_auto_restart(self) -> None:
        if self._auto_restart_pending:
            return
        self._auto_restart_pending = True
        self._auto_restart_result = None
        logger.warning("Auto-restart triggered after polling stalled")
        self.btn_auto_restart.configure(state="disabled")
        self.footer_lbl.configure(text=self._tr("auto_restarting"))
        threading.Thread(
            target=self._auto_restart_worker,
            name="save-mod-auto-restart",
            daemon=True,
        ).start()

    def _auto_restart_worker(self) -> None:
        try:
            logger.info("Auto-restart worker: requesting bot shutdown")
            if not self._runner.stop(timeout=30.0) or self._runner.is_running:
                self._auto_restart_result = "timeout"
                logger.error("Auto-restart aborted because the bot thread did not stop")
                return
            logger.info("Auto-restart worker: bot stopped; starting it again")
            self._runner.start()
            self._auto_restart_result = "started"
            logger.info("Auto-restart worker: new bot thread started")
        except Exception as exc:
            self._auto_restart_result = f"error:{type(exc).__name__}"
            logger.exception("Auto-restart worker failed")

    def _stop_bot(self) -> None:
        self._bot_should_run = False
        self._auto_restart_retry_at = None
        self._auto_restart_attempted = False
        self.btn_stop.configure(state="disabled")
        self.update_idletasks()
        self._runner.stop()
        self.btn_start.configure(state="normal")
        STATS.set_status("stopped")

    def _on_close(self) -> None:
        if self._runner.is_running:
            if not messagebox.askokcancel(self._tr("close_title"), self._tr("close_question")):
                return
            self._runner.stop()
        if self._lock is not None:
            self._lock.release()
        self.destroy()

    def _open_media(self) -> None:
        path = BASE_DIR / "media"
        path.mkdir(parents=True, exist_ok=True)
        os.startfile(path)  # type: ignore[attr-defined]

    def _open_data(self) -> None:
        path = BASE_DIR / "data"
        path.mkdir(parents=True, exist_ok=True)
        os.startfile(path)  # type: ignore[attr-defined]

    def _open_log(self) -> None:
        path = BASE_DIR / "bot.log"
        if not path.exists():
            path.write_text("", encoding="utf-8")
        os.startfile(path)  # type: ignore[attr-defined]

    def _status_visual(self, status: str, last_poll_at: float) -> tuple[str, str, str]:
        stale = bool(last_poll_at) and (time.time() - last_poll_at) > 45
        if status == "starting":
            return WARN, self._tr("status_starting"), WARN
        if status == "stopped":
            return MUTED, self._tr("status_stopped"), MUTED
        if status == "conflict":
            return DANGER, self._tr("status_conflict"), DANGER
        if stale:
            return WARN, self._tr("status_stale"), WARN
        return OK, self._tr("status_online"), OK

    def _fill_list(self, lb: tk.Listbox, events: list[RecentEvent]) -> None:
        lines = []
        for ev in events[:60]:
            label = _kind_label(ev.kind, self._language)
            lines.append(f"{_fmt_time(ev.at)}  {label:<11}  {self._translate_event_detail(ev.detail)}")
        self._set_list_lines(lb, lines)

    def _translate_event_detail(self, detail: str) -> str:
        if self._language == "ru":
            return detail
        replacements = (
            ("подключение отключено", "connection disabled"),
            ("подключение включено", "connection enabled"),
            ("одноразовое медиа", "one-time media"),
            ("правка текста", "message edited"),
            ("сообщ.", "messages"),
            ("удалено", "deleted"),
            ("сообщение", "message"),
            ("медиа", "media"),
            (" от ", " by "),
        )
        for source, target in replacements:
            detail = detail.replace(source, target)
        return detail

    def _fill_messages(self, text: tk.Text, items: list[RecentMessage]) -> None:
        self._visible_messages = items[:80]
        lines = []
        for msg in self._visible_messages:
            uid = str(msg.user_id) if msg.user_id is not None else "?"
            nick = (msg.name or self._tr("no_name")).replace("\n", " ").strip()
            if msg.username:
                nick = f"{nick} (@{msg.username})"
            lines.append(f"{_fmt_time(msg.at)}  {uid}  {nick} — {msg.text}")
        rendered = "\n".join(lines) if lines else self._tr("messages_empty")
        if text.get("1.0", "end-1c") == rendered:
            return

        text.configure(state="normal")
        text.delete("1.0", "end")
        if self._visible_messages:
            for index, msg in enumerate(self._visible_messages):
                uid = str(msg.user_id) if msg.user_id is not None else "?"
                nick = (msg.name or self._tr("no_name")).replace("\n", " ").strip()
                if msg.username:
                    nick = f"{nick} (@{msg.username})"
                text.insert("end", f"{_fmt_time(msg.at)}  ")
                if msg.user_id is None:
                    text.insert("end", uid)
                else:
                    text.insert("end", uid, ("user_id",))
                line_end = "\n" if index < len(self._visible_messages) - 1 else ""
                text.insert("end", f"  {nick} — {msg.text}{line_end}")
        else:
            text.insert("end", rendered)
        text.configure(state="disabled")

    def _open_message_folder_from_event(self, event):
        line_number = int(event.widget.index(f"@{event.x},{event.y}").split(".", 1)[0])
        message_index = line_number - 1
        if not 0 <= message_index < len(self._visible_messages):
            return "break"

        folder = self._media_dir / str(self._visible_messages[message_index].chat_id)
        if not folder.is_dir():
            messagebox.showinfo(
                self._tr("folder_missing_title"),
                self._tr("folder_missing"),
                parent=self,
            )
            return "break"

        try:
            os.startfile(str(folder))
        except OSError as exc:
            messagebox.showerror(self._tr("folder_open_error"), str(exc), parent=self)
        return "break"

    def _set_list_lines(self, lb: tk.Listbox, lines: list[str]) -> None:
        current = lb.get(0, "end")
        if tuple(current) == tuple(lines):
            return
        lb.delete(0, "end")
        for line in lines:
            lb.insert("end", line)
        if not lines:
            lb.insert("end", self._tr("list_empty"))

    def _refresh_log_view(self) -> None:
        if self.nb.select() != str(self.log_text.master):
            return
        now = time.monotonic()
        if now - self._last_log_refresh_at < 3.0:
            return
        self._last_log_refresh_at = now

        log_path = BASE_DIR / "bot.log"
        if not log_path.exists():
            return
        try:
            with open(log_path, "rb") as fh:
                fh.seek(0, os.SEEK_END)
                size = fh.tell()
                fh.seek(max(0, size - 40000))
                raw = fh.read().decode("utf-8", errors="replace")
        except OSError:
            return

        interesting = []
        for line in raw.splitlines()[-120:]:
            low = line.lower()
            if any(k in low for k in ("error", "critical", "warning", "saved", "delete", "connection", "online", "conflict", "stopped")):
                # strip token from telegram urls if present
                if "api.telegram.org/bot" in line:
                    parts = line.split("api.telegram.org/bot", 1)
                    rest = parts[1]
                    slash = rest.find("/")
                    line = parts[0] + "api.telegram.org/bot***/" + (rest[slash + 1:] if slash >= 0 else "")
                interesting.append(line)

        rendered = "\n".join(interesting[-80:])
        current = self.log_text.get("1.0", "end-1c")
        if current == rendered:
            return
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        for line in interesting[-80:]:
            tag = ()
            low = line.lower()
            if "error" in low or "critical" in low or "conflict" in low:
                tag = ("err",)
            elif "warning" in low:
                tag = ("warn",)
            elif "saved" in low or "online" in low:
                tag = ("ok",)
            self.log_text.insert("end", line + "\n", tag)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _tick(self) -> None:
        snap = STATS.snapshot()
        running = self._runner.is_running
        poll_reference = snap["last_poll_at"] or (snap["started_at"] if running else 0.0)
        polling_healthy = (
            running
            and snap["status"] == "online"
            and snap["last_poll_at"] >= snap["started_at"]
        )
        stale = (
            running
            and snap["status"] in {"starting", "online"}
            and bool(poll_reference)
            and (time.time() - poll_reference) > 45
        )
        color, label, _ = self._status_visual(snap["status"], poll_reference)
        if not running and snap["status"] != "stopped":
            label = self._tr("status_stopped")
            color = MUTED

        if self._auto_restart_result is not None:
            result = self._auto_restart_result
            self._auto_restart_result = None
            self._auto_restart_pending = False
            self.btn_auto_restart.configure(state="normal")
            if result == "started":
                self._auto_restart_retry_at = time.monotonic() + 60.0
                self.footer_lbl.configure(text=self._tr("auto_waiting"))
            else:
                self._auto_restart_retry_at = time.monotonic() + 60.0
                self.footer_lbl.configure(text=self._tr("auto_retry"))

        if polling_healthy:
            recovered = self._auto_restart_retry_at is not None
            self._auto_restart_attempted = False
            self._auto_restart_retry_at = None
            if recovered:
                self.footer_lbl.configure(text=self._tr("auto_restarted"))
        elif self._auto_restart_enabled and self._bot_should_run and not self._auto_restart_pending:
            retry_due = (
                self._auto_restart_retry_at is not None
                and time.monotonic() >= self._auto_restart_retry_at
            )
            first_attempt = stale and not self._auto_restart_attempted and self._auto_restart_retry_at is None
            runner_stopped = not running and self._auto_restart_retry_at is None
            if retry_due or first_attempt or runner_stopped:
                self._auto_restart_retry_at = None
                self._auto_restart_attempted = True
                self._begin_auto_restart()

        self.status_dot.configure(fg=color)
        self.status_lbl.configure(text=label, fg=color)
        uptime = _fmt_uptime(time.time() - snap["started_at"]) if running else "—"
        self.uptime_lbl.configure(text=uptime)
        self._update_poll_label(snap)

        self.card_msg.set(f"{snap['messages']:,}")
        self.card_media.set(f"{snap['media']:,}")
        self.card_del.set(f"{snap['deleted']:,}")
        self.card_edit.set(f"{snap['edits']:,}")
        self.card_err.set(f"{snap['errors']:,}")
        self.card_db.set(f"{snap['db_messages']:,}")

        self._fill_list(self.events_list, snap["recent"])
        self._fill_messages(self.messages_list, snap["recent_messages"])
        self._fill_list(self.errors_list, snap["recent_errors"])
        self._refresh_log_view()

        self.btn_start.configure(state="disabled" if running or self._auto_restart_pending else "normal")
        self.btn_stop.configure(state="normal" if running and not self._auto_restart_pending else "disabled")

        self.after(800, self._tick)


def _write_crash(exc: BaseException | None = None) -> None:
    import traceback

    path = BASE_DIR / "data" / "panel_crash.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write("\n" + "=" * 60 + "\n")
        fh.write(datetime.now().isoformat(timespec="seconds") + "\n")
        if exc is not None:
            fh.write(f"{type(exc).__name__}: {exc}\n")
        fh.write(traceback.format_exc())


def main() -> None:
    root = str(BASE_DIR)
    if root not in sys.path:
        sys.path.insert(0, root)
    try:
        setup_logging(console=False)
        app = SaveModPanel()
        app.mainloop()
    except Exception as exc:
        _write_crash(exc)
        try:
            root_tk = tk.Tk()
            root_tk.withdraw()
            messagebox.showerror("Save Mod — пиздец случился", f"{exc}\n\nПодробности: data\\panel_crash.log")
            root_tk.destroy()
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
