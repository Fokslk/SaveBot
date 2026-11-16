"""Save Mod — desktop control panel.

Requires PySide6-Essentials. The bot and storage modules remain unchanged.
"""
from __future__ import annotations

import logging
import math
import os
import re
import sys
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import (Qt, QTimer, QUrl, QVariantAnimation, QEasingCurve,
                            QPropertyAnimation, QPointF)
from PySide6.QtGui import QColor, QDesktopServices, QPainter, QPen, QFont
from PySide6.QtWidgets import (QApplication, QFrame, QGraphicsOpacityEffect, QGridLayout,
                               QHBoxLayout, QHeaderView, QLabel, QListWidget, QListWidgetItem,
                               QMainWindow, QMessageBox, QPlainTextEdit, QPushButton, QSizePolicy,
                               QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from bot.config import BASE_DIR, load_config
from bot.instance import InstanceLock, already_running_message, kill_foreign_bots
from bot.runtime_stats import STATS
from bot.runner import BotRunner, setup_logging

logger = logging.getLogger(__name__)
BG = '#10131b'
SURFACE = '#191e2a'
BORDER = '#303747'
TEXT = '#f3f4f8'
MUTED = '#a5afc2'
PURPLE = '#baacff'
BLUE = '#8abfff'
MINT = '#83dfc1'
RED = '#ff9797'
AMBER = '#f0c986'
SERIES = (('messages', BLUE, '●'), ('media', MINT, '■'), ('errors', RED, '◆'))

WORDS = {
 'ru': {
  'overview':'Обзор', 'activity':'События', 'messages':'Сообщения', 'media':'Медиа', 'errors':'Ошибки', 'logs':'Логи',
  'workspace':'ПАНЕЛЬ', 'shortcuts':'БЫСТРЫЙ ДОСТУП', 'media_dir':'Папка медиа', 'log_file':'Файл лога', 'data_dir':'Папка базы',
  'tagline':'Панель бота', 'overview_sub':'Состояние бота и активность за текущий сеанс',
  'activity_sub':'Последние сохранения и действия', 'messages_sub':'Нажмите на ID, чтобы открыть папку переписки',
  'errors_sub':'Последние ошибки текущего сеанса', 'logs_sub':'Последние важные строки из bot.log',
  'start':'▶   Запустить', 'stop':'■   Остановить', 'auto_on':'Автоперезапуск: вкл', 'auto_off':'Автоперезапуск: выкл',
  'motion_on':'Анимация: вкл', 'motion_off':'Анимация: выкл', 'language':'EN', 'total_msg':'Сообщения',
  'total_media':'Медиа', 'total_deleted':'Удаления', 'total_edits':'Правки', 'total_errors':'Ошибки', 'total_db':'В базе',
  'this_session':'за сеанс', 'stored':'всего записей', 'chart':'Динамика активности', 'chart_sub':'Событий в минуту · замер примерно раз в 10 секунд',
  'chart_wait':'График появится после первого замера', 'recent':'Последние действия', 'view_all':'Все события  →',
  'empty_events':'Пока нет событий', 'empty_messages':'Пока нет сообщений', 'empty_errors':'Пока нет ошибок', 'empty_logs':'Записей пока нет',
  'status_stopped':'Остановлен', 'status_starting':'Запускается', 'status_online':'Работает', 'status_conflict':'Конфликт',
  'status_stale':'Нет ответа', 'status_stopping':'Останавливается', 'status_restart':'Перезапускается', 'uptime':'Время работы',
  'poll':'Последний опрос', 'event':'Последнее событие', 'ago_s':'{n} с назад', 'ago_m':'{n} мин назад', 'ago_h':'{n} ч назад',
  'time':'ВРЕМЯ', 'user_id':'ID', 'name':'ОТПРАВИТЕЛЬ', 'message':'СООБЩЕНИЕ', 'no_name':'без имени',
  'error_title':'Ошибка', 'config_error':'Ошибка конфигурации', 'start_error':'Не удалось запустить бота',
  'stopped_notice':'Бот остановлен.', 'stopping_notice':'Останавливаем бота…', 'stop_failed':'Не удалось остановить бота. Проверьте лог.',
  'restart_notice':'Соединение не отвечает. Перезапускаем бота…', 'restart_wait':'Перезапущен, ожидаем связь с сервером.',
  'restart_retry':'Перезапуск не удался. Следующая попытка через 60 секунд.', 'restart_ok':'Соединение восстановлено.',
  'auto_enabled':'Автоперезапуск включён.', 'auto_disabled':'Автоперезапуск выключен.',
  'conflict_notice':'Уже запущено в другом окне.', 'folder_missing':'Папки с медиа для этой переписки пока нет.',
  'open_failed':'Не удалось открыть путь.', 'close_title':'Закрыть Save Mod?', 'close_question':'Бот будет остановлен перед закрытием панели.',
  'busy_close':'Дождитесь завершения текущей операции.', 'single':'Один экземпляр · подробности в bot.log', 'event_save':'Сохранено',
  'event_media':'Медиа', 'event_deleted':'Удалено', 'event_edit':'Изменено', 'event_error':'Ошибка', 'event_connection':'Связь', 'event_update':'Обновление',
 },
 'en': {
  'overview':'Overview', 'activity':'Activity', 'messages':'Messages', 'media':'Media', 'errors':'Errors', 'logs':'Logs',
  'workspace':'WORKSPACE', 'shortcuts':'QUICK ACCESS', 'media_dir':'Media folder', 'log_file':'Log file', 'data_dir':'Data folder',
  'tagline':'Bot dashboard', 'overview_sub':'Bot status and activity for the current session',
  'activity_sub':'Recent saves and actions', 'messages_sub':'Click an ID to open its conversation folder',
  'errors_sub':'Recent errors in the current session', 'logs_sub':'Recent important lines from bot.log',
  'start':'▶   Start', 'stop':'■   Stop', 'auto_on':'Auto-restart: on', 'auto_off':'Auto-restart: off',
  'motion_on':'Motion: on', 'motion_off':'Motion: off', 'language':'RU', 'total_msg':'Messages',
  'total_media':'Media', 'total_deleted':'Deleted', 'total_edits':'Edits', 'total_errors':'Errors', 'total_db':'In database',
  'this_session':'this session', 'stored':'total records', 'chart':'Activity over time', 'chart_sub':'Events per minute · sampled about every 10 seconds',
  'chart_wait':'The chart appears after the first sample', 'recent':'Recent activity', 'view_all':'All activity  →',
  'empty_events':'No activity yet', 'empty_messages':'No messages yet', 'empty_errors':'No errors yet', 'empty_logs':'No log entries yet',
  'status_stopped':'Stopped', 'status_starting':'Starting', 'status_online':'Online', 'status_conflict':'Conflict',
  'status_stale':'Not responding', 'status_stopping':'Stopping', 'status_restart':'Restarting', 'uptime':'Uptime',
  'poll':'Last poll', 'event':'Last event', 'ago_s':'{n}s ago', 'ago_m':'{n}m ago', 'ago_h':'{n}h ago',
  'time':'TIME', 'user_id':'ID', 'name':'SENDER', 'message':'MESSAGE', 'no_name':'unknown',
  'error_title':'Error', 'config_error':'Configuration error', 'start_error':'Could not start the bot',
  'stopped_notice':'Bot stopped.', 'stopping_notice':'Stopping the bot…', 'stop_failed':'Could not stop the bot. Check the log.',
  'restart_notice':'Connection is unresponsive. Restarting the bot…', 'restart_wait':'Restarted; waiting for the connection.',
  'restart_retry':'Restart failed. Retrying in 60 seconds.', 'restart_ok':'Connection restored.',
  'auto_enabled':'Auto-restart enabled.', 'auto_disabled':'Auto-restart disabled.',
  'conflict_notice':'Already running in another window.', 'folder_missing':'No media folder exists for this conversation yet.',
  'open_failed':'Could not open the path.', 'close_title':'Close Save Mod?', 'close_question':'The bot will stop before the panel closes.',
  'busy_close':'Please wait for the current operation to finish.', 'single':'Single instance · details in bot.log', 'event_save':'Saved',
  'event_media':'Media', 'event_deleted':'Deleted', 'event_edit':'Edited', 'event_error':'Error', 'event_connection':'Connection', 'event_update':'Update',
 }
}

STYLESHEET = '''
QWidget { color: #f3f4f8; background: transparent; font-family: "Segoe UI", "Arial"; font-size: 14px; }
QMainWindow, QWidget#root { background: #10131b; }
QFrame#sidebar { background: #171b26; border-right: 1px solid #303747; }
QFrame#panel { background: #191e2a; border: 1px solid #303747; border-radius: 12px; }
QFrame#metric { background: #191e2a; border: 1px solid #303747; border-radius: 12px; }
QFrame#metric:hover { border: 1px solid #675e9b; }
QLabel#brand { font-size: 19px; font-weight: 750; letter-spacing: 1px; }
QLabel#brandmark { background: #bbaeff; color: #17122d; border-radius: 10px; font-size: 19px; font-weight: 800; }
QLabel#eyebrow { color: #a5afc2; font-size: 11px; font-weight: 700; letter-spacing: 1px; }
QLabel#muted { color: #a5afc2; }
QLabel#heading { font-size: 27px; font-weight: 750; }
QLabel#section { font-size: 16px; font-weight: 700; }
QLabel#metricName { color: #bac2d1; font-size: 13px; font-weight: 600; }
QLabel#metricValue { color: #f3f4f8; font-size: 26px; font-weight: 750; }
QLabel#tiny { color: #a5afc2; font-size: 12px; }
QLabel#status { border-radius: 12px; padding: 7px 12px; font-weight: 700; }
QPushButton { background: #242a39; border: 1px solid #374052; border-radius: 8px; padding: 9px 14px; font-weight: 600; min-height: 20px; }
QPushButton:hover { background: #30394b; border-color: #67718c; }
QPushButton:pressed { background: #3b455a; }
QPushButton:focus { border: 1px solid #baacff; }
QPushButton:disabled { color: #8390a3; background: #202533; border-color: #303747; }
QPushButton#primary { background: #baacff; color: #201a36; border: 1px solid #baacff; }
QPushButton#primary:hover { background: #d0c6ff; }
QPushButton#primary:disabled { background: #34334b; color: #a2a1b7; border-color: #34334b; }
QPushButton#nav { text-align: left; background: transparent; border: 1px solid transparent; color: #b7c0d1; padding: 10px 12px; }
QPushButton#nav:hover { background: #242a39; color: #f3f4f8; }
QPushButton#nav:checked { background: #322d4e; border: 1px solid #534a78; color: #eee9ff; }
QPushButton#link { background: transparent; color: #c5baff; border: 0px; padding: 2px; }
QPushButton#link:hover { color: white; }
QListWidget, QTableWidget, QPlainTextEdit { background: #191e2a; border: 0px; color: #e8edf5; outline: 0; }
QListWidget::item { padding: 10px 8px; border-bottom: 1px solid #2c3341; }
QListWidget::item:selected, QTableWidget::item:selected { background: #373350; color: white; }
QTableWidget { gridline-color: #303747; selection-background-color: #373350; }
QTableWidget::item { padding: 8px; }
QHeaderView::section { background: #202635; color: #a5afc2; border: 0; border-bottom: 1px solid #303747; padding: 10px 8px; font-weight: 700; font-size: 11px; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 4px 0; }
QScrollBar::handle:vertical { background: #495269; border-radius: 5px; min-height: 25px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
'''


def label(text='', name=None):
    w = QLabel(text)
    if name: w.setObjectName(name)
    return w

def button(text='', name=None, cb=None):
    w = QPushButton(text)
    if name: w.setObjectName(name)
    w.setCursor(Qt.PointingHandCursor)
    if cb: w.clicked.connect(cb)
    return w

def card():
    w = QFrame(); w.setObjectName('panel')
    return w

def clock(ts):
    return datetime.fromtimestamp(ts).strftime('%H:%M:%S') if ts else '—'

def uptime(sec):
    sec = max(0, int(sec)); h, rem = divmod(sec, 3600); m, s = divmod(rem, 60)
    return f'{h}:{m:02}:{s:02}' if h else f'{m:02}:{s:02}'

class Metric(QFrame):
    def __init__(self, name, caption, accent, motion):
        super().__init__(); self.setObjectName('metric'); self._motion = motion; self._value = 0; self._target = 0
        self.setMinimumHeight(105)
        lay = QVBoxLayout(self); lay.setContentsMargins(16, 12, 16, 12); lay.setSpacing(3)
        top = QHBoxLayout(); self.title = label(name, 'metricName'); top.addWidget(self.title); top.addStretch()
        mark = label('●'); mark.setStyleSheet(f'color: {accent}; font-size: 12px;'); top.addWidget(mark)
        self.value = label('0', 'metricValue'); self.caption = label(caption, 'tiny')
        lay.addLayout(top); lay.addWidget(self.value); lay.addWidget(self.caption)
        self.anim = QVariantAnimation(self); self.anim.setDuration(280); self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.valueChanged.connect(self._update_value)
    def _update_value(self, v):
        self._value = round(v); self.value.setText(f'{self._value:,}')
    def set_value(self, n):
        n = int(n)
        if self._target == n: return
        self._target = n; self.anim.stop()
        if not self._motion(): self._update_value(n); return
        self.anim.setStartValue(self._value); self.anim.setEndValue(n); self.anim.start()
    def finish(self):
        self.anim.stop(); self._update_value(self._target)

class ActivityChart(QWidget):
    """10-second sampled rates based on the real counters, up to 24 samples."""
    def __init__(self, text, motion):
        super().__init__(); self._text=text; self._motion=motion
        self.samples=deque(maxlen=24); self.baseline=None; self.session=None; self.hover=None; self.hover_changed=None
        self.setMinimumHeight(160); self.setMouseTracking(True)
        self.reveal=1.; self.anim=QVariantAnimation(self); self.anim.setDuration(300); self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.valueChanged.connect(self._on_reveal)
    def _on_reveal(self, v): self.reveal=float(v); self.update()
    def finish(self): self.anim.stop(); self.reveal=1.; self.update()
    def observe(self, snap, running):
        if not running: self.baseline=None; return
        now=time.monotonic(); values=tuple(snap[k] for k,_,_ in SERIES)
        if snap['started_at'] != self.session:
            self.session=snap['started_at']; self.samples.clear(); self.baseline=None; self.hover=None; self.anim.stop(); self.reveal=1.
            if self.hover_changed:self.hover_changed(None)
            self.update()
        if self.baseline is None: self.baseline=(now, values); return
        previous, old=self.baseline; elapsed=now-previous
        if any(n<o for n,o in zip(values,old)):
            self.samples.clear(); self.baseline=(now,values); self.hover=None; self.anim.stop(); self.reveal=1.
            if self.hover_changed:self.hover_changed(None)
            self.update(); return
        if elapsed >= 10:
            self.samples.append((time.time(), tuple((n-o)*60/elapsed for n,o in zip(values,old))))
            self.baseline=(now,values); self.hover=None; self.anim.stop()
            if self.hover_changed:self.hover_changed(None)
            if self._motion() and len(self.samples)>1:
                self.anim.setStartValue(0.0); self.anim.setEndValue(1.0); self.anim.start()
            else: self.reveal=1.; self.update()
    def mouseMoveEvent(self, event):
        if not self.samples: return
        left, right=42, self.width()-16; n=len(self.samples)
        if right <= left: return
        if n == 1:
            self.hover=0
        else:
            first,last=self.samples[0][0],self.samples[-1][0]
            ratio=max(0.,min(1.,(event.position().x()-left)/(right-left)))
            if last > first:
                target=first + ratio * (last-first)
                self.hover=min(range(n),key=lambda i:abs(self.samples[i][0]-target))
            else:
                self.hover=max(0,min(n-1,round(ratio*(n-1))))
        if self.hover_changed: self.hover_changed(self.hover)
        self.update()
    def leaveEvent(self,event):
        self.hover=None
        if self.hover_changed:self.hover_changed(None)
        self.update(); super().leaveEvent(event)
    def paintEvent(self, event):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w,h=self.width(),self.height(); left,right,top,bottom=42,w-16,10,h-25
        p.setFont(QFont('Segoe UI',9))
        if not self.samples:
            p.setPen(QColor(MUTED)); p.drawText(self.rect(), Qt.AlignCenter, self._text('chart_wait')); return
        maximum=max(v for _,vals in self.samples for v in vals); step=max(1,math.ceil(maximum/4)); ceiling=step*4
        for i in range(5):
            y=bottom-(bottom-top)*i/4
            p.setPen(QPen(QColor('#333b4b'),1)); p.drawLine(QPointF(left,y),QPointF(right,y))
            p.setPen(QColor(MUTED)); p.drawText(0,round(y)-8,left-8,16,Qt.AlignRight|Qt.AlignVCenter,str(i*step))
        n=len(self.samples)
        def pos(i,v):
            if n==1: fraction=.5
            elif self.samples[-1][0]>self.samples[0][0]:
                fraction=(self.samples[i][0]-self.samples[0][0])/(self.samples[-1][0]-self.samples[0][0])
            else: fraction=i/(n-1)
            return QPointF(left + (right-left)*fraction, bottom-(bottom-top)*v/ceiling)
        if self.hover is not None:
            x=pos(self.hover,0).x(); p.setPen(QPen(QColor('#788399'),1,Qt.DashLine)); p.drawLine(QPointF(x,top),QPointF(x,bottom))
        for j,(_,col,shape) in enumerate(SERIES):
            p.setPen(QPen(QColor(col),2)); coords=[pos(i,vals[j]) for i,(_,vals) in enumerate(self.samples)]
            for i in range(1,n):
                end=coords[i]
                if i==n-1 and self.reveal<1:
                    a=coords[i-1]; end=QPointF(a.x()+(end.x()-a.x())*self.reveal,a.y()+(end.y()-a.y())*self.reveal)
                p.drawLine(coords[i-1],end)
            p.setBrush(QColor(col))
            for i,point in enumerate(coords):
                if i==n-1 and n>1 and self.reveal<1: continue
                x,y=point.x(),point.y(); r=3
                if j==0: p.drawEllipse(point,r,r)
                elif j==1: p.drawRect(round(x-r),round(y-r),2*r,2*r)
                else:
                    from PySide6.QtGui import QPolygonF
                    p.drawPolygon(QPolygonF([QPointF(x,y-r-1),QPointF(x+r+1,y),QPointF(x,y+r+1),QPointF(x-r-1,y)]))
        p.setPen(QColor(MUTED)); p.setFont(QFont('Consolas',8))
        p.drawText(left,h-16,100,16,Qt.AlignLeft,clock(self.samples[0][0]))
        if n>1: p.drawText(right-100,h-16,100,16,Qt.AlignRight,clock(self.samples[-1][0]))

class SaveModPanel(QMainWindow):
    def __init__(self, bootstrap=True):
        super().__init__(); self.setWindowTitle('Save Mod'); self.resize(1280,850); self.setMinimumSize(1000,720)
        self._lang='ru'; self._motion=True; self._runner=BotRunner(); self._lock=None; self._media_dir=BASE_DIR/'media'
        self._auto_enabled=True; self._should_run=False; self._pending=None; self._worker_result=None
        self._restart_attempted=False; self._retry_at=None; self._close_after_stop=False; self._last_log=0.; self._visible_messages=[]
        self._lists_key=None; self._messages_key=None; self._last_status='stopped'
        self._build(); self._set_language(); self._tick()
        self._timer=QTimer(self); self._timer.timeout.connect(self._tick); self._timer.start(800)
        if bootstrap: QTimer.singleShot(300, self._bootstrap)
    def tr_(self,key,**kw): return WORDS[self._lang][key].format(**kw)
    def _build(self):
        root=QWidget(); root.setObjectName('root'); self.setCentralWidget(root)
        main=QHBoxLayout(root); main.setContentsMargins(0,0,0,0); main.setSpacing(0)
        side=QFrame(); side.setObjectName('sidebar'); side.setFixedWidth(214); main.addWidget(side)
        sl=QVBoxLayout(side); sl.setContentsMargins(16,22,16,16); sl.setSpacing(4)
        brandrow=QHBoxLayout(); mark=label('S','brandmark'); mark.setFixedSize(38,38); mark.setAlignment(Qt.AlignCenter)
        brandcol=QVBoxLayout(); brandcol.setSpacing(0); brandcol.addWidget(label('SAVE MOD','brand')); self.brand_sub=label('', 'tiny'); brandcol.addWidget(self.brand_sub)
        brandrow.addWidget(mark); brandrow.addSpacing(8); brandrow.addLayout(brandcol); brandrow.addStretch(); sl.addLayout(brandrow); sl.addSpacing(28)
        self.nav_title=label('', 'eyebrow'); sl.addWidget(self.nav_title); sl.addSpacing(6)
        self.nav={}; icons={'overview':'◫','activity':'≡','messages':'▤','errors':'!','logs':'⌘'}
        for key in ('overview','activity','messages','errors','logs'):
            b=button(name='nav'); b.setCheckable(True); b.clicked.connect(lambda checked=False,k=key:self._navigate(k)); self.nav[key]=b; sl.addWidget(b)
            b._icon=icons[key]
        sl.addSpacing(20); self.quick_title=label('', 'eyebrow'); sl.addWidget(self.quick_title); sl.addSpacing(6)
        self.shortcuts={}
        for key,action in [('media_dir',self._open_media),('log_file',self._open_log),('data_dir',self._open_data)]:
            b=button(name='nav', cb=action); self.shortcuts[key]=b; sl.addWidget(b)
        sl.addStretch(); self.motion_btn=button(cb=self._toggle_motion); sl.addWidget(self.motion_btn)
        self.lang_btn=button(cb=self._toggle_language); sl.addWidget(self.lang_btn)
        content=QWidget(); main.addWidget(content,1)
        c=QVBoxLayout(content); c.setContentsMargins(28,24,28,18); c.setSpacing(16)
        head=QHBoxLayout(); left=QVBoxLayout(); left.setSpacing(3)
        self.page_title=label('', 'heading'); self.page_sub=label('', 'muted'); left.addWidget(self.page_title); left.addWidget(self.page_sub); head.addLayout(left); head.addStretch()
        self.status=label('', 'status'); head.addWidget(self.status); self.start_btn=button(name='primary',cb=self._start_bot); self.stop_btn=button(cb=self._stop_bot)
        head.addWidget(self.start_btn); head.addWidget(self.stop_btn); c.addLayout(head)
        self.stack=QStackedWidget(); c.addWidget(self.stack,1)
        self.pages={}; self._build_overview()
        self.events_list=QListWidget(); self._build_list_page('activity',self.events_list)
        self.messages_table=QTableWidget(0,4); self.messages_table.setShowGrid(False); self.messages_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.messages_table.setSelectionBehavior(QTableWidget.SelectRows); self.messages_table.verticalHeader().setVisible(False)
        self.messages_table.setAlternatingRowColors(False); self.messages_table.setWordWrap(False); self.messages_table.setTextElideMode(Qt.ElideRight)
        header=self.messages_table.horizontalHeader(); header.setSectionResizeMode(0,QHeaderView.ResizeToContents); header.setSectionResizeMode(1,QHeaderView.ResizeToContents); header.setSectionResizeMode(2,QHeaderView.ResizeToContents); header.setSectionResizeMode(3,QHeaderView.Stretch)
        self.messages_table.cellClicked.connect(self._message_clicked); self._build_list_page('messages',self.messages_table)
        self.errors_list=QListWidget(); self._build_list_page('errors',self.errors_list)
        self.logs_text=QPlainTextEdit(); self.logs_text.setReadOnly(True); self.logs_text.setLineWrapMode(QPlainTextEdit.NoWrap); self._build_list_page('logs',self.logs_text)
        foot=QHBoxLayout(); self.footer=label('', 'tiny'); foot.addWidget(self.footer,1)
        self.auto_btn=button(cb=self._toggle_auto); foot.addWidget(self.auto_btn); c.addLayout(foot)
        self._page_effect=QGraphicsOpacityEffect(self.stack); self.stack.setGraphicsEffect(self._page_effect); self._page_effect.setOpacity(1)
        self._page_anim=QPropertyAnimation(self._page_effect,b'opacity',self); self._page_anim.setDuration(200); self._page_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._current_page='overview'; self.stack.setCurrentWidget(self.pages['overview']); self.nav['overview'].setChecked(True)
    def _build_overview(self):
        page=QWidget(); self.pages['overview']=page; self.stack.addWidget(page)
        outer=QVBoxLayout(page); outer.setContentsMargins(0,0,0,0); outer.setSpacing(16)
        grid=QGridLayout(); grid.setSpacing(10); self.metrics={}
        for i,(key,accent) in enumerate((('total_msg',BLUE),('total_media',MINT),('total_deleted',AMBER),('total_edits',PURPLE),('total_errors',RED),('total_db','#a5afc2'))):
            m=Metric('', '', accent, lambda:self._motion); self.metrics[key]=m; grid.addWidget(m,i//3,i%3)
        for i in range(3):grid.setColumnStretch(i,1)
        outer.addLayout(grid)
        lower=QHBoxLayout(); lower.setSpacing(12); outer.addLayout(lower,1)
        graph=card(); gl=QVBoxLayout(graph); gl.setContentsMargins(18,16,18,14); gl.setSpacing(8)
        self.graph_title=label('','section'); self.graph_sub=label('','tiny'); gl.addWidget(self.graph_title); gl.addWidget(self.graph_sub)
        legend=QHBoxLayout(); self.legend={}
        for key,col,shape in SERIES:
            x=label(); x.setStyleSheet(f'color:{col};font-weight:600;font-size:11px;'); self.legend[key]=(x,shape); legend.addWidget(x)
        legend.addStretch(); self.hover_time=label('', 'tiny'); legend.addWidget(self.hover_time); gl.addLayout(legend)
        self.chart=ActivityChart(self.tr_,lambda:self._motion); self.chart.hover_changed=self._chart_hover
        gl.addWidget(self.chart,1); lower.addWidget(graph,3)
        recent=card(); rl=QVBoxLayout(recent); rl.setContentsMargins(16,16,16,12); rl.setSpacing(10)
        row=QHBoxLayout(); self.recent_title=label('','section'); row.addWidget(self.recent_title); row.addStretch(); self.view_all=button(name='link',cb=lambda:self._navigate('activity')); row.addWidget(self.view_all)
        rl.addLayout(row); self.recent_list=QListWidget(); self.recent_list.setSelectionMode(QListWidget.NoSelection); self.recent_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff); self.recent_list.setTextElideMode(Qt.ElideRight); rl.addWidget(self.recent_list,1); lower.addWidget(recent,2)
        health=card(); hl=QHBoxLayout(health); hl.setContentsMargins(16,11,16,11); hl.setSpacing(18)
        self.uptime_lbl=label('', 'tiny'); self.poll_lbl=label('', 'tiny'); self.event_lbl=label('', 'tiny')
        hl.addWidget(self.uptime_lbl); hl.addStretch(); hl.addWidget(self.poll_lbl); hl.addWidget(self.event_lbl); outer.addWidget(health)
    def _build_list_page(self,key,body):
        panel=card(); layout=QVBoxLayout(panel); layout.setContentsMargins(16,12,16,12); layout.addWidget(body)
        self.pages[key]=panel; self.stack.addWidget(panel)
    def _set_language(self):
        self.brand_sub.setText(self.tr_('tagline')); self.nav_title.setText(self.tr_('workspace')); self.quick_title.setText(self.tr_('shortcuts'))
        for k,b in self.nav.items(): b.setText(f'{b._icon}    {self.tr_(k)}')
        for k,b in self.shortcuts.items(): b.setText('↗    '+self.tr_(k))
        self.start_btn.setText(self.tr_('start')); self.stop_btn.setText(self.tr_('stop')); self.lang_btn.setText(self.tr_('language'))
        self.motion_btn.setText(self.tr_('motion_on' if self._motion else 'motion_off')); self.auto_btn.setText(self.tr_('auto_on' if self._auto_enabled else 'auto_off'))
        for k,m in self.metrics.items(): m.title.setText(self.tr_(k)); m.caption.setText(self.tr_('stored' if k=='total_db' else 'this_session'))
        self.graph_title.setText(self.tr_('chart')); self.graph_sub.setText(self.tr_('chart_sub')); self.recent_title.setText(self.tr_('recent')); self.view_all.setText(self.tr_('view_all'))
        self._chart_hover(self.chart.hover)
        self.messages_table.setHorizontalHeaderLabels([self.tr_('time'),self.tr_('user_id'),self.tr_('name'),self.tr_('message')])
        self.footer.setText(self.tr_('single')); self._page_text(); self._lists_key=None; self._messages_key=None; self.chart.update()
    def _chart_hover(self,index):
        values=None
        if index is not None and 0 <= index < len(self.chart.samples):
            t,values=self.chart.samples[index];self.hover_time.setText(clock(t))
        else:self.hover_time.setText('')
        for i,(k,_,shape) in enumerate(SERIES):
            value=f' {values[i]:.1f}' if values is not None else ''
            self.legend[k][0].setText(shape+'  '+self.tr_(k)+value)

    def _page_text(self):
        self.page_title.setText(self.tr_(self._current_page)); self.page_sub.setText(self.tr_(self._current_page+'_sub'))
    def _navigate(self,key):
        if key==self._current_page:return
        self._current_page=key; self.stack.setCurrentWidget(self.pages[key]); self._page_text()
        for k,b in self.nav.items(): b.setChecked(k==key)
        self._page_anim.stop()
        if self._motion:
            self._page_anim.setStartValue(.35); self._page_anim.setEndValue(1.); self._page_anim.start()
        else:self._page_effect.setOpacity(1.)
        if key=='logs':self._last_log=0.;self._refresh_log()
    def _toggle_language(self): self._lang='en' if self._lang=='ru' else 'ru'; self._set_language(); self._tick()
    def _toggle_motion(self):
        self._motion=not self._motion; self.motion_btn.setText(self.tr_('motion_on' if self._motion else 'motion_off'))
        if not self._motion:
            self._page_anim.stop(); self._page_effect.setOpacity(1.); self.chart.finish()
            for m in self.metrics.values():m.finish()
    def _toggle_auto(self):
        if self._pending:return
        self._auto_enabled=not self._auto_enabled; self._restart_attempted=False
        if not self._auto_enabled:self._retry_at=None
        self.auto_btn.setText(self.tr_('auto_on' if self._auto_enabled else 'auto_off'))
        self.footer.setText(self.tr_('auto_enabled' if self._auto_enabled else 'auto_disabled'))
    def _bootstrap(self):
        try:
            kill_foreign_bots(keep_pid=os.getpid(),include_panel=False)
            lock=InstanceLock()
            if not lock.acquire():
                QMessageBox.critical(self,'Save Mod',already_running_message()); self.footer.setText(self.tr_('conflict_notice'));return
            self._lock=lock
            try:self._media_dir=load_config().media_dir
            except Exception as e:
                QMessageBox.critical(self,self.tr_('config_error'),str(e));self.footer.setText(self.tr_('config_error'));return
            self._start_bot()
        except Exception as e:
            _write_crash(e); QMessageBox.critical(self,self.tr_('error_title'),str(e))
    def _start_bot(self):
        if self._runner.is_running or self._pending:return
        if self._lock is None:
            lock=InstanceLock()
            if not lock.acquire():QMessageBox.critical(self,'Save Mod',already_running_message());return
            self._lock=lock
        try:
            kill_foreign_bots(keep_pid=os.getpid(),include_panel=False)
            self._restart_attempted=False;self._retry_at=None;self._should_run=True;self._runner.start()
        except Exception as e:
            self._should_run=False;_write_crash(e);QMessageBox.critical(self,self.tr_('start_error'),str(e))
        self._tick()
    def _stop_bot(self):
        if self._pending:return
        self._should_run=False; self._retry_at=None; self._restart_attempted=False
        self._pending='stop'; self._worker_result=None; self.footer.setText(self.tr_('stopping_notice'))
        def work():
            try:self._worker_result=bool(self._runner.stop()) and not self._runner.is_running
            except Exception:logger.exception('Stop failed');self._worker_result=False
        threading.Thread(target=work,daemon=True,name='panel-stop').start();self._tick()
    def _restart(self):
        if self._pending:return
        self._pending='restart';self._worker_result=None;self.footer.setText(self.tr_('restart_notice'))
        def work():
            try:
                if not self._runner.stop(timeout=30) or self._runner.is_running:self._worker_result=False;return
                self._runner.start(); self._worker_result=True
            except Exception:logger.exception('Restart failed');self._worker_result=False
        threading.Thread(target=work,daemon=True,name='panel-restart').start()
    def _open_path(self,path,folder=False):
        try:
            if folder:path.mkdir(parents=True,exist_ok=True)
            else:path.touch(exist_ok=True)
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve()))):raise OSError(self.tr_('open_failed'))
        except OSError as e:QMessageBox.warning(self,self.tr_('error_title'),str(e))
    def _open_media(self):self._open_path(Path(self._media_dir),True)
    def _open_data(self):self._open_path(BASE_DIR/'data',True)
    def _open_log(self):self._open_path(BASE_DIR/'bot.log')
    def _message_clicked(self,row,col):
        if col!=1 or not 0<=row<len(self._visible_messages):return
        msg=self._visible_messages[row]
        if msg.user_id is None:return
        folder=Path(self._media_dir)/str(msg.chat_id)
        if not folder.is_dir():QMessageBox.information(self,self.tr_('messages'),self.tr_('folder_missing'));return
        self._open_path(folder,True)
    def _ago(self,ts):
        if not ts:return '—'
        sec=max(0,int(time.time()-ts))
        if sec<60:return self.tr_('ago_s',n=sec)
        if sec<3600:return self.tr_('ago_m',n=sec//60)
        return self.tr_('ago_h',n=sec//3600)
    def _fill_lists(self,snap):
        def line(ev):
            kind=ev.kind.split(',')[0].strip(); name=WORDS[self._lang].get('event_'+kind,kind)
            detail=ev.detail
            if self._lang=='en':
                for old,new in (('подключение отключено','connection disabled'),('подключение включено','connection enabled'),('одноразовое медиа','one-time media'),('правка текста','message edited'),('сообщ.','messages'),('удалено','deleted'),('сообщение','message'),('медиа','media'),(' от ',' by ')):
                    detail=detail.replace(old,new)
            return f'{clock(ev.at)}   {name}  ·  {detail}'
        events=[line(e) for e in snap['recent'][:60]]; errors=[line(e) for e in snap['recent_errors'][:60]]
        key=(self._lang,tuple(events),tuple(errors))
        if key==self._lists_key:return
        self._lists_key=key
        for widget,items,empty in ((self.events_list,events,'empty_events'),(self.recent_list,events[:7],'empty_events'),(self.errors_list,errors,'empty_errors')):
            widget.clear()
            if items:
                widget.addItems(items)
                for i in range(widget.count()):widget.item(i).setToolTip(items[i])
            else:
                item=QListWidgetItem(self.tr_(empty));item.setFlags(Qt.NoItemFlags);item.setForeground(QColor(MUTED));widget.addItem(item)
    def _fill_messages(self,items):
        visible=items[:80]; key=(self._lang,tuple((m.at,m.user_id,m.chat_id,m.name,m.username,m.text) for m in visible))
        if key==self._messages_key:return
        self._messages_key=key;self._visible_messages=visible
        self.messages_table.clearSpans()
        self.messages_table.setRowCount(max(1, len(visible)))
        if not visible:
            self.messages_table.setSpan(0, 0, 1, 4)
            item=QTableWidgetItem(self.tr_('empty_messages'));item.setFlags(Qt.NoItemFlags);item.setForeground(QColor(MUTED))
            self.messages_table.setItem(0,0,item);self.messages_table.setRowHeight(0,42)
            return
        for i,m in enumerate(visible):
            nick=(m.name or self.tr_('no_name')).replace('\n',' ').strip()
            if m.username:nick+=f' (@{m.username})'
            for j,value in enumerate((clock(m.at),str(m.user_id) if m.user_id is not None else '?',nick,m.text)):
                item=QTableWidgetItem(value)
                if j==1 and m.user_id is not None:item.setForeground(QColor(BLUE));item.setToolTip(self.tr_('messages_sub'))
                self.messages_table.setItem(i,j,item)
            self.messages_table.setRowHeight(i,42)
    def _refresh_log(self):
        now=time.monotonic()
        if self._current_page!='logs' or now-self._last_log<3:return
        self._last_log=now;path=BASE_DIR/'bot.log'
        if not path.exists():self.logs_text.setPlainText(self.tr_('empty_logs'));return
        try:
            with path.open('rb') as f:f.seek(0,2);size=f.tell();f.seek(max(0,size-40000));raw=f.read().decode('utf-8',errors='replace')
        except OSError:return
        terms=('error','critical','warning','saved','delete','connection','online','conflict','stopped')
        lines=[re.sub(r'(api\.telegram\.org/(?:file/)?bot)[^/\s]+',r'\1***',line,flags=re.IGNORECASE) for line in raw.splitlines()[-120:] if any(k in line.lower() for k in terms)]
        lines=[re.sub(r'\d{6,12}:[A-Za-z0-9_-]{30,}','***',line) for line in lines]
        text='\n'.join(lines[-80:]) or self.tr_('empty_logs')
        if self.logs_text.toPlainText()!=text:self.logs_text.setPlainText(text)
    def _tick(self):
        if self._pending and self._worker_result is not None:
            pending,ok=self._pending,self._worker_result;self._pending=None;self._worker_result=None
            if pending=='stop':
                self.footer.setText(self.tr_('stopped_notice' if ok else 'stop_failed'))
                if self._close_after_stop:
                    self._close_after_stop=False
                    if ok:self._release();QTimer.singleShot(0,self.close);return
            else:
                self._retry_at=time.monotonic()+60;self.footer.setText(self.tr_('restart_wait' if ok else 'restart_retry'))
        snap=STATS.snapshot();running=self._runner.is_running;poll=snap['last_poll_at'] or (snap['started_at'] if running else 0)
        healthy=running and snap['status']=='online' and snap['last_poll_at']>=snap['started_at']
        stale=running and snap['status'] in ('starting','online') and poll and time.time()-poll>45
        if healthy:
            recovered=self._retry_at is not None;self._restart_attempted=False;self._retry_at=None
            if recovered:self.footer.setText(self.tr_('restart_ok'))
        elif self._auto_enabled and self._should_run and not self._pending:
            due=self._retry_at is not None and time.monotonic()>=self._retry_at
            first=bool(stale) and not self._restart_attempted and self._retry_at is None
            stopped=not running and self._retry_at is None
            if due or first or stopped:self._retry_at=None;self._restart_attempted=True;self._restart()
        state=('stopping' if self._pending=='stop' else 'restart' if self._pending=='restart' else
               'stopped' if not running else 'conflict' if snap['status']=='conflict' else
               'stale' if stale else snap['status'] if snap['status'] in ('starting','online') else 'starting')
        color={'online':MINT,'starting':AMBER,'stopping':AMBER,'restart':AMBER,'stale':AMBER,'conflict':RED,'stopped':MUTED}[state]
        self.status.setText('●  '+self.tr_('status_'+state));self.status.setStyleSheet(f'color:{color}; background:#252b39; border:1px solid #394253;')
        self.start_btn.setEnabled(not running and not self._pending);self.stop_btn.setEnabled(running and not self._pending);self.auto_btn.setEnabled(not self._pending)
        self.uptime_lbl.setText(self.tr_('uptime')+'   '+(uptime(time.time()-snap['started_at']) if running else '—'))
        self.poll_lbl.setText(self.tr_('poll')+'   '+self._ago(snap['last_poll_at']))
        self.event_lbl.setText(self.tr_('event')+'   '+self._ago(snap['last_event_at']))
        for key,stat in (('total_msg','messages'),('total_media','media'),('total_deleted','deleted'),('total_edits','edits'),('total_errors','errors'),('total_db','db_messages')):self.metrics[key].set_value(snap[stat])
        self.chart.observe(snap,running);self._fill_lists(snap);self._fill_messages(snap['recent_messages']);self._refresh_log()
    def _release(self):
        if self._lock is not None:self._lock.release();self._lock=None
    def closeEvent(self,event):
        if self._pending:
            QMessageBox.information(self,self.tr_('close_title'),self.tr_('busy_close'));event.ignore();return
        if self._runner.is_running:
            ans=QMessageBox.question(self,self.tr_('close_title'),self.tr_('close_question'),QMessageBox.Yes|QMessageBox.No,QMessageBox.No)
            if ans!=QMessageBox.Yes:event.ignore();return
            self._close_after_stop=True;self._stop_bot();event.ignore();return
        self._release();event.accept()

def _write_crash(exc=None):
    import traceback
    path=BASE_DIR/'data'/'panel_crash.log';path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a',encoding='utf-8') as f:
        f.write('\n'+'='*60+'\n'+datetime.now().isoformat(timespec='seconds')+'\n')
        if exc:f.write(f'{type(exc).__name__}: {exc}\n')
        f.write(traceback.format_exc())

def main():
    try:
        setup_logging(console=False);app=QApplication.instance() or QApplication(sys.argv);app.setStyle('Fusion');app.setStyleSheet(STYLESHEET)
        window=SaveModPanel();window.show();app.exec()
    except Exception as exc:
        _write_crash(exc);raise

if __name__=='__main__':main()
