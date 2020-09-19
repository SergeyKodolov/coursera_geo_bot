from telebot import types

from db import db


def set_radius(message: types.Message):
    """Установить значение радиуса поиска ближайших локаций"""
    try:
        radius = int(message.text)
        if 10 <= radius <= 15000:
            _id = message.from_user.id
            db.update_radius(_id, radius)
            return radius
        else:
            return None
    except Exception as ex:
        print(ex)
        return None


def get_ids(user_id, user_location):
    """Формирование списка ближайших местоположений"""
    radius = db.get_radius(user_id)

    locations_ids = db.get_locations_ids(user_id)
    near_locations_ids = db.get_near_locations_ids(user_location, locations_ids, radius)
    return near_locations_ids
