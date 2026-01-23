# all files licensed and ©️ copyrighted 
from typing import Optional

from telegram import Message, Update, Bot, User
from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import BadRequest
from telegram.ext import CommandHandler, run_async, Filters
from telegram.utils.helpers import escape_markdown

from UPPERMOON import dispatcher
from UPPERMOON.mongo import db
from UPPERMOON.modules.helper_funcs.chat_status import user_admin
from UPPERMOON.modules.helper_funcs.string_handling import markdown_parser

# mongodb collection
rules_collection = db.rules


def get_chat_rules(chat_id: int) -> str:
    data = rules_collection.find_one({"_id": chat_id})
    return data.get("rules", "") if data else ""


def set_chat_rules(chat_id: int, rules: str):
    rules_collection.update_one(
        {"_id": chat_id},
        {"$set": {"rules": rules}},
        upsert=True
    )


def clear_chat_rules(chat_id: int):
    rules_collection.delete_one({"_id": chat_id})


@run_async
def get_rules(bot: Bot, update: Update):
    chat_id = update.effective_chat.id
    send_rules(update, chat_id)


# not async
def send_rules(update, chat_id, from_pm=False):
    bot = dispatcher.bot
    user = update.effective_user  # type: Optional[User]

    try:
        chat = bot.get_chat(chat_id)
    except BadRequest as excp:
        if excp.message == "Chat not found" and from_pm:
            bot.send_message(
                user.id,
                "⚠️ ʀᴜʟᴇs sʜᴏʀᴛᴄᴜᴛ ɪs ɴᴏᴛ sᴇᴛ ᴘʀᴏᴘᴇʀʟʏ.\nᴀsᴋ ᴀᴅᴍɪɴs ᴛᴏ ғɪx ɪᴛ."
            )
            return
        raise

    rules = get_chat_rules(chat_id)

    if rules:
        text = "📜 ʀᴜʟᴇs ғᴏʀ *{}*:\n\n{}".format(
            escape_markdown(chat.title),
            rules
        )
    else:
        text = ""

    if from_pm and rules:
        bot.send_message(user.id, text, parse_mode=ParseMode.MARKDOWN)

    elif from_pm:
        bot.send_message(
            user.id,
            "ℹ️ ɴᴏ ʀᴜʟᴇs ʜᴀᴠᴇ ʙᴇᴇɴ sᴇᴛ ғᴏʀ ᴛʜɪs ᴄʜᴀᴛ ʏᴇᴛ."
        )

    elif rules:
        update.effective_message.reply_text(
            "📩 ᴄʟɪᴄᴋ ʙᴇʟᴏᴡ ᴛᴏ ᴠɪᴇᴡ ᴛʜɪs ɢʀᴏᴜᴘ’s ʀᴜʟᴇs.",
            reply_markup=InlineKeyboardMarkup(
                [[
                    InlineKeyboardButton(
                        "📜 ʀᴜʟᴇs",
                        url=f"t.me/{bot.username}?start={chat_id}"
                    )
                ]]
            )
        )

    else:
        update.effective_message.reply_text(
            "ℹ️ ᴛʜᴇ ᴀᴅᴍɪɴs ʜᴀᴠᴇɴ’ᴛ sᴇᴛ ᴀɴʏ ʀᴜʟᴇs ʏᴇᴛ."
        )


@run_async
@user_admin
def set_rules(bot: Bot, update: Update):
    chat_id = update.effective_chat.id
    msg = update.effective_message  # type: Optional[Message]

    args = msg.text.split(None, 1)
    if len(args) != 2:
        return

    raw_text = args[1]
    offset = len(raw_text) - len(msg.text)
    parsed = markdown_parser(
        raw_text,
        entities=msg.parse_entities(),
        offset=offset
    )

    set_chat_rules(chat_id, parsed)
    update.effective_message.reply_text(
        "✅ ʀᴜʟᴇs sᴜᴄᴄᴇssғᴜʟʟʏ sᴇᴛ."
    )


@run_async
@user_admin
def clear_rules(bot: Bot, update: Update):
    chat_id = update.effective_chat.id
    clear_chat_rules(chat_id)
    update.effective_message.reply_text(
        "🧹 ʀᴜʟᴇs ʜᴀᴠᴇ ʙᴇᴇɴ ᴄʟᴇᴀʀᴇᴅ."
    )


def __chat_settings__(chat_id, user_id):
    return "ʀᴜʟᴇs sᴇᴛ: `{}`".format(bool(get_chat_rules(chat_id)))


__help__ = """
 - /rules: ɢᴇᴛ ᴛʜᴇ ʀᴜʟᴇs ғᴏʀ ᴛʜɪs ᴄʜᴀᴛ.

*ᴀᴅᴍɪɴ ᴏɴʟʏ:*
 - /setrules <ʀᴜʟᴇs>: sᴇᴛ ʀᴜʟᴇs.
 - /clearrules: ᴄʟᴇᴀʀ ʀᴜʟᴇs.
"""

__mod_name__ = "Rules"

dispatcher.add_handler(CommandHandler("rules", get_rules, filters=Filters.group))
dispatcher.add_handler(CommandHandler("setrules", set_rules, filters=Filters.group))
dispatcher.add_handler(CommandHandler("clearrules", clear_rules, filters=Filters.group))
