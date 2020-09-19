from typing import List

from telebot import types


def get_keyboard(row: int, buttons: List[str], callback_data: List[str]) -> types.InlineKeyboardMarkup:
    """Инициализирует пользовательскую клавиатуру"""
    keyboard = types.InlineKeyboardMarkup(row_width=row)
    buttons = [types.InlineKeyboardButton(text=text, callback_data=data or text)
               for text, data in zip(buttons, callback_data)]
    keyboard.add(*buttons)
    return keyboard