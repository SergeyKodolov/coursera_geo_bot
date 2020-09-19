from typing import Dict

from db import db
from vars import EMPTY


def check_user(chat_id: int) -> Dict:
    """Проверяет существование пользователя"""
    if not db.is_there_user(chat_id):
        return {
            'chat_id': chat_id,
            'text': 'Произошла ошибка :(\n\n'
                    'Воспользуйтесь командой /start'
        }


def check_locations(chat_id: int) -> Dict:
    """Проверяет существование местоположений"""
    if not db.are_there_locations(chat_id):
        return {
            'chat_id': chat_id,
            'text': EMPTY
        }