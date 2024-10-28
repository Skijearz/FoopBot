# Foop - Discord Bot

Foop(the anti Poof) is a Discord bot built with Python using the `discord.py` library. The bot includes various features (e.g., moderation, entertainment, music controls, etc.) to enhance the experience on Discord servers.
The bot is intended for my personal use only but see [Installation](#installation) if you want to host it yourself.

## Table of Contents

- [About the Project](#about-the-project)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
---

## About the Project

This bot is developed using the `discord.py` library and offers a variety of functionalities to improve server management and interaction on Discord.
Every feature is just something i imagined to be a handy or funny tool for myself and friends on our Discord Servers. 
Uses various API's and therefore needs some API_KEYS to work (e.g. YouTube,Twitch,Steam,DofusDB)

---

## Features
- **Twitch**: Post a notification to a desired channel if a streamer goes Live
- **YouTube**: Post a notification to a desired channel if a new video of a selected channel is uploaded
- **Music Control**: Play, pause, and stop music from YouTube
- **Dofus**: Post the Daily Almanax of the Games to a channel
- **Steam**: Notify a user if a perfect game on steam gets new achievements
- **Short**: Creates a short link of a url using my simple SHORTENER repo.
---

## Prerequisites

- Python 3.8 or higher
- `discord.py` library (`pip install discord.py` for the music stuff, the voice part of discord.py is necessesary)
- The Music part needs ffmpeg to be installed on the machine to work!

---

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Skijearz/FoopBot.git
   cd FoopBot
    ```
2. **Create and activate a virtual environment (recommended):**
   ```bash
    python3 -m venv venv
    source venv/bin/activate  # for Mac/Linux
    venv\Scripts\activate  # for Windows
    ```

3. **Install dependencies:**
   ```bash
    pip install -r requirements.txt
   ```
4. **Get a Discord Bot Token:**
  - Create an application on the Discord [Discord Developer Portal](https://discord.com/developers)
  - Set up a bot under this application and copy the bot token
5. **Get Various other Tokens:**
    - YouTube
    - Twitch
    - Steam

## Configuration
1. **Add Tokens to the Bot**: create a `config.py` file in the root directory and add them like this:
  ```python
    TOKEN = ""
    YOUTUBE_API_TOKEN =""
    TWITCH_API_TOKEN =""
    TWITCH_API_CHANNEL_ID =""
    STEAM_WEB_API_KEY =""
```

## Usage
**Run Foop**: Use the following command to start the bot
  ```bash
    python Foop.py
 ```
**Docker usage**: To isolate the Bot into a Docker Container, the repository includes a basic dockerfile aswell as a dockercompose config. Either edit them to your liking or use the following command to use the basic configs
  ```bash
    docker compose build
    docker compose up -d
   ```
**Commands**: All the commands available are discord slash commands so you can get a preview of all commands if you type `/` into the chat.
