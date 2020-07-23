import json
import os
from dadata import Dadata
from telebot import types
from vars import DADATA_SECRET_KEY, DADATA_TOKEN

dadata_secret_key = os.getenv('DADATA_SECRET_KEY') or DADATA_SECRET_KEY
dadata_token = os.getenv('DADATA_TOKEN') or DADATA_TOKEN
dadata = Dadata(dadata_token, dadata_secret_key)


def get_keyboard(row, buttons, callback_data):
    """Инициализирует клавиатуру обработки геопозиуии от пользователя"""
    keyboard = types.InlineKeyboardMarkup(row_width=row)
    buttons = [types.InlineKeyboardButton(text=text, callback_data=data or text)
               for text, data in zip(buttons, callback_data)]
    keyboard.add(*buttons)
    return keyboard


def clean_text(message):
    """Возвращает местоположение по введенному тексту"""
    title = message.text
    address = None
    location = None

    result = dadata.clean('address', message.text)
    if result is not None:
        address = result['result']
        if result["geo_lat"] is not None and result["geo_lon"] is not None:
            location = json.dumps(
                {'latitude': float(result["geo_lat"]),
                 'longitude': float(result["geo_lon"])}
            )

    return title, address, location


def clean_geolocate(message):
    """Возвращает адрес и локацию по координатам"""
    geo_lat, geo_lon = message.json["location"]["latitude"], message.json["location"]["longitude"]
    result = dadata.geolocate(name='address', lat=geo_lat, lon=geo_lon)

    if len(result) > 0:
        address = result[0]['value']
    else:
        address = f'{message.json["location"]["latitude"]}, ' \
                  f'{message.json["location"]["longitude"]}'
    location = json.dumps(message.json['location'])

    return address, location
