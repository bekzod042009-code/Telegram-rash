"""Telegram bot (aiogram, long polling): /start, /id, menyu tugmasi va xabarnomalar."""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup, MenuButtonWebApp, Message,
                           WebAppInfo)

from . import config, db

log = logging.getLogger("bot")
bot: Bot | None = None
username = ""


async def _save_referral(invitee: int, payload: str):
    ref = payload.removeprefix("ref")
    if not (payload.startswith("ref") and ref.isascii() and ref.isdigit() and len(ref) < 19):
        return
    if int(ref) == invitee:
        return
    await db.pool.execute(
        """INSERT INTO referrals(invitee_tg, referrer_tg)
           SELECT $1, $2 WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE tg_id = $1)
           ON CONFLICT (invitee_tg) DO NOTHING""", invitee, int(ref))


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def start(message: Message, command: CommandObject):
        if message.chat.type != "private":
            return
        if command.args:
            await _save_referral(message.from_user.id, command.args)
        if not config.WEBAPP_URL.startswith("https://"):
            await message.answer("Ilova manzili hali sozlanmagan.")
            return
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(
            text="Ilovani ochish", web_app=WebAppInfo(url=config.WEBAPP_URL))]])
        await message.answer("Rash yordamchi: test yarating va yeching.", reply_markup=keyboard)

    @dp.message(Command("id"))
    async def my_id(message: Message):
        await message.answer(f"Sizning Telegram ID: {message.from_user.id}")

    return dp


async def run():
    """Server bilan birga ishlaydi. Xato bo'lsa server to'xtamaydi, bot qayta urinadi."""
    global bot, username
    if not config.BOT_TOKEN:
        log.warning("BOT_TOKEN yo'q: bot ishga tushmadi.")
        return
    dp = build_dispatcher()
    while True:
        try:
            bot = Bot(config.BOT_TOKEN)
            username = (await bot.get_me()).username or ""
            await bot.delete_webhook()
            if config.WEBAPP_URL.startswith("https://"):
                await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(
                    text="Ochish", web_app=WebAppInfo(url=config.WEBAPP_URL)))
            else:
                log.warning("WEBAPP_URL yo'q: Railway'da domen yarating va qayta deploy qiling.")
            await dp.start_polling(bot, handle_signals=False, close_bot_session=False)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.error("Bot xatosi: %s. 30 soniyadan keyin qayta urinadi.", type(e).__name__)
        finally:
            if bot:
                await bot.session.close()
        await asyncio.sleep(30)


_tasks: set[asyncio.Task] = set()


async def _send(chat_id: int, text: str):
    try:
        await bot.send_message(chat_id, text)
    except Exception:
        log.info("Xabar yuborilmadi: %s", chat_id)


def notify(chat_ids, text: str):
    if not bot:
        return
    for chat_id in chat_ids:
        task = asyncio.create_task(_send(chat_id, text))
        _tasks.add(task)
        task.add_done_callback(_tasks.discard)
