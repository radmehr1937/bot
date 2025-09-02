# CG‑AI Telegram Bot

This repository contains a simple Telegram bot that automates the process of logging into your
personal account on **Oxaam** and extracting the credentials for the free CG‑AI plan.
When you send the `/cgai` command to the bot, it logs in to `oxaam.com`,
opens the CG‑AI activation panel, and returns the public email and password
for the CG‑AI service.

> **Disclaimer**
>
> 1. This project is intended for educational purposes only. Please ensure that using
>    automated logins or scraping credentials complies with Oxaam’s terms of service and
>    any applicable laws and regulations.
> 2. You must supply your own Oxaam account credentials via environment variables. Do **not**
>    commit them to this repository or expose them publicly. Use the provided
>    `.env.example` as a template.
> 3. The CG‑AI credentials provided by Oxaam are public/shared. Use them responsibly
>    and avoid sharing with unauthorized parties.

## Features

- Uses the [`python-telegram-bot`](https://python-telegram-bot.org/) library to handle
  Telegram updates asynchronously【628509785262377†L17-L29】.
- Automates browser actions with [Playwright](https://playwright.dev/python/) to log into
  Oxaam and fetch the free CG‑AI account details.
- Stores configuration via environment variables so you can deploy to
  platforms like [Railway](https://railway.app).

## Usage

### 1. Configure your environment

Create a `.env` file based on the provided `.env.example` and set the following variables:

```
TELEGRAM_BOT_TOKEN=<your‑telegram‑bot‑token>
ALLOWED_CHAT_ID=<your‑telegram‑chat‑id>
OXAAM_USER_EMAIL=<your‑oxaam‑login‑email>
OXAAM_USER_PASSWORD=<your‑oxaam‑login‑password>
```

`ALLOWED_CHAT_ID` ensures that only your chat receives the bot’s response.

### 2. Install dependencies (for local development)

```bash
pip install -r requirements.txt
playwright install --with-deps chromium  # if not already installed
```

### 3. Run locally

```bash
python bot.py
```

Start chatting with your bot on Telegram and send `/cgai` to retrieve the CG‑AI credentials.

### 4. Deployment on Railway

Railway makes it easy to deploy directly from a GitHub repository. Follow these steps:

1. Create a new project on Railway and select **Deploy from GitHub repo**【428973097759863†L111-L124】.
2. Connect your GitHub account and choose this repository.
3. Railway detects the `Dockerfile` and builds the container. Ensure you set the
   environment variables (`TELEGRAM_BOT_TOKEN`, `ALLOWED_CHAT_ID`, `OXAAM_USER_EMAIL`,
   `OXAAM_USER_PASSWORD`) in the **Variables** section of the project.
4. Once deployed, the bot will start polling Telegram and is ready to use.

### 5. Notes

- The bot uses a headless Chromium instance, which may require extra flags in some
  containers. This Dockerfile includes `--no-sandbox` for compatibility.
- Railway’s free tier may go to sleep after inactivity. Consider upgrades if you
  need 24/7 availability.
- If Oxaam introduces CAPTCHA, 2‑factor authentication, or other protections,
  the Playwright automation may fail. You will need to manually handle those cases or
  use a session cookie saved in the container.

## License

This project is licensed under the MIT License. See `LICENSE` for details.