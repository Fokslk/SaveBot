# Save Mod — Telegram Bot

[English](#english) | [Русский](#russian)

<a id="english"></a>
## English

Save Mod is a Telegram Business bot that archives personal conversations and media locally, and sends notifications about edited or deleted messages. It includes a PySide6 desktop control panel with Russian and English UI, a headless mode, and an optional ANSI console dashboard.

### Features

| Feature | Description |
|---------|-------------|
| Deleted messages | Sends the saved copy (text, caption, media) of a deleted message to the service chat. Text-only deletions are also appended to `media/<chat_id>/deleted_texts.txt`. |
| Edited messages | Saves the original text and caption and reports edits as “before → after”. |
| Media archive | Downloads supported media when received so it remains available after deletion. One-time / protected photos, videos and video notes are saved when the business owner replies to them (Telegram limitation). |
| Desktop panel | Start/stop, live session metrics, activity chart, event, message and error lists, log tail, RU/EN toggle and auto-restart. |
| Headless mode | Runs without a GUI; `--console` enables a live ANSI dashboard. |
| Single instance | `data/save_mod.lock` prevents duplicate instances; on Windows, other `python -m bot.main` processes of this project are stopped automatically. |

### Setup

#### 1. Create a bot

1. Open [@BotFather](https://t.me/BotFather) in Telegram.
2. Send `/newbot`, then choose a name and username.
3. Keep the bot token from BotFather private.

#### 2. Enable Business Mode

In BotFather, open **/mybots → your bot → Bot Settings → Business Mode** (also called Secretary Mode in some Telegram clients) and turn it on.

#### 3. Connect the bot to Telegram Business

1. Open **Telegram Settings → Telegram Business → Chatbots** (wording may vary by client).
2. Enter the bot username and grant permission to read and process messages.
3. Confirm the connection. The bot will send an activation message.

#### 4. Configure `.env`

Copy `.env.example` to `.env` and set `BOT_TOKEN`. Optionally set `SERVICE_CHAT_ID`, `DATABASE_PATH` and `MEDIA_DIR`.

#### 5. Configure the administrator

Set your Telegram user ID in `ADMIN_USER_ID` in `bot/config.py` before using `/status`. The value is intentionally `None` by default, so the admin command remains unavailable until configured.

### Installation

Requires Python 3.10–3.15 (the versions supported by the pinned `PySide6-Essentials` and `python-telegram-bot`).

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
notepad .env
```

`requirements.txt` includes `PySide6-Essentials` for the desktop panel. For headless-only use, `python-telegram-bot` and `python-dotenv` are enough:

```powershell
pip install python-telegram-bot==22.8 python-dotenv==1.2.2
```

### Service chat

Notifications are sent to the connected owner's private chat by default. To send them to a group or channel, set `SERVICE_CHAT_ID` in `.env` and add the bot with permission to send messages. Everyone with access to that chat will see the archived content.

```env
SERVICE_CHAT_ID=-1001234567890
```

### Running

| Command | Description |
|---------|-------------|
| `start.bat` | Opens the desktop control panel (foreground console). |
| `python -m bot.panel` or `python run.py` | Opens the panel without the BAT wrapper. |
| `run_bot.ps1` | Starts the panel in the background with `pythonw`. |
| `python -m bot.main --headless` | Runs the bot without GUI; writes to `bot.log`. |
| `python -m bot.main --headless --console` | Headless mode with a live ANSI dashboard. |
| `pythonw -m bot.main` | Headless mode in the background. |

Only one instance can run at a time: the panel and all headless modes share `data/save_mod.lock`. On Windows, starting the bot stops other `python -m bot.main` processes of this project.

### Bot commands

| Command | Description |
|---------|-------------|
| `/start` | Shows the connection instructions |
| `/status` | Lists active Telegram Business connections; available to the configured administrator in a private chat only |

### Project structure

```text
SaveBot\
├── bot/
│   ├── main.py                 # Entry point: GUI by default, --headless / --console
│   ├── panel.py                # PySide6 desktop control panel
│   ├── dashboard.py            # ANSI console dashboard for headless mode
│   ├── runner.py               # Telegram application, polling and logging
│   ├── config.py               # Configuration from .env; ADMIN_USER_ID
│   ├── instance.py             # Single-instance lock and duplicate process cleanup
│   ├── storage.py              # SQLite message storage
│   ├── media.py                # Media downloads and type detection
│   ├── formatters.py           # Notification formatting
│   ├── runtime_stats.py        # In-memory session statistics for the UIs
│   ├── utils.py                # Business connection resolution
│   └── handlers/
│       ├── business_connection.py
│       ├── commands.py
│       ├── deleted.py
│       ├── messages.py
│       └── notifications.py
├── data/                       # SQLite DB, lock and panel logs (created automatically)
├── media/                      # Downloaded media (created automatically)
├── bot.log                     # Runtime log (created automatically)
├── .env.example
├── requirements.txt
├── start.bat                   # Open the desktop panel
├── run_bot.bat                 # Alias for start.bat
├── run_bot.ps1                 # Start the panel in background with pythonw
└── run.py                      # python run.py → desktop panel
```

### Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `BOT_TOKEN` | Yes | Token from BotFather |
| `SERVICE_CHAT_ID` | No | Destination for notifications; defaults to the owner's private chat |
| `DATABASE_PATH` | No | SQLite path relative to the project root; defaults to `data/messages.db` |
| `MEDIA_DIR` | No | Media directory relative to the project root; defaults to `media/` |

### Files and logs

- `data/messages.db` — SQLite database with messages, edits and business connections.
- `media/<chat_id>/<type>/` — downloaded media.
- `media/<chat_id>/deleted_texts.txt` — plain-text archive of deleted text-only messages.
- `bot.log` — runtime log.
- `data/panel_stdout.log`, `data/panel_crash.log` — panel output and crash reports when launched via `start.bat`.

### Telegram API limitations

- Bots cannot directly forward messages from Business chats; Save Mod sends copies of content it has already stored.
- Messages received before the bot was connected are not in its database.
- The bot must remain running to capture updates continuously.
- One-time / protected media can be saved only after the business owner replies to the message.
- The Bot API limits file downloads to 20 MB; larger media is stored as metadata only.
- Notification times are shown in the local timezone of the machine running the bot.

### Data privacy

Conversations and media are stored unencrypted on disk. Protect the project folder and `.env`: anyone with access to them can read the archive or take over the bot. Do not share `data/`, `media/` or log files. On Windows, restrict NTFS permissions on the project folder to your account (plus SYSTEM and Administrators); inherited permissions on some drives let other local users read or modify these files.

### License

This project is for personal use and learning. Use it in accordance with applicable law and Telegram policies.

<a id="russian"></a>
## Русский

Save Mod — бот для Telegram Business, который локально сохраняет личные переписки и медиа, а также отправляет уведомления об изменённых и удалённых сообщениях. В комплекте есть настольная панель управления на PySide6 с русским и английским интерфейсом, headless-режим и необязательный ANSI-дашборд для консоли.

### Возможности

| Возможность | Описание |
|-------------|----------|
| Удалённые сообщения | Отправляет сохранённую копию (текст, подпись, медиа) удалённого сообщения в сервисный чат. Удалённые текстовые сообщения также дописываются в `media/<chat_id>/deleted_texts.txt`. |
| Изменённые сообщения | Сохраняет исходный текст и подпись и показывает изменение в формате «было → стало». |
| Архив медиа | Загружает поддерживаемые медиа при получении, чтобы они оставались доступны после удаления. Одноразовые и защищённые фото, видео и кружки сохраняются только после ответа владельца бизнеса на сообщение (ограничение Telegram). |
| Настольная панель | Запуск и остановка, метрики текущего сеанса, график активности, списки событий, сообщений и ошибок, хвост лога, переключение RU/EN и автоперезапуск. |
| Headless-режим | Работа без GUI; с флагом `--console` включается живой ANSI-дашборд. |
| Один экземпляр | `data/save_mod.lock` не даёт запустить дубликат; на Windows лишние процессы `python -m bot.main` останавливаются автоматически. |

### Настройка

#### 1. Создайте бота

1. Откройте [@BotFather](https://t.me/BotFather) в Telegram.
2. Отправьте `/newbot`, затем задайте имя и username.
3. Не передавайте токен бота, полученный у BotFather, посторонним.

#### 2. Включите Business Mode

В BotFather откройте **/mybots → ваш бот → Bot Settings → Business Mode** (в некоторых клиентах Telegram также называется Secretary Mode) и включите его.

#### 3. Подключите бота к Telegram Business

1. Откройте **Настройки Telegram → Telegram для бизнеса → Чат-боты** (название раздела может отличаться в разных клиентах).
2. Укажите username бота и разрешите ему читать и обрабатывать сообщения.
3. Подтвердите подключение. Бот отправит сообщение об активации.

#### 4. Настройте `.env`

Скопируйте `.env.example` в `.env` и укажите `BOT_TOKEN`. При необходимости задайте `SERVICE_CHAT_ID`, `DATABASE_PATH` и `MEDIA_DIR`.

#### 5. Настройте администратора

Перед использованием `/status` укажите свой Telegram user ID в `ADMIN_USER_ID` файла `bot/config.py`. По умолчанию значение намеренно установлено в `None`, поэтому команда администратора недоступна, пока вы не настроите ID.

### Установка

Требуется Python 3.10–3.15 (версии, которые поддерживают закреплённые `PySide6-Essentials` и `python-telegram-bot`).

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
notepad .env
```

`requirements.txt` включает `PySide6-Essentials` для настольной панели. Если панель не нужна, достаточно `python-telegram-bot` и `python-dotenv`:

```powershell
pip install python-telegram-bot==22.8 python-dotenv==1.2.2
```

### Сервисный чат

По умолчанию уведомления приходят в личный чат подключённого владельца. Чтобы отправлять их в группу или канал, задайте `SERVICE_CHAT_ID` в `.env` и добавьте бота с правом отправки сообщений. Все, у кого есть доступ к этому чату, увидят сохранённую переписку.

```env
SERVICE_CHAT_ID=-1001234567890
```

### Запуск

| Команда | Описание |
|---------|----------|
| `start.bat` | Открывает настольную панель управления (в текущем окне консоли). |
| `python -m bot.panel` или `python run.py` | Открывает панель без BAT-обёртки. |
| `run_bot.ps1` | Запускает панель в фоне через `pythonw`. |
| `python -m bot.main --headless` | Бот без GUI; пишет в `bot.log`. |
| `python -m bot.main --headless --console` | Headless-режим с живым ANSI-дашбордом. |
| `pythonw -m bot.main` | Headless-бот в фоне. |

Одновременно может работать только один экземпляр: панель и все headless-режимы используют общий `data/save_mod.lock`. На Windows при запуске останавливаются другие процессы `python -m bot.main` этого проекта.

### Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Показывает инструкцию по подключению |
| `/status` | Показывает активные подключения Telegram Business; доступна только настроенному администратору в личном чате с ботом |

### Структура проекта

```text
SaveBot\
├── bot/
│   ├── main.py                 # Точка входа: GUI по умолчанию, --headless / --console
│   ├── panel.py                # Настольная панель на PySide6
│   ├── dashboard.py            # ANSI-дашборд для headless-режима
│   ├── runner.py               # Telegram-приложение, polling и логирование
│   ├── config.py               # Конфигурация из .env; ADMIN_USER_ID
│   ├── instance.py             # Блокировка одного экземпляра и очистка процессов
│   ├── storage.py              # SQLite-хранилище сообщений
│   ├── media.py                # Скачивание медиа и определение типа
│   ├── formatters.py           # Форматирование уведомлений
│   ├── runtime_stats.py        # Статистика сеанса в памяти для интерфейсов
│   ├── utils.py                # Определение business-подключения
│   └── handlers/
│       ├── business_connection.py
│       ├── commands.py
│       ├── deleted.py
│       ├── messages.py
│       └── notifications.py
├── data/                       # База SQLite, lock и логи панели (создаются автоматически)
├── media/                      # Загруженные медиа (создаётся автоматически)
├── bot.log                     # Лог работы (создаётся автоматически)
├── .env.example
├── requirements.txt
├── start.bat                   # Открыть настольную панель
├── run_bot.bat                 # Псевдоним start.bat
├── run_bot.ps1                 # Запуск панели в фоне через pythonw
└── run.py                      # python run.py → настольная панель
```

### Переменные окружения

| Переменная | Обязательная | Описание |
|------------|--------------|----------|
| `BOT_TOKEN` | Да | Токен от BotFather |
| `SERVICE_CHAT_ID` | Нет | Чат для уведомлений; по умолчанию личный чат владельца |
| `DATABASE_PATH` | Нет | Путь к SQLite относительно корня проекта; по умолчанию `data/messages.db` |
| `MEDIA_DIR` | Нет | Папка для медиа относительно корня проекта; по умолчанию `media/` |

### Файлы и логи

- `data/messages.db` — база SQLite с сообщениями, правками и business-подключениями.
- `media/<chat_id>/<type>/` — загруженные медиа.
- `media/<chat_id>/deleted_texts.txt` — текстовый архив удалённых сообщений без медиа.
- `bot.log` — журнал работы.
- `data/panel_stdout.log`, `data/panel_crash.log` — вывод и отчёты о падениях панели при запуске через `start.bat`.

### Ограничения Telegram API

- Боты не могут напрямую пересылать сообщения из Business-чатов; Save Mod отправляет копии содержимого, которое уже успел сохранить.
- Сообщения, полученные до подключения бота, отсутствуют в его базе данных.
- Чтобы непрерывно получать обновления, бот должен постоянно работать.
- Одноразовые и защищённые медиа можно сохранить только после ответа владельца бизнеса на сообщение.
- Bot API ограничивает скачивание файлов 20 МБ; более крупные медиа сохраняются только как метаданные.
- Время в уведомлениях показывается в локальном часовом поясе машины, на которой запущен бот.

### Приватность данных

Переписки и медиа хранятся на диске без шифрования. Защищайте папку проекта и `.env`: любой, у кого есть к ним доступ, может прочитать архив или перехватить управление ботом. Не передавайте папки `data/`, `media/` и файлы логов посторонним. На Windows ограничьте NTFS-права на папку проекта своей учётной записью (а также SYSTEM и «Администраторы»): унаследованные права на некоторых дисках позволяют другим локальным пользователям читать и изменять эти файлы.

### Лицензия

Проект предназначен для личного использования и обучения. Соблюдайте законодательство и правила Telegram.
