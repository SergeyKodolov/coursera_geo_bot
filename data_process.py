from haversine import haversine, Unit
from telebot import types
import json


def get_keyboard(row, buttons, callback_data):
    """Инициализирует клавиатуру обработки геопозиуии от пользователя"""
    keyboard = types.InlineKeyboardMarkup(row_width=row)
    buttons = [types.InlineKeyboardButton(text=text, callback_data=data or text)
               for text, data in zip(buttons, callback_data)]
    keyboard.add(*buttons)
    return keyboard


def create_user(_id, users):
    """Добавление пользователя в базу данных"""
    if _id not in users:
        users[str(_id)] = {
            'locations': {},
            'radius': 500
        }
        with open('db.json', 'w') as f:
            json.dump(users, f)


def check_locations(locations, bot, message):
    """Проверка сохраненных местоположений"""
    if len(locations) == 0:
        msg = bot.send_message(
            message.chat.id,
            'Нет добавленных геолокаций.\n\n'
            'Добавьте первую с помощью команды /add, '
            'или прикрепив геопозицию.'
        )
        return True
    return False


def get_near_locations(user_location, locations, radius):
    """Возвращает массив ближайших локаций"""
    near_locations = []
    for key, location in locations:
        if 'location' in location:
            coord = (
                float(location['location']['latitude']),
                float(location['location']['longitude'])
            )
            dist = haversine(coord, user_location, unit=Unit.METERS)
            if dist <= radius:
                near_locations.append(location)

    return near_locations


def clean_text(dadata, message, location):
    """Возвращает местоположение по введенному тексту"""
    result = dadata.clean('address', message.text)
    if result is not None:
        location['address'] = result['result']
        if result["geo_lat"] is not None and result["geo_lon"] is not None:
            location['location'] = {'latitude': float(result["geo_lat"]),
                                    'longitude': float(result["geo_lon"])}
    else:
        location['title'] = message.text


def clean_geolocate(message, dadata, location):
    geo_lat, geo_lon = message.json["location"]["latitude"], message.json["location"]["longitude"]
    result = dadata.geolocate(name='address', lat=geo_lat, lon=geo_lon)

    if len(result) > 0:
        location['address'] = result[0]['value']
    else:
        location['address'] = f'{message.json["location"]["latitude"]}, ' \
                              f'{message.json["location"]["longitude"]}'
    location['location'] = message.json['location']
