import asyncio
import os
import re
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Load environment variables from a local .env file if present. In production,
# Railway (or your hosting platform) will provide these variables.
load_dotenv()

# Grab required environment variables. The bot will exit if any are missing.
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_CHAT_ID = int(os.getenv("ALLOWED_CHAT_ID", "0"))
OXAAM_EMAIL = os.getenv("OXAAM_USER_EMAIL")
OXAAM_PASSWORD = os.getenv("OXAAM_USER_PASSWORD")

# Target URL for logging into Oxaam
LOGIN_URL = "https://www.oxaam.com/login.php"


def require_env() -> None:
    """Ensure all required environment variables are present."""
    missing = [
        key
        for key, value in {
            "TELEGRAM_BOT_TOKEN": BOT_TOKEN,
            "ALLOWED_CHAT_ID": ALLOWED_CHAT_ID,
            "OXAAM_USER_EMAIL": OXAAM_EMAIL,
            "OXAAM_USER_PASSWORD": OXAAM_PASSWORD,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}"
        )


@asynccontextmanager
async def browser_context():
    """
    Create an async Playwright browser context. This context uses Chromium in
    headless mode and ensures proper cleanup after use.
    """
    async with async_playwright() as p:
        # Launch Chromium headless. The `--no-sandbox` flag is often necessary in
        # container environments like Railway to avoid sandbox issues.
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context()
        try:
            yield context
        finally:
            await context.close()
            await browser.close()


async def fetch_cgai_credentials() -> tuple[str, str]:
    """
    Navigate to the Oxaam dashboard and extract the email and password for the
    free CG‑AI plan from the activation panel. Returns a tuple of
    (email, password) on success or raises an error on failure.
    """
    async with browser_context() as context:
        page = await context.new_page()
        # Navigate to the login page
        await page.goto(LOGIN_URL, timeout=60000)

        # Fill in login credentials. Use flexible selectors in case the input
        # fields have varying names or classes.
        email_selector = 'input[type="email"], input[name*="email" i], input[type="text"]'
        password_selector = 'input[type="password"], input[name*="pass" i]'
        await page.fill(email_selector, OXAAM_EMAIL)
        await page.fill(password_selector, OXAAM_PASSWORD)

        # Click the login button. Look for possible variations in button text.
        await page.get_by_role("button", name=re.compile(r"(sign\s*in|login|ورود)", re.I)).click()

        # Wait until the dashboard is loaded
        await page.wait_for_url(re.compile(r"/dashboard\.php", re.I), timeout=60000)

        # Click the CG-AI activation panel
        await page.get_by_text(re.compile(r"Click Here to Activate\s+CG-AI", re.I)).first.click()

        # Locate the activation panel that contains the credentials
        steps_title = page.get_by_text(re.compile(r"Steps to Activate Free CG-AI", re.I))
        await steps_title.wait_for(timeout=30000)
        panel = steps_title.locator("xpath=..")  # Go to the parent container
        panel_text = await panel.inner_text()

        # Try to extract the email and password using regex
        email_match = re.search(r"Email\s*[→:\-]\s*([^\s]+)", panel_text, flags=re.I)
        password_match = re.search(r"Password\s*[→:\-]\s*([^\s]+)", panel_text, flags=re.I)

        # Fallback regex to extract any email
        if not email_match:
            email_match = re.search(
                r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", panel_text
            )
        # Fallback to extract any non-space token following the word Password
        if not password_match:
            password_match = re.search(r"(?i)Password.*?\b([^\s]+)", panel_text)

        # If still missing, inspect any <code> or <kbd> elements in the panel
        if not (email_match and password_match):
            code_texts = await panel.locator("code, kbd").all_text_contents()
            if len(code_texts) >= 2:
                cg_email = code_texts[0].strip()
                cg_password = code_texts[1].strip()
                return cg_email, cg_password
            raise RuntimeError(
                "Could not parse CG-AI credentials from the activation panel"
            )

        cg_email = email_match.group(1).strip()
        cg_password = password_match.group(1).strip()
        return cg_email, cg_password


def is_allowed(update: Update) -> bool:
    """Check whether the incoming update is from the authorized chat."""
    return update.effective_chat and update.effective_chat.id == ALLOWED_CHAT_ID


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a greeting and brief instructions when the /start command is issued."""
    if not is_allowed(update):
        return
    await update.message.reply_text(
        "سلام! برای دریافت ایمیل و پسورد CG‑AI از دستور /cgai استفاده کنید."
    )


async def cgai(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /cgai command. Fetches the CG‑AI credentials and sends them back to
    the user as a code block. Includes basic error handling and timeout messages.
    """
    if not is_allowed(update):
        return
    msg = await update.message.reply_text(
        "در حال ورود به اکسام و واکشی اطلاعات CG‑AI..."
    )
    try:
        cg_email, cg_password = await fetch_cgai_credentials()
        await context.bot.edit_message_text(
            chat_id=msg.chat.id,
            message_id=msg.message_id,
            text=(
                f"اطلاعات CG‑AI:\nEmail:\n`{cg_email}`\nPassword:\n`{cg_password}`"
            ),
            parse_mode="Markdown",
        )
    except PlaywrightTimeoutError:
        await context.bot.edit_message_text(
            chat_id=msg.chat.id,
            message_id=msg.message_id,
            text="ناموفق: تایم‌اوت هنگام لاگین یا واکشی اطلاعات. بعداً دوباره امتحان کنید.",
        )
    except Exception as e:
        await context.bot.edit_message_text(
            chat_id=msg.chat.id,
            message_id=msg.message_id,
            text=f"ناموفق: {e}",
        )


def main() -> None:
    """Entry point for running the bot."""
    require_env()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cgai", cgai))
    app.run_polling(close_loop=False)


if __name__ == "__main__":
    asyncio.run(main())