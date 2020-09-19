from db import db


def check(_id: int):
    """Создание пользователя, если не существует"""
    if not db.is_there_user(_id):
        db.create_user(_id)


def delete(_id: int):
    """Удаление пользователя"""
    if db.is_there_user(_id):
        db.delete_user_data(_id)
