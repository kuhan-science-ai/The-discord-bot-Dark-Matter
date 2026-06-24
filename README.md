# Dark-Matter - AI-Powered Discord Social Bot

Dark-Matter is a complete, production-ready, conversational Discord bot architected in Python. Dark-Matter acts as a friendly, social, smart, and community-oriented member of your Discord server, powered by Google Gemini (`gemini-2.5-flash`) via the official Google GenAI SDK.

Dark-Matter features **short-term dialogue memory**, **long-term user relationship memory** (consolidated automatically via AI analysis), a **guild knowledge system** for local FAQs/rules, a new-member **welcome system**, and an built-in **anti-spam rate limiter**.

---

## Features

- 💬 **Dynamic Conversations**: Responds to direct mentions, replies, or the `/ask` slash command. Uses past context and long-term user memories to personalize responses.
- 🧠 **Smart Memory System**:
  - *Short-Term Memory*: Rolling 15-message dialogue logs tracked in SQLite.
  - *Long-Term Memory*: Profiles interests, hobbies, preferences, and updates relationship summaries automatically in the background after conversations (to minimize token counts and avoid raw log retention).
- 📚 **Server Knowledge Base**: Server Admins can teach the bot rules, events, or FAQs. The bot seamlessly leverages this context to answer server-specific questions.
- 👋 **Welcome System**: Greets new server members with a friendly, custom message mentioning them.
- 🛡️ **Anti-Spam Controls**: Token-bucket-style request rate limiting (max 5 requests per 30 seconds per user) to safeguard your Gemini API quota.
- 🐳 **Dockerized**: Container configuration ready for quick deployment.
- 🗄️ **SQLite + Asyncio**: Safe, non-blocking asynchronous database operations using `aiosqlite`.

---

## Slash Commands

### General Commands
- `/ask <question>`: Chat or query Dark-Matter.
- `/help`: Detailed description of commands.
- `/ping`: Check the bot's websocket connection latency.
- `/serverinfo`: Displays server metadata and statistics.

### Memory Commands
- `/profile`: Shows basic profile details saved in the database.
- `/memory`: Inspects long-term interests, hobbies, and relationship summaries.
- `/clear_memory`: Wipes long-term memories stored for the caller.

### Admin Commands (Server Knowledge)
- `/knowledge_add <key> <value>`: Save server rules, events, or FAQs.
- `/knowledge_remove <key>`: Deletes a knowledge record.
- `/knowledge_list`: List all custom server knowledge taught to Dark-Matter.

---

## Setup Instructions

### Part 1: Discord Portal Setup (Prerequisites)
1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Click **New Application** and name it (e.g. `Dark-Matter`).
3. Navigate to **Bot** in the left menu.
4. Reset/copy the **Token** (this will be your `DISCORD_TOKEN`).
5. Scroll down to **Privileged Gateway Intents** and enable:
   - **Presence Intent**
   - **Server Members Intent** (Required for the welcome system)
   - **Message Content Intent** (Required for reading mentions/replies)
6. Go to **OAuth2 > URL Generator**:
   - Under *Scopes*, check `bot` and `applications.commands`.
   - Under *Bot Permissions*, check:
     - `Send Messages`
     - `Read Message History`
     - `Embed Links`
     - `Use Slash Commands`
7. Copy the generated URL and paste it into your browser to invite Dark-Matter to your server.

---

### Part 2: Local Installation

1. **Clone the Repository** and open the folder.
2. **Setup environment variables**:
   Copy `.env.example` to `.env` and fill in the values:
   ```bash
   cp .env.example .env
   ```
   Edit `.env`:
   - `DISCORD_TOKEN`: Paste your Discord bot token.
   - `GEMINI_API_KEY`: Paste your Google GenAI API key.
   - `BOT_NAME`: `Dark-Matter` (or your custom bot name).

3. **Install Dependencies**:
   It is recommended to use a virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Linux/macOS:
   source venv/bin/activate

   pip install -r requirements.txt
   ```

4. **Run the Bot**:
   ```bash
   python bot.py
   ```
   *Note: On first startup, the bot will automatically compile the SQLite database structure inside `data/database.db` and log connection alerts to `logs/bot.log`.*

---

## Docker Deployment

You can deploy the bot as a container:

1. **Build the Docker Image**:
   ```bash
   docker build -t dark-matter-bot .
   ```

2. **Run the Container**:
   Mount the local directory for persistent database storage:
   ```bash
   docker run -d \
     --name dark-matter-bot \
     --env-file .env \
     -v "$(pwd)/data:/app/data" \
     -v "$(pwd)/logs:/app/logs" \
     dark-matter-bot
   ```

---

## Code Architecture

```
d:\discord.gg-kuhan-ai\
├── bot.py                  # Entrypoint: sets up intents and launches connection
├── config.py               # Loads .env configurations and starts file loggers
├── database.py             # Asynchronous DB execution wrapper using aiosqlite
├── schema.sql              # Database structure
├── requirements.txt        # Python packages
├── Dockerfile              # Container deployment instructions
├── .env.example            # Environment configurations template
│
├── cogs/
│   ├── chat.py             # Event listener for mentions/replies & `/ask` command
│   ├── memory.py           # Commands for viewing and resetting profile/memories
│   ├── moderation.py       # Event listener for member join (welcome greetings)
│   ├── knowledge.py        # Commands for admin guild knowledge updates
│   └── utility.py          # General helper commands
│
├── services/
│   ├── gemini_service.py   # Wrapper for Gemini API calls and content updates
│   ├── memory_service.py   # Coordinates user database history and background updates
│   └── knowledge_service.py# Handles storage operations for guild specific knowledge
│
├── data/                   # Contains persistent sqlite database
└── logs/                   # Contains bot log output (bot.log)
```
