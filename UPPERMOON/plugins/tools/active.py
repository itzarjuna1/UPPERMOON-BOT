# Advanced Active VC, Members & Logger with advanced modules 
# Author: Upper Moon Bots | License: GNU v3.0
from typing import List
from unidecode import unidecode
from datetime import datetime

from pyrogram import filters, enums
from pyrogram.types import Message, ChatMemberUpdated

from UPPERMOON import app
from UPPERMOON.misc import SUDOERS
from UPPERMOON.utils.database import (
    get_active_chats,
    get_active_video_chats,
    remove_active_chat,
    remove_active_video_chat,
)


# ------------------------- Helpers ------------------------- #

async def fetch_chat_info(chat_id: int) -> tuple[str, str]:
    """Safely fetch chat title and username"""
    try:
        chat = await app.get_chat(chat_id)
        title = unidecode(chat.title).upper()
        username = chat.username
        return title, username
    except Exception:
        return None, None


async def generate_active_list(
    chat_ids: List[int], remove_func
) -> str:
    """Generate formatted list of active voice/video chats"""
    if not chat_ids:
        return ""

    text_lines = []
    for idx, chat_id in enumerate(chat_ids, start=1):
        title, username = await fetch_chat_info(chat_id)
        if not title:
            await remove_func(chat_id)
            continue

        if username:
            text_lines.append(
                f"<b>{idx}.</b> <a href='https://t.me/{username}'>{title}</a> [<code>{chat_id}</code>]"
            )
        else:
            text_lines.append(f"<b>{idx}.</b> {title} [<code>{chat_id}</code>]")

    return "\n".join(text_lines)


# ------------------------- Active Chats Commands ------------------------- #

@app.on_message(filters.command(["ac"]) & SUDOERS)
async def active_vc(_, message: Message):
    """Quick overview of counts of active voice and video chats"""
    voice_count = len(await get_active_chats())
    video_count = len(await get_active_video_chats())
    await message.reply_text(
        f"<b>» ᴀᴄᴛɪᴠᴇ ᴠᴏɪᴄᴇ ᴄʜᴀᴛs:</b>\n\n"
        f"ᴠᴏɪᴄᴇ: {voice_count}\n"
        f"ᴠɪᴅᴇᴏ: {video_count}"
    )


@app.on_message(filters.command(["activevc", "activevoice"]) & SUDOERS)
async def active_voice_chats(_, message: Message):
    """Show list of active voice chats"""
    reply = await message.reply_text("» ɢᴇᴛᴛɪɴɢ ᴀᴄᴛɪᴠᴇ ᴠᴏɪᴄᴇ ᴄʜᴀᴛs ʟɪsᴛ...")
    active_chats = await get_active_chats()
    text = await generate_active_list(active_chats, remove_active_chat)

    if not text:
        await reply.edit_text(f"» ɴᴏ ᴀᴄᴛɪᴠᴇ ᴠᴏɪᴄᴇ ᴄʜᴀᴛs ᴏɴ {app.mention}.")
    else:
        await reply.edit_text(
            f"<b>» ʟɪsᴛ ᴏғ ᴄᴜʀʀᴇɴᴛʟʏ ᴀᴄᴛɪᴠᴇ ᴠᴏɪᴄᴇ ᴄʜᴀᴛs :</b>\n\n{text}",
            disable_web_page_preview=True,
        )


@app.on_message(filters.command(["activev", "activevideo"]) & SUDOERS)
async def active_video_chats(_, message: Message):
    """Show list of active video chats"""
    reply = await message.reply_text("» ɢᴇᴛᴛɪɴɢ ᴀᴄᴛɪᴠᴇ ᴠɪᴅᴇᴏ ᴄʜᴀᴛs ʟɪsᴛ...")
    active_chats = await get_active_video_chats()
    text = await generate_active_list(active_chats, remove_active_video_chat)

    if not text:
        await reply.edit_text(f"» ɴᴏ ᴀᴄᴛɪᴠᴇ ᴠɪᴅᴇᴏ ᴄʜᴀᴛs ᴏɴ {app.mention}.")
    else:
        await reply.edit_text(
            f"<b>» ʟɪsᴛ ᴏғ ᴄᴜʀʀᴇɴᴛʟʏ ᴀᴄᴛɪᴠᴇ ᴠɪᴅᴇᴏ ᴄʜᴀᴛs :</b>\n\n{text}",
            disable_web_page_preview=True,
        )


# ------------------------- Active VC Members ------------------------- #

@app.on_message(filters.command(["vcmembers"]) & SUDOERS)
async def active_vc_members(_, message: Message):
    """Show list of members currently in the group voice chat"""
    chat_id = message.chat.id
    try:
        participants = await app.get_chat_members(chat_id, filter=enums.ChatMembersFilter.VOICE)
    except Exception:
        return await message.reply_text("» ᴄᴏᴜʟᴅɴ'ᴛ ʀᴇᴛʀɪᴇᴠᴇ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ ᴍᴇᴍʙᴇʀs.")

    if not participants:
        return await message.reply_text("» ɴᴏ ᴍᴇᴍʙᴇʀs ɪɴ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ.")

    text_lines = [f"<b>» ᴠᴏɪᴄᴇ ᴍᴇᴍʙᴇʀs ({len(participants)}):</b>"]
    for idx, member in enumerate(participants, start=1):
        user = member.user
        name = unidecode(user.first_name)
        text_lines.append(f"<b>{idx}.</b> {name} [{user.id}]")

    await message.reply_text("\n".join(text_lines))


# ------------------------- VC Join/Leave Logger ------------------------- #

@app.on_chat_member_updated()
async def vc_logger(_, chat_member_update: ChatMemberUpdated):
    """Log who joined or left the VC directly in the group"""
    chat = chat_member_update.chat
    user = chat_member_update.from_user

    old = chat_member_update.old_chat_member
    new = chat_member_update.new_chat_member

    # Joined VC
    if old.status != enums.ChatMemberStatus.RESTRICTED and new.status == enums.ChatMemberStatus.RESTRICTED:
        # User muted or left VC, ignore
        return
    if new.is_member and not old.is_member:
        await chat.send_message(f"✅ {unidecode(user.first_name)} joined the voice chat.")
    # Left VC
    elif old.is_member and not new.is_member:
        await chat.send_message(f"❌ {unidecode(user.first_name)} left the voice chat.")
