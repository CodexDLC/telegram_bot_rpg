
from typing import Optional

from aiogram.types import User, Message, Chat


class MessageInfoFormatter:
    """Форматтер для красивого вывода информации о сообщении Telegram"""

    def _format_user_info(self, user: User) -> str:
        """Форматирует информацию о пользователе"""
        info = f"👤 <b>Пользователь:</b>\n"
        info += f"  • ID: <code>{user.id}</code>\n"
        info += f"  • Username: @{user.username}\n" if user.username else ""
        info += f"  • Имя: {user.first_name}"
        info += f" {user.last_name}" if user.last_name else ""
        info += f"\n  • Бот: {'Да' if user.is_bot else 'Нет'}\n"
        return info

    def _format_chat_info(self, chat: Chat, message_thread_id: Optional[int] = None) -> str:
        """Форматирует информацию о чате"""
        chat_types = {
            'private': '💬 Личный чат',
            'group': '👥 Группа',
            'supergroup': '👥 Супергруппа',
            'channel': '📢 Канал'
        }

        info = f"📍 <b>Чат:</b>\n"
        info += f"  • ID: <code>{chat.id}</code>\n"
        info += f"  • Тип: {chat_types.get(chat.type, chat.type)}\n"

        if chat.title:
            info += f"  • Название: {chat.title}\n"
        if chat.username:
            info += f"  • Username: @{chat.username}\n"
        if message_thread_id:
            info += f"  • ID топика: <code>{message_thread_id}</code>\n"

        return info

    def _format_message_info(self, message: Message) -> str:
        """Форматирует информацию о сообщении"""
        info = f"✉️ <b>Сообщение:</b>\n"
        info += f"  • ID: <code>{message.message_id}</code>\n"
        info += f"  • Дата: {message.date.strftime('%d.%m.%Y %H:%M:%S')}\n"

        if message.reply_to_message:
            info += f"  • Ответ на: <code>{message.reply_to_message.message_id}</code>\n"

        return info

    @staticmethod
    def format_full_info(message: Message) -> str:
        """Полная информация о сообщении в красивом формате"""
        formatter = MessageInfoFormatter()
        parts = []

        if message.from_user:
            parts.append(formatter._format_user_info(message.from_user))

        parts.append(formatter._format_chat_info(
            message.chat,
            message.message_thread_id
        ))

        parts.append(formatter._format_message_info(message))

        # Дополнительная информация
        extras = []
        if message.text:
            extras.append(f"📝 Текст: {message.text[:50]}..." if len(message.text) > 50 else f"📝 Текст: {message.text}")
        if message.photo:
            extras.append("🖼 Содержит фото")
        if message.document:
            extras.append(f"📎 Документ: {message.document.file_name}")
        if message.forward_date:
            extras.append("↪️ Пересланное сообщение")

        if extras:
            parts.append("ℹ️ <b>Дополнительно:</b>\n  • " + "\n  • ".join(extras))

        return "\n\n".join(parts)

    @staticmethod
    def format_chat_ids_only(message: Message) -> str:
        """Только ID для быстрого копирования"""
        info = "🆔 <b>ID для копирования:</b>\n\n"
        info += f"Chat ID: <code>{message.chat.id}</code>\n"

        if message.message_thread_id:
            info += f"Thread ID: <code>{message.message_thread_id}</code>\n"

        if message.from_user:
            info += f"User ID: <code>{message.from_user.id}</code>\n"

        return info