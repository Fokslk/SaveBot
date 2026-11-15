from __future__ import annotations

import logging
import math
from collections import deque
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
        "subtitle": "Панель управления", "overview": "ОБЗОР", "activity": "АКТИВНОСТЬ", "quick_access": "БЫСТРЫЙ ДОСТУП", "uptime": "Время работы", "chart_title": "Динамика активности", "chart_focus": "Подробно: {name}", "chart_all": "Все показатели", "card_graph": "График ↗", "card_selected": "На графике ✓", "chart_window": "Скорость в минуту · замер ≈ 10 сек · история до 4 минут", "chart_empty": "График появится после первого замера", "chart_messages": "Сообщения", "chart_media": "Медиа", "chart_errors": "Ошибки", "motion_on": "Анимация: вкл", "motion_off": "Анимация: выкл", "language_button": "EN", "start": "▶  Запустить",
        "stop": "■  Остановить", "auto_off": "Автоперезапуск: выкл", "auto_on": "Автоперезапуск: вкл",
        "media_button": "📁 Медиа", "log_button": "📄 Лог", "data_button": "🏠 База",
        "poll": "poll", "event": "событие", "messages": "Сообщения", "media": "Медиа",
        "deleted": "Удаления", "edits": "Правки", "errors": "Ошибки", "database": "В базе",
        "tab_events": "Действия", "tab_messages": "Сообщения", "tab_errors": "Ошибки", "tab_logs": "Логи",
        "footer_default": "Один экземпляр · Подробности в bot.log", "status_starting": "ЗАПУСК",
        "status_stopped": "ОСТАНОВЛЕН", "status_stopping": "ОСТАНОВКА", "stopped_notice": "Бот остановлен.", "stopping_notice": "Останавливаем бота…", "stop_failed": "Бот не остановился. Проверьте лог и попробуйте ещё раз.", "stop_wait": "Дождитесь завершения остановки бота.", "new_error": "Новая ошибка — подробности во вкладке «Ошибки».", "status_conflict": "КОНФЛИКТ", "status_stale": "ЗАСТОЙ",
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
        "subtitle": "Control panel", "overview": "OVERVIEW", "activity": "ACTIVITY", "quick_access": "QUICK ACCESS", "uptime": "Uptime", "chart_title": "Activity trends", "chart_focus": "Detail: {name}", "chart_all": "All metrics", "card_graph": "View graph ↗", "card_selected": "On graph ✓", "chart_window": "Per minute · sampled ~10 sec · up to 4 minutes", "chart_empty": "The graph will appear after the first sample", "chart_messages": "Messages", "chart_media": "Media", "chart_errors": "Errors", "motion_on": "Motion: on", "motion_off": "Motion: off", "language_button": "RU", "start": "▶  Start",
        "stop": "■  Stop", "auto_off": "Auto-restart: off", "auto_on": "Auto-restart: on",
        "media_button": "📁 Media", "log_button": "📄 Log", "data_button": "🏠 Database",
        "poll": "poll", "event": "event", "messages": "Messages", "media": "Media",
        "deleted": "Deleted", "edits": "Edits", "errors": "Errors", "database": "In database",
        "tab_events": "Activity", "tab_messages": "Messages", "tab_errors": "Errors", "tab_logs": "Logs",
        "footer_default": "Single instance · Details in bot.log", "status_starting": "STARTING",
        "status_stopped": "STOPPED", "status_stopping": "STOPPING", "stopped_notice": "Bot stopped.", "stopping_notice": "Stopping the bot…", "stop_failed": "The bot did not stop. Check the log and try again.", "stop_wait": "Please wait until the bot has stopped.", "new_error": "New error — see the Errors tab for details.", "status_conflict": "CONFLICT", "status_stale": "STALE",
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


def _mix_color(start: str, end: str, progress: float) -> str:
    """Interpolate two #rrggbb colors without relying on additional packages."""
    values = [round(int(start[i:i + 2], 16) * (1 - progress)
                    + int(end[i:i + 2], 16) * progress) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(values)


class MotionNotebook(tk.Frame):
    """A compact notebook with interruptible, optional directional transitions."""

    def __init__(self, master, motion):
        super().__init__(master, bg=BG, highlightthickness=0)
        self._motion = motion
        self._pages = []
        self._buttons = {}
        self._selected = None
        self._animation_id = None
        self._generation = 0
        self.header = tk.Frame(self, bg=BG)
        self.header.pack(side="top", fill="x")
        self.bind("<Configure>", self._resize)

    def add(self, page, text):
        holder = tk.Frame(self.header, bg=BG)
        holder.pack(side="left", padx=(0, 4))
        button = tk.Button(holder, text=text, command=lambda: self._select(page),
                           bg=BG2, fg=MUTED, activebackground=BG3, activeforeground=TEXT,
                           relief="flat", bd=0, padx=16, pady=8, cursor="hand2",
                           highlightthickness=1, highlightbackground=BG2,
                           highlightcolor=ACCENT2, font=("Segoe UI", 10, "bold"), takefocus=True)
        button.pack(fill="x")
        underline = tk.Frame(holder, bg=BG2, height=3)
        underline.pack(fill="x")
        self._pages.append(page)
        self._buttons[page] = (button, underline)
        if self._selected is None:
            self._selected = page
        self._show_selected()

    def tab(self, page, **options):
        if "text" in options:
            self._buttons[page][0].configure(text=options["text"])

    def select(self):
        return str(self._selected) if self._selected else ""

    def _geometry(self):
        return max(1, self.winfo_width()), max(1, self.winfo_height() - 44)

    def _show_selected(self):
        w, h = self._geometry()
        for page in self._pages:
            if page is self._selected:
                page.place(x=0, y=44, width=w, height=h)
            else:
                page.place_forget()
            button, line = self._buttons[page]
            chosen = page is self._selected
            button.configure(bg=CARD if chosen else BG2, fg=TEXT if chosen else MUTED,
                             highlightbackground=CARD if chosen else BG2)
            line.configure(bg=ACCENT if chosen else BG2)
        self.header.lift()

    def finish(self):
        self._generation += 1
        if self._animation_id is not None:
            self.after_cancel(self._animation_id)
            self._animation_id = None
        self._show_selected()

    def _resize(self, event):
        if event.widget is self:
            self.finish()

    def _select(self, page):
        if page is self._selected:
            return
        self.finish()
        previous = self._selected
        direction = 1 if self._pages.index(page) > self._pages.index(previous) else -1
        self._selected = page
        if not self._motion():
            self._show_selected()
            return
        width, height = self._geometry()
        if width <= 1 or height <= 1:
            self._show_selected()
            return
        for candidate in self._pages:
            button, line = self._buttons[candidate]
            chosen = candidate is page
            button.configure(bg=CARD if chosen else BG2, fg=TEXT if chosen else MUTED,
                             highlightbackground=CARD if chosen else BG2)
            line.configure(bg=ACCENT if chosen else BG2)
        page.place(x=direction * width, y=44, width=width, height=height)
        page.lift()
        self.header.lift()
        started, generation = time.monotonic(), self._generation
        def frame():
            if generation != self._generation:
                return
            progress = min(1.0, (time.monotonic() - started) / 0.22)
            eased = 1 - (1 - progress) ** 3
            page.place_configure(x=round(direction * width * (1 - eased)))
            previous.place_configure(x=round(-direction * width * eased))
            if progress < 1.0 and self._motion():
                self._animation_id = self.after(16, frame)
            else:
                self._animation_id = None
                self._show_selected()
        frame()


class NoticeLabel(tk.Label):
    """Highlight a changed message briefly; the message remains readable afterwards."""
    def __init__(self, master, motion, **kw):
        self._motion = motion
        self._notice_id = None
        self._notice_text = kw.get("text", "")
        super().__init__(master, **kw)

    def configure(self, *args, **kw):
        text = kw.get("text")
        changed = text is not None and text != self._notice_text
        if text is not None:
            self._notice_text = text
        result = super().configure(*args, **kw)
        if changed:
            if self._notice_id is not None:
                self.after_cancel(self._notice_id)
                self._notice_id = None
            if not self._motion():
                super().configure(fg=MUTED)
            else:
                started = time.monotonic()
                def frame():
                    progress = min(1.0, (time.monotonic() - started) / 0.55)
                    super(NoticeLabel, self).configure(fg=_mix_color(TEXT, MUTED, progress))
                    if progress < 1 and self._motion():
                        self._notice_id = self.after(30, frame)
                    else:
                        self._notice_id = None
                        super(NoticeLabel, self).configure(fg=MUTED)
                frame()
        return result

    config = configure

    def finish(self):
        if self._notice_id is not None:
            self.after_cancel(self._notice_id)
            self._notice_id = None
        super().configure(fg=MUTED)


class MetricCard(tk.Frame):
    """Metric values ease to their latest actual count; motion is optional."""

    def __init__(self, master, title: str, accent: str = ACCENT, motion=lambda: True, **kw):
        super().__init__(master, bg=CARD, highlightthickness=1, highlightbackground=LINE, **kw)
        self._motion = motion
        self._current = 0
        self._target = 0
        self._animation_id = None
        self._selection_id = None
        self._accent = accent
        self._selected = False
        self._selection_color = LINE
        self._click_callback = None
        self._stripe = tk.Frame(self, bg=accent, height=3)
        self._stripe.pack(fill="x")
        inner = tk.Frame(self, bg=CARD)
        self._inner = inner
        inner.pack(fill="both", expand=True, padx=14, pady=(10, 12))
        self.title_lbl = tk.Label(inner, text=title.upper(), bg=CARD, fg=MUTED,
                                  font=("Segoe UI", 9, "bold"), anchor="w")
        self.title_lbl.pack(fill="x")
        self.value_lbl = tk.Label(inner, text="0", bg=CARD, fg=TEXT,
                                  font=("Segoe UI", 23, "bold"), anchor="w")
        self.value_lbl.pack(fill="x", pady=(3, 0))

    def enable_detail(self, callback, label):
        self._click_callback = callback
        self.configure(cursor="hand2", takefocus=True, highlightcolor=self._accent)
        self.hint = tk.Label(self._inner, text=label, bg=CARD, fg=self._accent,
                             font=("Segoe UI", 8, "bold"), anchor="w", cursor="hand2")
        self.hint.pack(fill="x", pady=(3, 0))
        for widget in (self, self._stripe, self._inner, self.title_lbl, self.value_lbl, self.hint):
            widget.configure(cursor="hand2")
            widget.bind("<Button-1>", lambda event: self._click_callback())
        self.bind("<Return>", lambda event: self._click_callback())
        self.bind("<space>", lambda event: self._click_callback())

    def set_selection(self, selected, label):
        self._selected = selected
        self.hint.configure(text=label)
        if self._selection_id is not None:
            self.after_cancel(self._selection_id)
            self._selection_id = None
        start = self._selection_color
        end = self._accent if selected else LINE
        if not self._motion():
            self._selection_color = end
            self.configure(highlightbackground=end)
            return
        started = time.monotonic()
        def frame():
            progress = min(1.0, (time.monotonic() - started) / 0.22)
            eased = 1 - (1 - progress) ** 3
            self._selection_color = _mix_color(start, end, eased)
            self.configure(highlightbackground=self._selection_color)
            if progress < 1 and self._motion():
                self._selection_id = self.after(16, frame)
            else:
                self._selection_id = None
                self._selection_color = end
                self.configure(highlightbackground=end)
        frame()

    def set(self, value: str) -> None:
        target = int(value.replace(",", ""))
        if target == self._target and (self._motion() or self._current == target):
            return
        self._target = target
        if self._animation_id is not None:
            self.after_cancel(self._animation_id)
            self._animation_id = None
        if not self._motion():
            self._current = target
            self.value_lbl.configure(text=f"{target:,}")
            return
        start, started = self._current, time.monotonic()
        def frame():
            progress = min(1.0, (time.monotonic() - started) / 0.35)
            eased = 1 - (1 - progress) ** 3
            self._current = round(start + (target - start) * eased)
            self.value_lbl.configure(text=f"{self._current:,}")
            if progress < 1.0 and self._motion():
                self._animation_id = self.after(25, frame)
            else:
                self._current = target
                self.value_lbl.configure(text=f"{target:,}")
                self._animation_id = None
        frame()


class ActivityChart(tk.Frame):
    """Live rates derived only from observed counters; no invented history."""

    COLORS = (ACCENT2, ACCENT, DANGER)
    KEYS = ("messages", "media", "errors")

    def __init__(self, master, tr, motion):
        super().__init__(master, bg=CARD, highlightthickness=1, highlightbackground=LINE)
        self._tr = tr
        self._motion = motion
        self._reveal = 1.0
        self._reveal_id = None
        self.samples = deque(maxlen=24)
        self._baseline = None
        self._session = None
        self._hover_index = None
        self._filter = None
        self.on_filter_change = None
        top = tk.Frame(self, bg=CARD)
        top.pack(fill="x", padx=16, pady=(12, 0))
        self.title_label = tk.Label(top, bg=CARD, fg=TEXT, font=("Segoe UI", 12, "bold"), anchor="w")
        self.title_label.pack(side="left")
        self.reset_button = tk.Button(top, command=lambda: self.set_filter(None),
                                      bg=BG3, fg=TEXT, activebackground=LINE,
                                      activeforeground=TEXT, relief="flat", bd=0,
                                      padx=10, pady=4, font=("Segoe UI", 9, "bold"),
                                      cursor="hand2", takefocus=True,
                                      highlightthickness=1, highlightbackground=LINE,
                                      highlightcolor=ACCENT2)
        self.reset_button.pack(side="right")
        self.window_label = tk.Label(top, bg=CARD, fg=MUTED, font=("Segoe UI", 9), anchor="e")
        self.window_label.pack(side="right", padx=(0, 16))
        legend = tk.Frame(self, bg=CARD)
        legend.pack(fill="x", padx=16, pady=(5, 0))
        self.legend_labels = []
        for color in self.COLORS:
            label = tk.Label(legend, bg=CARD, fg=color, font=("Segoe UI", 9, "bold"), anchor="w")
            label.pack(side="left", padx=(0, 18))
            self.legend_labels.append(label)
        self.canvas = tk.Canvas(self, bg=CARD, height=122, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        self.canvas.bind("<Configure>", lambda event: self.draw())
        self.canvas.bind("<Motion>", self._on_hover)
        self.canvas.bind("<Leave>", self._on_leave)
        self.refresh_language()

    def refresh_language(self):
        self.title_label.configure(text=self._tr("chart_focus", name=self._tr("chart_" + self._filter))
                                   if self._filter else self._tr("chart_title"))
        self.reset_button.configure(text=self._tr("chart_all"),
                                    state="normal" if self._filter else "disabled",
                                    disabledforeground=MUTED)
        self.window_label.configure(text=self._tr("chart_window"))
        self._update_legend()
        self.draw()

    def set_filter(self, key):
        if key is not None and key not in self.KEYS:
            raise ValueError("Unknown chart metric")
        self._filter = key
        self._hover_index = None
        self.finish_motion()
        self.refresh_language()
        if self.on_filter_change:
            self.on_filter_change(key)

    def _update_legend(self):
        for i, (key, label) in enumerate(zip(self.KEYS, self.legend_labels)):
            suffix = ""
            if self._hover_index is not None and self.samples:
                unit = "min" if self._tr("language_button") == "RU" else "мин"
                suffix = f"  {self.samples[self._hover_index][1][i]:.1f}/{unit}"
            label.configure(text=f"{('●', '■', '◆')[i]}  {self._tr('chart_' + key)}{suffix}",
                            fg=self.COLORS[i] if self._filter in (None, key) else MUTED)

    def observe(self, snap, running):
        if not running:
            self._baseline = None
            return
        now = time.monotonic()
        current = tuple(snap[key] for key in self.KEYS)
        session = snap["started_at"]
        if self._session != session or self._baseline is None:
            # A new session has fresh counters; never join it to previous history.
            if self._session != session:
                self.samples.clear()
                self._hover_index = None
                self._session = session
                self._update_legend()
                self.draw()
            self._baseline = (now, current)
            return
        then, previous = self._baseline
        elapsed = now - then
        if any(a < b for a, b in zip(current, previous)):
            self.samples.clear()
            self._hover_index = None
            self._baseline = (now, current)
            self._update_legend()
            self.draw()
            return
        if elapsed >= 10.0:
            rates = tuple((a - b) * 60.0 / elapsed for a, b in zip(current, previous))
            self.samples.append((time.time(), rates))
            self._baseline = (now, current)
            self._hover_index = None
            self._update_legend()
            self._reveal_latest()

    def _reveal_latest(self):
        if self._reveal_id is not None:
            self.after_cancel(self._reveal_id)
            self._reveal_id = None
        if not self._motion() or len(self.samples) < 2:
            self._reveal = 1.0
            self.draw()
            return
        started = time.monotonic()
        def frame():
            progress = min(1.0, (time.monotonic() - started) / 0.28)
            self._reveal = 1 - (1 - progress) ** 3
            self.draw()
            if progress < 1 and self._motion():
                self._reveal_id = self.after(16, frame)
            else:
                self._reveal = 1.0
                self._reveal_id = None
                self.draw()
        frame()

    def finish_motion(self):
        if self._reveal_id is not None:
            self.after_cancel(self._reveal_id)
            self._reveal_id = None
        self._reveal = 1.0
        self.draw()

    def _on_hover(self, event):
        if not self.samples:
            return
        width = max(1, self.canvas.winfo_width())
        left, right = 38, width - 12
        if right <= left:
            return
        if len(self.samples) == 1:
            index = 0
        else:
            index = round((event.x - left) / (right - left) * (len(self.samples) - 1))
            index = max(0, min(len(self.samples) - 1, index))
        if index != self._hover_index:
            self._hover_index = index
            self._update_legend()
            self.draw()

    def _on_leave(self, event):
        self._hover_index = None
        self._update_legend()
        self.draw()

    def draw(self):
        canvas = self.canvas
        canvas.delete("all")
        width, height = canvas.winfo_width(), canvas.winfo_height()
        if width < 100 or height < 60:
            return
        left, right, top, bottom = 38, width - 12, 8, height - 25
        if not self.samples:
            canvas.create_text(width / 2, height / 2, text=self._tr("chart_empty"),
                               fill=MUTED, font=("Segoe UI", 10))
            return
        visible_indices = [i for i, key in enumerate(self.KEYS) if self._filter in (None, key)]
        maximum = max(values[i] for _, values in self.samples for i in visible_indices)
        # Four whole-number intervals; zero remains visible for count rates.
        step = max(1, math.ceil(maximum / 4))
        ceiling = step * 4
        for i in range(5):
            y = bottom - (bottom - top) * i / 4
            canvas.create_line(left, y, right, y, fill=LINE)
            canvas.create_text(left - 8, y, text=str(i * step), fill=MUTED,
                               anchor="e", font=("Segoe UI", 8))
        count = len(self.samples)
        def xy(index, value):
            x = left + ((right - left) * index / (count - 1) if count > 1 else (right - left) / 2)
            y = bottom - (bottom - top) * value / ceiling
            return x, y
        if self._hover_index is not None:
            x, _ = xy(self._hover_index, 0)
            canvas.create_line(x, top, x, bottom, fill=MUTED, dash=(2, 3))
        for series in visible_indices:
            color = self.COLORS[series]
            coords = [coord for i, (_, values) in enumerate(self.samples) for coord in xy(i, values[series])]
            if count > 1:
                if self._reveal < 1.0:
                    x0, y0, x1, y1 = coords[-4:]
                    partial = coords[:-2] + [x0 + (x1 - x0) * self._reveal,
                                               y0 + (y1 - y0) * self._reveal]
                    canvas.create_line(*partial, fill=color, width=2)
                else:
                    canvas.create_line(*coords, fill=color, width=2)
            for i, (_, values) in enumerate(self.samples):
                if i == count - 1 and count > 1 and self._reveal < 1.0:
                    continue
                x, y = xy(i, values[series])
                # Unique shape for each series, not color alone.
                r = 3
                if series == 0:
                    canvas.create_oval(x-r, y-r, x+r, y+r, fill=color, outline=CARD)
                elif series == 1:
                    canvas.create_rectangle(x-r, y-r, x+r, y+r, fill=color, outline=CARD)
                else:
                    canvas.create_polygon(x, y-r-1, x+r+1, y, x, y+r+1, x-r-1, y, fill=color, outline=CARD)
        first = datetime.fromtimestamp(self.samples[0][0]).strftime("%H:%M:%S")
        last = datetime.fromtimestamp(self.samples[-1][0]).strftime("%H:%M:%S")
        if count == 1:
            canvas.create_text((left + right) / 2, height - 6, text=first, fill=MUTED,
                               font=("Consolas", 8), anchor="s")
        else:
            canvas.create_text(left, height - 6, text=first, fill=MUTED, font=("Consolas", 8), anchor="sw")
            canvas.create_text(right, height - 6, text=last, fill=MUTED, font=("Consolas", 8), anchor="se")
        if self._hover_index is not None:
            ts = datetime.fromtimestamp(self.samples[self._hover_index][0]).strftime("%H:%M:%S")
            canvas.create_text((left + right) / 2, height - 6, text=ts, fill=TEXT,
                               font=("Consolas", 8, "bold"), anchor="s")


class SaveModPanel(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Save Mod")
        self.geometry("1180x900")
        self.minsize(900, 760)
        self.configure(bg=BG)
        self._language = "ru"
        self._motion_enabled = True
        self._status_color = MUTED
        self._status_kind = "stopped"
        self._stop_pending = False
        self._stop_result = None
        self._error_session = None
        self._last_error_count = 0
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
        self.after(80, self._animate_status)
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
        button = tk.Button(
            parent, text=text, command=command, bg=bg, fg=fg,
            activebackground="#8ae6d0" if primary else LINE,
            activeforeground=fg, disabledforeground="#8291a3",
            relief="flat", borderwidth=0, highlightthickness=1,
            highlightbackground=bg if primary else LINE, highlightcolor=ACCENT2,
            font=("Segoe UI", 10, "bold"), padx=14, pady=8, cursor="hand2",
            takefocus=True,
        )
        button._normal_bg = bg
        button._hovered = False
        button._hover_id = None
        def animate_color(target):
            if button._hover_id is not None:
                button.after_cancel(button._hover_id)
                button._hover_id = None
            current = button.cget("bg")
            if not self._motion_enabled or not current.startswith("#") or len(current) != 7:
                button.configure(bg=target)
                return
            started = time.monotonic()
            def frame():
                progress = min(1.0, (time.monotonic() - started) / 0.16)
                eased = 1 - (1 - progress) ** 3
                button.configure(bg=_mix_color(current, target, eased))
                if progress < 1 and self._motion_enabled:
                    button._hover_id = button.after(16, frame)
                else:
                    button._hover_id = None
                    button.configure(bg=target)
            frame()
        button._animate_color = animate_color
        def enter(event):
            button._hovered = True
            if button.cget("state") != "disabled":
                animate_color("#8ae6d0" if primary or button._normal_bg == OK else "#34485c")
        def leave(event):
            button._hovered = False
            animate_color(button._normal_bg)
        button.bind("<Enter>", enter)
        button.bind("<Leave>", leave)
        return button

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
        self.btn_auto_restart._normal_bg = OK
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
        self.btn_motion = self._button(shortcuts, self._tr("motion_on"), self._toggle_motion)
        self.btn_motion.pack(side="right")

        overview = tk.Frame(self, bg=BG)
        overview.pack(fill="x", padx=24, pady=(20, 8))
        self.overview_title = tk.Label(overview, text=self._tr("overview"), bg=BG, fg=MUTED,
                                       font=("Segoe UI", 9, "bold"), anchor="w")
        self.overview_title.pack(side="left")
        metrics = tk.Frame(self, bg=BG)
        metrics.pack(fill="x", padx=24)
        for i in range(6):
            metrics.columnconfigure(i, weight=1, uniform="metrics")
        self.card_msg = MetricCard(metrics, self._tr("messages"), ACCENT2, motion=lambda: self._motion_enabled)
        self.card_media = MetricCard(metrics, self._tr("media"), ACCENT, motion=lambda: self._motion_enabled)
        self.card_del = MetricCard(metrics, self._tr("deleted"), WARN, motion=lambda: self._motion_enabled)
        self.card_edit = MetricCard(metrics, self._tr("edits"), "#d4afff", motion=lambda: self._motion_enabled)
        self.card_err = MetricCard(metrics, self._tr("errors"), DANGER, motion=lambda: self._motion_enabled)
        self.card_db = MetricCard(metrics, self._tr("database"), "#9badc1", motion=lambda: self._motion_enabled)
        for i, card in enumerate((self.card_msg, self.card_media, self.card_del,
                                   self.card_edit, self.card_err, self.card_db)):
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0))

        self.chart = ActivityChart(self, self._tr, lambda: self._motion_enabled)
        self.chart.pack(fill="x", padx=24, pady=(16, 0))
        self._detail_cards = {"messages": self.card_msg, "media": self.card_media,
                              "errors": self.card_err}
        for key, card in self._detail_cards.items():
            card.enable_detail(lambda k=key: self._focus_metric(k), self._tr("card_graph"))
        self.chart.on_filter_change = self._sync_selected_cards

        section = tk.Frame(self, bg=BG)
        section.pack(fill="x", padx=24, pady=(20, 8))
        self.activity_title = tk.Label(section, text=self._tr("activity"), bg=BG, fg=MUTED,
                                      font=("Segoe UI", 9, "bold"), anchor="w")
        self.activity_title.pack(side="left")
        footer = tk.Frame(self, bg=BG2, height=34, highlightthickness=1, highlightbackground=LINE)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)
        self.footer_lbl = NoticeLabel(footer, lambda: self._motion_enabled, text=self._tr("footer_default"), bg=BG2, fg=MUTED,
                                   font=("Segoe UI", 9), anchor="w")
        self.footer_lbl.pack(fill="both", expand=True, padx=24)
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=24, pady=(0, 16))
        self.nb = MotionNotebook(body, lambda: self._motion_enabled)
        self.nb.pack(fill="both", expand=True)
        self.events_list = self._make_list_tab(self._tr("tab_events"))
        self.messages_list = self._make_messages_tab(self._tr("tab_messages"))
        self.errors_list = self._make_list_tab(self._tr("tab_errors"))
        self.log_text = self._make_log_tab(self._tr("tab_logs"))
        self._update_poll_label(STATS.snapshot())

    def _tr(self, key: str, **values: str) -> str:
        return UI_TEXT[self._language][key].format(**values)

    def _focus_metric(self, key: str) -> None:
        self.chart.set_filter(None if self.chart._filter == key else key)

    def _sync_selected_cards(self, selected: str | None) -> None:
        for key, card in self._detail_cards.items():
            active = key == selected
            card.set_selection(active, self._tr("card_selected" if active else "card_graph"))

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
        self.btn_motion.configure(text=self._tr("motion_on" if self._motion_enabled else "motion_off"))
        self.chart.refresh_language()
        self._sync_selected_cards(self.chart._filter)
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

    def _toggle_motion(self) -> None:
        self._motion_enabled = not self._motion_enabled
        self.btn_motion.configure(text=self._tr("motion_on" if self._motion_enabled else "motion_off"))
        if not self._motion_enabled:
            self.nb.finish()
            self.chart.finish_motion()
            self._sync_selected_cards(self.chart._filter)
            self.footer_lbl.finish()
            self.status_dot.configure(fg=self._status_color)
            for card in (self.card_msg, self.card_media, self.card_del,
                         self.card_edit, self.card_err, self.card_db):
                card.set(str(card._target))

    def _animate_status(self) -> None:
        if self._motion_enabled and self._status_kind in {"starting", "stopping"}:
            # A gentle pulse communicates work in progress; online remains still.
            amount = 0.72 + 0.28 * (0.5 + 0.5 * math.sin(time.monotonic() * 2.0))
            rgb = [round(int(BG2[i:i+2], 16) * (1 - amount) + int(WARN[i:i+2], 16) * amount)
                   for i in (1, 3, 5)]
            self.status_dot.configure(fg="#%02x%02x%02x" % tuple(rgb))
        else:
            self.status_dot.configure(fg=self._status_color)
        self.after(80, self._animate_status)

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
        self._status_kind = "starting"
        self._status_color = WARN
        self.status_lbl.configure(text=self._tr("status_starting"), fg=WARN)
        self.status_dot.configure(fg=WARN)

    def _toggle_auto_restart(self) -> None:
        if self._auto_restart_pending:
            return
        self._auto_restart_enabled = not self._auto_restart_enabled
        self._auto_restart_attempted = False
        if not self._auto_restart_enabled:
            self._auto_restart_retry_at = None
        enabled = self._auto_restart_enabled
        self.btn_auto_restart._normal_bg = OK if enabled else BG3
        if self.btn_auto_restart._hover_id is not None:
            self.btn_auto_restart.after_cancel(self.btn_auto_restart._hover_id)
            self.btn_auto_restart._hover_id = None
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
        if self._stop_pending or self._auto_restart_pending:
            return
        self._bot_should_run = False
        self._auto_restart_retry_at = None
        self._auto_restart_attempted = False
        self._stop_pending = True
        self._stop_result = None
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="disabled")
        self._status_kind = "stopping"
        self._status_color = WARN
        self.status_lbl.configure(text=self._tr("status_stopping"), fg=WARN)
        self.status_dot.configure(fg=WARN)
        self.footer_lbl.configure(text=self._tr("stopping_notice"))
        def worker():
            try:
                self._stop_result = bool(self._runner.stop())
            except Exception:
                logger.exception("Bot stop failed")
                self._stop_result = False
        threading.Thread(target=worker, name="save-mod-stop", daemon=True).start()

    def _on_close(self) -> None:
        if self._stop_pending:
            messagebox.showinfo(self._tr("close_title"), self._tr("stop_wait"), parent=self)
            return
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
        if self._stop_pending and self._stop_result is not None:
            stopped = self._stop_result
            self._stop_pending = False
            self._stop_result = None
            self.footer_lbl.configure(text=self._tr("stopped_notice" if stopped else "stop_failed"))
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

        self._status_kind = snap["status"] if running else "stopped"
        if self._stop_pending:
            self._status_kind = "stopping"
            color, label = WARN, self._tr("status_stopping")
        self._status_color = color
        self.status_dot.configure(fg=color)
        self.status_lbl.configure(text=label, fg=color)
        uptime = _fmt_uptime(time.time() - snap["started_at"]) if running else "—"
        self.uptime_lbl.configure(text=uptime)
        self._update_poll_label(snap)
        self.chart.observe(snap, running)
        if snap["started_at"] != self._error_session:
            self._error_session = snap["started_at"]
            self._last_error_count = 0
        if snap["errors"] > self._last_error_count and not self._auto_restart_pending and not self._stop_pending:
            self.footer_lbl.configure(text=self._tr("new_error"))
        self._last_error_count = snap["errors"]

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

        self.btn_start.configure(state="disabled" if running or self._auto_restart_pending or self._stop_pending else "normal")
        self.btn_stop.configure(state="normal" if running and not self._auto_restart_pending and not self._stop_pending else "disabled")

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
