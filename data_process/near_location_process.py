from typing import List

from telebot import types
from haversine import haversine, Unit

from db import db


def set_radius(message: types.Message):
    """Установить значение радиуса поиска ближайших геопозиций"""
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
    """Формирование списка ближайших геопозиций"""
    radius = db.get_radius(user_id)

    locations_ids = db.get_locations_ids(user_id)
    near_locations_ids = get_near_locations_ids(user_location, locations_ids, radius)
    return near_locations_ids


def get_near_locations_ids(user_location: int, locations_ids: List[int], radius: float) -> List[int]:
    """Возвращает массив ближайших местоположений"""
    near_locations_ids = []
    for location_id in locations_ids:
        location = db.get_location(location_id)
        if location.location:
            coord = (
                location.location['latitude'],
                location.location['longitude']
            )
            dist = haversine(coord, user_location, unit=Unit.METERS)
            if dist <= radius:
                near_locations_ids.append(location_id)

    return near_locations_ids
