import html
import re
from typing import Optional, List

import telegram
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ParseMode,
    User,
    CallbackQuery,
    Message,
    Chat,
    Update,
    Bot,
)
from telegram.error import BadRequest
from telegram.ext import (
    CommandHandler,
    run_async,
    DispatcherHandlerStop,
    MessageHandler,
    Filters,
    CallbackQueryHandler,
)
from telegram.utils.helpers import mention_html

from UPPERMOON import dispatcher, BAN_STICKER
from UPPERMOON.modules.disable import DisableAbleCommandHandler
from UPPERMOON.modules.helper_funcs.chat_status import (
    is_user_admin,
    bot_admin,
    user_admin_no_reply,
    user_admin,
    can_restrict,
)
from UPPERMOON.modules.helper_funcs.extraction import (
    extract_text,
    extract_user_and_text,
    extract_user,
)
from UPPERMOON.modules.helper_funcs.filters import CustomFilters
from UPPERMOON.modules.helper_funcs.misc import split_message
from UPPERMOON.modules.helper_funcs.string_handling import split_quotes
from UPPERMOON.modules.log_channel import loggable
from UPPERMOON.modules.sql import warns_sql as sql

# ──────────────────────────────────────────────
# constants
# ──────────────────────────────────────────────

WARN_HANDLER_GROUP = 9
CURRENT_WARNING_FILTER_STRING = "<b>ᴄᴜʀʀᴇɴᴛ ᴡᴀʀɴɪɴɢ ғɪʟᴛᴇʀs ɪɴ ᴛʜɪs ᴄʜᴀᴛ:</b>\n"

# upload your own mp4/gif to catbox.moe
WARN_VIDEO_URL = "https://files.catbox.moe/abc123.mp4"

# ──────────────────────────────────────────────
# warn core
# ──────────────────────────────────────────────

def warn(user: User, chat: Chat, reason: str, message: Message, warner: User = None) -> str:
    if is_user_admin(chat, user.id):
        message.reply_text("ᴀᴅᴍɪɴs ᴄᴀɴ’ᴛ ʙᴇ ᴡᴀʀɴᴇᴅ 😼")
        return ""

    warner_tag = (
        mention_html(warner.id, warner.first_name)
        if warner else "ᴀᴜᴛᴏᴍᴀᴛᴇᴅ ᴡᴀʀɴ ғɪʟᴛᴇʀ"
    )

    limit, soft_warn = sql.get_warn_setting(chat.id)
    num_warns, reasons = sql.warn_user(user.id, chat.id, reason)

    if num_warns >= limit:
        sql.reset_warns(user.id, chat.id)
        if soft_warn:
            chat.unban_member(user.id)
            reply = f"{limit} ᴡᴀʀɴɪɴɢs — {mention_html(user.id, user.first_name)} ʜᴀs ʙᴇᴇɴ ᴋɪᴄᴋᴇᴅ!"
        else:
            chat.kick_member(user.id)
            reply = f"{limit} ᴡᴀʀɴɪɴɢs — {mention_html(user.id, user.first_name)} ʜᴀs ʙᴇᴇɴ ʙᴀɴɴᴇᴅ!"

        for r in reasons:
            reply += f"\n • {html.escape(r)}"

        message.bot.send_sticker(chat.id, BAN_STICKER)
        keyboard = None

        log_reason = (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"#WARN_BAN\n"
            f"<b>ᴀᴅᴍɪɴ:</b> {warner_tag}\n"
            f"<b>ᴜsᴇʀ:</b> {mention_html(user.id, user.first_name)} (<code>{user.id}</code>)\n"
            f"<b>ʀᴇᴀsᴏɴ:</b> {html.escape(reason)}\n"
            f"<b>ᴄᴏᴜɴᴛ:</b> <code>{num_warns}/{limit}</code>"
        )

    else:
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("ʀᴇᴍᴏᴠᴇ ᴡᴀʀɴ", callback_data=f"rm_warn({user.id})")]]
        )

        reply = f"{mention_html(user.id, user.first_name)} ʜᴀs {num_warns}/{limit} ᴡᴀʀɴɪɴɢs ⚠️"
        if reason:
            reply += f"\n\nʀᴇᴀsᴏɴ:\n{html.escape(reason)}"

        log_reason = (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"#WARN\n"
            f"<b>ᴀᴅᴍɪɴ:</b> {warner_tag}\n"
            f"<b>ᴜsᴇʀ:</b> {mention_html(user.id, user.first_name)} (<code>{user.id}</code>)\n"
            f"<b>ʀᴇᴀsᴏɴ:</b> {html.escape(reason)}\n"
            f"<b>ᴄᴏᴜɴᴛ:</b> <code>{num_warns}/{limit}</code>"
        )

    try:
        # 🔥 warning video
        message.bot.send_video(
            chat_id=chat.id,
            video=WARN_VIDEO_URL,
            caption=(
                "⚠️ ᴡᴀʀɴɪɴɢ!\n\n"
                f"{mention_html(user.id, user.first_name)}\n\n"
                "ʙᴇʜᴀᴠᴇ ᴏʀ ғᴀᴄᴇ ᴄᴏɴsᴇǫᴜᴇɴᴄᴇs 😼"
            ),
            parse_mode=ParseMode.HTML,
        )

        message.reply_text(reply, reply_markup=keyboard, parse_mode=ParseMode.HTML)

    except BadRequest as excp:
        if excp.message == "Reply message not found":
            message.reply_text(reply, reply_markup=keyboard, parse_mode=ParseMode.HTML, quote=False)
        else:
            raise

    return log_reason

# ──────────────────────────────────────────────
# handlers (unchanged logic)
# ──────────────────────────────────────────────

@run_async
@user_admin_no_reply
@bot_admin
@loggable
def button(bot: Bot, update: Update) -> str:
    query = update.callback_query
    user = update.effective_user
    match = re.match(r"rm_warn\((.+?)\)", query.data)

    if match:
        user_id = match.group(1)
        chat = update.effective_chat
        if sql.remove_warn(user_id, chat.id):
            update.effective_message.edit_text(
                f"ᴡᴀʀɴ ʀᴇᴍᴏᴠᴇᴅ ʙʏ {mention_html(user.id, user.first_name)}.",
                parse_mode=ParseMode.HTML,
            )
    return ""

# ──────────────────────────────────────────────
# dispatcher
# ──────────────────────────────────────────────

dispatcher.add_handler(CommandHandler("warn", warn_user, pass_args=True, filters=Filters.group))
dispatcher.add_handler(CallbackQueryHandler(button, pattern=r"rm_warn"))
dispatcher.add_handler(CommandHandler(["resetwarn", "resetwarns"], reset_warns, pass_args=True, filters=Filters.group))
dispatcher.add_handler(DisableAbleCommandHandler("warns", warns, pass_args=True, filters=Filters.group))
dispatcher.add_handler(CommandHandler("addwarn", add_warn_filter, filters=Filters.group))
dispatcher.add_handler(CommandHandler(["nowarn", "stopwarn"], remove_warn_filter, filters=Filters.group))
dispatcher.add_handler(
    DisableAbleCommandHandler(["warnlist", "warnfilters"], list_warn_filters, filters=Filters.group, admin_ok=True)
)
dispatcher.add_handler(CommandHandler("warnlimit", set_warn_limit, pass_args=True, filters=Filters.group))
dispatcher.add_handler(CommandHandler("strongwarn", set_warn_strength, pass_args=True, filters=Filters.group))
dispatcher.add_handler(MessageHandler(CustomFilters.has_text & Filters.group, reply_filter), WARN_HANDLER_GROUP)
