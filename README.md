# Save Mod — Telegram Bot

[English](#english) | [Русский](#russian)

<a id="english"></a>
## English

Save Mod is a Telegram Business bot that archives personal conversations and media locally, and sends notifications about edited or deleted messages. It includes a desktop control panel with Russian and English UI.

### Features

| Feature | Description |
|---------|-------------|
| Deleted messages | Finds the saved copy of a deleted message and sends it to the service chat |
| Edited messages | Saves the original text and reports edits as “before → after” |
| Protected media | Downloads supported media when received so it remains available if the message is deleted |

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

#### 4. Configure the administrator

Set your Telegram user ID in `ADMIN_USER_ID` in `bot/config.py` before using `/status`. The value is intentionally `None` by default, so the admin command remains unavailable until configured.

### Service chat

Notifications are sent to the connected owner's private chat by default. To send them to a group or channel, set `SERVICE_CHAT_ID` in `.env` and add the bot with permission to send messages.

```env
SERVICE_CHAT_ID=-1001234567890
```

### Bot commands

| Command | Description |
|---------|-------------|
| `/start` | Shows the connection instructions |
| `/status` | Lists active Telegram Business connections; available to the configured administrator in a private chat only |

### Project structure

```text
E:\SaveBot\
├── bot/
│   ├── main.py              # Entry point
│   ├── config.py            # Configuration loaded from .env
│   ├── storage.py           # SQLite message storage
│   ├── media.py             # Media downloads
│   ├── formatters.py        # Notification formatting
│   └── handlers/            # Telegram update handlers
├── data/                    # SQLite database (created automatically)
├── media/                   # Downloaded media (created automatically)
├── .env.example
└── requirements.txt
```

### Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `BOT_TOKEN` | Yes | Token from BotFather |
| `SERVICE_CHAT_ID` | No | Destination for notifications |
| `DATABASE_PATH` | No | SQLite path; defaults to `data/messages.db` |
| `MEDIA_DIR` | No | Media directory; defaults to `media/` |

### Windows startup

Run `start.bat` to open the desktop control panel. For background operation, run:

```powershell
pythonw -m bot.main
```

For production, use a continuously available host such as a VPS.

### Telegram API limitations

- Bots cannot directly forward messages from Business chats; Save Mod sends copies of content it has already stored.
- Messages received before the bot was connected are not in its database.
- The bot must remain running to capture updates continuously.

### License

This project is for personal use and learning. Use it in accordance with applicable law and Telegram policies.

<a id="russian"></a>
## Русский

Save Mod — бот для Telegram Business, который локально сохраняет личные переписки и медиа, а также отправляет уведомления об изменённых и удалённых сообщениях. В комплекте есть настольная панель управления с русским и английским интерфейсом.

### Возможности

| Возможность | Описание |
|-------------|----------|
| Удалённые сообщения | Находит сохранённую копию удалённого сообщения и отправляет её в сервисный чат |
| Изменённые сообщения | Сохраняет исходный текст и показывает изменение в формате «было → стало» |
| Защищённые медиа | Загружает поддерживаемые медиа при получении, чтобы они оставались доступны после удаления сообщения |

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

#### 4. Настройте администратора

Перед использованием `/status` укажите свой Telegram user ID в `ADMIN_USER_ID` файла `bot/config.py`. По умолчанию значение намеренно установлено в `None`, поэтому команда администратора недоступна, пока вы не настроите ID.

### Сервисный чат

По умолчанию уведомления приходят в личный чат подключённого владельца. Чтобы отправлять их в группу или канал, задайте `SERVICE_CHAT_ID` в `.env` и добавьте бота с правом отправки сообщений.

```env
SERVICE_CHAT_ID=-1001234567890
```

### Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Показывает инструкцию по подключению |
| `/status` | Показывает активные подключения Telegram Business; доступна только настроенному администратору в личном чате с ботом |

### Структура проекта

```text
E:\SaveBot\
├── bot/
│   ├── main.py              # Точка входа
│   ├── config.py            # Конфигурация из .env
│   ├── storage.py           # SQLite-хранилище сообщений
│   ├── media.py             # Скачивание медиа
│   ├── formatters.py        # Форматирование уведомлений
│   └── handlers/            # Обработчики обновлений Telegram
├── data/                    # База SQLite (создаётся автоматически)
├── media/                   # Загруженные медиа (создаётся автоматически)
├── .env.example
└── requirements.txt
```

### Переменные окружения

| Переменная | Обязательная | Описание |
|------------|--------------|----------|
| `BOT_TOKEN` | Да | Токен от BotFather |
| `SERVICE_CHAT_ID` | Нет | Чат для уведомлений |
| `DATABASE_PATH` | Нет | Путь к SQLite; по умолчанию `data/messages.db` |
| `MEDIA_DIR` | Нет | Папка для медиа; по умолчанию `media/` |

### Запуск в Windows

Запустите `start.bat`, чтобы открыть настольную панель управления. Для работы в фоне выполните:

```powershell
pythonw -m bot.main
```

Для постоянной работы используйте доступный круглосуточно хост, например VPS.

### Ограничения Telegram API

- Боты не могут напрямую пересылать сообщения из Business-чатов; Save Mod отправляет копии содержимого, которое уже успел сохранить.
- Сообщения, полученные до подключения бота, отсутствуют в его базе данных.
- Чтобы непрерывно получать обновления, бот должен постоянно работать.

### Лицензия

Проект предназначен для личного использования и обучения. Соблюдайте законодательство и правила Telegram.