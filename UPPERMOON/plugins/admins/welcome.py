import html
from enum import Enum
from typing import List

from telegram import (
    Update,
    Bot,
    InlineKeyboardMarkup,
    ParseMode,
)
from telegram.error import BadRequest
from telegram.utils.helpers import (
    mention_markdown,
    mention_html,
    escape_markdown,
)

from UPPERMOON import dispatcher, OWNER_ID
from UPPERMOON.mongo import db
from UPPERMOON.plugins.helper.chat_status import user_admin
from UPPERMOON.plugins.helper.misc import build_keyboard
from UPPERMOON.plugins.helper.msg_types import get_welcome_type
from UPPERMOON.plugins.helper.string_handling import (
    markdown_parser,
    escape_invalid_curly_brackets,
)
from UPPERMOON.plugins.log_channel import loggable


# ───────────────── SMALL CAPS ───────────────── #

_SMALL_CAPS = {
    "a": "ᴀ", "b": "ʙ", "c": "ᴄ", "d": "ᴅ", "e": "ᴇ",
    "f": "ғ", "g": "ɢ", "h": "ʜ", "i": "ɪ", "j": "ᴊ",
    "k": "ᴋ", "l": "ʟ", "m": "ᴍ", "n": "ɴ", "o": "ᴏ",
    "p": "ᴘ", "q": "ǫ", "r": "ʀ", "s": "s", "t": "ᴛ",
    "u": "ᴜ", "v": "ᴠ", "w": "ᴡ", "x": "x", "y": "ʏ",
    "z": "ᴢ",
}

def sc(text: str) -> str:
    return "".join(_SMALL_CAPS.get(c.lower(), c) for c in text)


# ───────────────── TYPES ───────────────── #

class Types(Enum):
    TEXT = "text"
    BUTTON_TEXT = "button_text"
    STICKER = "sticker"
    DOCUMENT = "document"
    PHOTO = "photo"
    AUDIO = "audio"
    VOICE = "voice"
    VIDEO = "video"


# ───────────────── DATABASE ───────────────── #

WELCOME_DB = db.welcome

DEFAULT_WELCOME = "ʜᴇʏ {{first}}, ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ {{chatname}}!"
DEFAULT_GOODBYE = "ɢᴏᴏᴅʙʏᴇ {{first}}!"

VALID_WELCOME_FORMATTERS = [
    "first", "last", "fullname", "username",
    "id", "count", "chatname", "mention",
]

ENUM_FUNC_MAP = {
    Types.TEXT.value: dispatcher.bot.send_message,
    Types.BUTTON_TEXT.value: dispatcher.bot.send_message,
    Types.STICKER.value: dispatcher.bot.send_sticker,
    Types.DOCUMENT.value: dispatcher.bot.send_document,
    Types.PHOTO.value: dispatcher.bot.send_photo,
    Types.AUDIO.value: dispatcher.bot.send_audio,
    Types.VOICE.value: dispatcher.bot.send_voice,
    Types.VIDEO.value: dispatcher.bot.send_video,
}


def get_settings(chat_id: int) -> dict:
    data = WELCOME_DB.find_one({"chat_id": chat_id})
    if not data:
        data = {
            "chat_id": chat_id,
            "welcome_enabled": True,
            "welcome_text": DEFAULT_WELCOME,
            "welcome_type": Types.TEXT.value,
            "welcome_buttons": [],
            "goodbye_enabled": False,
            "goodbye_text": DEFAULT_GOODBYE,
            "goodbye_type": Types.TEXT.value,
            "goodbye_buttons": [],
            "clean_welcome": False,
            "last_welcome_msg_id": None,
        }
        WELCOME_DB.insert_one(data)
    return data


def update_settings(chat_id: int, **kwargs):
    WELCOME_DB.update_one(
        {"chat_id": chat_id},
        {"$set": kwargs},
        upsert=True,
    )


# ───────────────── SEND ───────────────── #

def send(update: Update, text: str, keyboard, backup: str):
    try:
        return update.effective_message.reply_text(
            sc(text),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard,
        )
    except Exception:
        return update.effective_message.reply_text(
            sc(markdown_parser(backup)),
            parse_mode=ParseMode.MARKDOWN,
        )


# ───────────────── NEW MEMBER ───────────────── #

def new_member(bot: Bot, update: Update):
    chat = update.effective_chat
    settings = get_settings(chat.id)

    if not settings["welcome_enabled"]:
        return

    for user in update.effective_message.new_chat_members:
        if user.id in (OWNER_ID, bot.id):
            continue

        if settings["welcome_type"] not in (Types.TEXT.value, Types.BUTTON_TEXT.value):
            ENUM_FUNC_MAP[settings["welcome_type"]](chat.id, settings["welcome_text"])
            return

        first = user.first_name or "User"
        last = user.last_name or first
        fullname = f"{first} {user.last_name}" if user.last_name else first
        mention = mention_markdown(user.id, first)
        username = f"@{escape_markdown(user.username)}" if user.username else mention

        text = escape_invalid_curly_brackets(
            settings["welcome_text"],
            VALID_WELCOME_FORMATTERS,
        ).format(
            first=escape_markdown(first),
            last=escape_markdown(last),
            fullname=escape_markdown(fullname),
            username=username,
            mention=mention,
            count=chat.get_members_count(),
            chatname=escape_markdown(chat.title),
            id=user.id,
        )

        keyboard = InlineKeyboardMarkup(
            build_keyboard(settings["welcome_buttons"])
        )

        sent = send(update, text, keyboard, DEFAULT_WELCOME)

        if settings["clean_welcome"] and settings["last_welcome_msg_id"]:
            try:
                bot.delete_message(chat.id, settings["last_welcome_msg_id"])
            except BadRequest:
                pass

        update_settings(chat.id, last_welcome_msg_id=sent.message_id)


# ───────────────── LEFT MEMBER ───────────────── #

def left_member(bot: Bot, update: Update):
    chat = update.effective_chat
    user = update.effective_message.left_chat_member

    if not user or user.id == bot.id:
        return

    settings = get_settings(chat.id)
    if not settings["goodbye_enabled"]:
        return

    ENUM_FUNC_MAP[settings["goodbye_type"]](
        chat.id,
        sc(settings["goodbye_text"]),
        parse_mode=ParseMode.MARKDOWN,
    )


# ───────────────── ADMIN COMMANDS ───────────────── #

@user_admin
@loggable
def set_welcome(bot: Bot, update: Update) -> str:
    chat = update.effective_chat
    user = update.effective_user

    text, t, content, buttons = get_welcome_type(update.effective_message)

    update_settings(
        chat.id,
        welcome_text=content or text,
        welcome_type=t,
        welcome_buttons=buttons,
    )

    update.effective_message.reply_text(sc("welcome message updated!"))

    return (
        f"<b>{html.escape(chat.title)}</b>\n"
        f"#SET_WELCOME\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}"
    )


@user_admin
@loggable
def reset_welcome(bot: Bot, update: Update) -> str:
    chat = update.effective_chat
    user = update.effective_user

    update_settings(
        chat.id,
        welcome_text=DEFAULT_WELCOME,
        welcome_type=Types.TEXT.value,
        welcome_buttons=[],
    )

    update.effective_message.reply_text(sc("welcome reset to default!"))

    return (
        f"<b>{html.escape(chat.title)}</b>\n"
        f"#RESET_WELCOME\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}"
)
