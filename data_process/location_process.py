from typing import List, Tuple
from telebot import types

import keyboard
from db import db
from data_process import dadata_text_clean


def new_location(message: types.Message) -> int:
    """Создание новой геопозиции"""
    _id = message.from_user.id
    loc_id = -1

    # пользователь вводит адрес
    if message.content_type == 'text':
        location = dadata_text_clean.clean_text(message.text)
        loc_id = db.create_location(_id, location)

    # пользователь отправляет геопозицию
    elif message.content_type == 'location':
        location = dadata_text_clean.clean_geolocate(message.json["location"])
        loc_id = db.create_location(_id, location)

    elif message.content_type == 'venue':
        location = db.Location(
            title=message.json['venue']['title'],
            address=message.json['venue']['address'],
            location=message.json['location']
        )
        loc_id = db.create_location(_id, location)

    # пользователь отправляет изображение
    elif message.content_type == 'photo':
        location = db.Location(
            photo=message.json['photo'][0]
        )
        loc_id = db.create_location(_id, location)

    return loc_id


def print_location(loc_id: int) -> Tuple[List, List]:
    """Подготовка данных для карточки геопозиции"""
    location = db.get_location(loc_id)
    if location.photo:
        msg1 = [
            location.photo['file_id'],
            location.title
        ]
    else:
        msg1 = [location.title]

    if location.location:
        msg2 = [
            location.location['latitude'],
            location.location['longitude'],
            location.title,
            location.address
        ]
    else:
        msg2 = None

    return msg1, msg2


def get_location_menu(loc_id: int, msg1_id: int) -> types.InlineKeyboardMarkup:
    """Клавиатура для редактирования геопозиции"""
    return keyboard.get_keyboard(
        1,
        ['Изменить название',
         'Изменить адрес',
         'Изменить изображение',
         'Изменить геопозицию',
         'Удалить'],
        [f'title#{loc_id}#{msg1_id}',
         f'address#{loc_id}#{msg1_id}',
         f'photo#{loc_id}#{msg1_id}',
         f'position#{loc_id}#{msg1_id}',
         f'delete#{loc_id}#{msg1_id}']
    )


def change_title(loc_id: int, title: str) -> str:
    """Изменение названия"""
    location = db.Location(title=title)
    db.update_location(loc_id, location)
    return 'Название успешно изменено!'


def change_address(loc_id: int, address: str) -> str:
    """Изменение адреса"""
    location = dadata_text_clean.clean_text(address)
    db.update_location(loc_id, location)
    return 'Адрес успешно изменен!'


def change_photo(loc_id: int, photo: dict) -> str:
    """Изменение изображения"""
    location = db.Location(photo=photo)
    db.update_location(loc_id, location)
    return 'Изображение успешно изменено!'


def change_location(loc_id: int, message: types.Message) -> str:
    """Изменение геопозиции"""
    location = db.Location()

    if message.content_type == 'location':
        location = dadata_text_clean.clean_geolocate(message.json['location'])

    elif message.content_type == 'venue':
        location.title = message.json['venue']['title']
        location.address = message.json['venue']['address']
        location.location = message.json['location']

    db.update_location(loc_id, location)
    return 'Геопозиция успешно изменена!'


def delete_location(loc_id: int) -> str:
    """Удаление геопозиции"""
    db.delete_location(loc_id)
    return f'Геопозиция {loc_id} успешно удалена!'


def get_location_ids(_id: int) -> List[int]:
    """Получить идентификаторы геопозиций"""
    return db.get_locations_ids(_id)
