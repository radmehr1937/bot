import asyncio
import os
import re
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Load environment variables from .env
load_dotenv()

# Required environment variables
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_CHAT_ID = int(os.getenv("ALLOWED_CHAT_ID", "0"))
OXAAM_EMAIL = os.getenv("OXAAM_USER_EMAIL")
OXAAM_PASSWORD = os.getenv("OXAAM_USER_PASSWORD")

# Proxy environment variables
PROXY_SERVER = os.getenv("PROXY_SERVER")   # مثل: http://brd.superproxy.io:33335
PROXY_USER = os.getenv("PROXY_USER")       # یوزرنیم پراکسی
PROXY_PASS = os.getenv("PROXY_PASS")       # پسورد پراکسی

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
            "PROXY_SERVER": PROXY_SERVER,
            "PROXY_USER": PROXY_USER,
            "PROXY_PASS": PROXY_PASS,
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
    Create an async Playwright browser context with proxy support
    and ignore SSL errors to prevent ERR_CERT_AUTHORITY_INVALID.
    """
    async with async_playwright() as p:
        proxy_settings = {
            "server": PROXY_SERVER,
            "username": PROXY_USER,
            "password": PROXY_PASS,
        }

        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--ignore-certificate-errors"]
        )
        context = await browser.new_context(
            proxy=proxy_settings,
            ignore_https_errors=True
        )
        try:
            yield context
        finally:
            await context.close()
            await browser.close()


async def fetch_cgai_credentials() -> tuple[str, str]:
    """Login to Oxaam, navigate to CG-AI panel, and scrape credentials."""
    async with browser_context() as context:
        page = await context.new_page()
        await page.goto(LOGIN_URL, timeout=60000)

        # Fill login form
        email_selector = 'input[type="email"], input[name*="email" i], input[type="text"]'
        password_selector = 'input[type="password"], input[name*="pass" i]'
        await page.fill(email_selector, OXAAM_EMAIL)
        await page.fill(password_selector, OXAAM_PASSWORD)

        # Login button
        await page.get_by_role("button", name=re.compile(r"(sign\s*in|login|ورود)", re.I)).click()

        # Wait until dashboard
        await page.wait_for_url(re.compile(r"/dashboard\.php", re.I), timeout=60000)

        # Click CG-AI activation panel
        await page.get_by_text(re.compile(r"Click Here to Activate\s+CG-AI", re.I)).first.click()

        steps_title = page.get_by_text(re.compile(r"Steps to Activate Free CG-AI", re.I))
        await steps_title.wait_for(timeout=30000)
        panel = steps_title.locator("xpath=..")  
        panel_text = await panel.inner_text()

        # Regex extraction
        email_match = re.search(r"Email\s*[→:\-]\s*([^\s]+)", panel_text, flags=re.I)
        password_match = re.search(r"Password\s*[→:\-]\s*([^\s]+)", panel_text, flags=re.I)

        if not email_match:
            email_match = re.search(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", panel_text)
        if not password_match:
            password_match = re.search(r"(?i)Password.*?\b([^\s]+)", panel_text)

        if not (email_match and password_match):
            code_texts = await panel.locator("code, kbd").all_text_contents()
            if len(code_texts) >= 2:
                return code_texts[0].strip(), code_texts[1].strip()
            raise RuntimeError("Could not parse CG-AI credentials")

        return email_match.group(1).strip(), password_match.group(1).strip()


def is_allowed(update: Update) -> bool:
    return update.effective_chat and update.effective_chat.id == ALLOWED_CHAT_ID


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return
    await update.message.reply_text("سلام! برای دریافت ایمیل و پسورد CG‑AI از دستور /cgai استفاده کنید.")


async def cgai(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return
    msg = await update.message.reply_text("در حال ورود به اکسام و واکشی اطلاعات CG‑AI...")
    try:
        cg_email, cg_password = await fetch_cgai_credentials()
        await context.bot.edit_message_text(
            chat_id=msg.chat.id,
            message_id=msg.message_id,
            text=f"اطلاعات CG‑AI:\nEmail:\n`{cg_email}`\nPassword:\n`{cg_password}`",
            parse_mode="Markdown",
        )
    except PlaywrightTimeoutError:
        await context.bot.edit_message_text(
            chat_id=msg.chat.id,
            message_id=msg.message_id,
            text="⏳ ناموفق: تایم‌اوت هنگام لاگین یا واکشی اطلاعات.",
        )
    except Exception as e:
        await context.bot.edit_message_text(
            chat_id=msg.chat.id,
            message_id=msg.message_id,
            text=f"❌ خطا: {e}",
        )


def main() -> None:
    require_env()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cgai", cgai))
    app.run_polling(close_loop=False)


if __name__ == "__main__":
    asyncio.run(main())
