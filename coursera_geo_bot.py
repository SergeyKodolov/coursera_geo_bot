import json
import uuid

import telebot
from telebot import types
from telegram_bot_pagination import InlineKeyboardPaginator
from dadata import Dadata
from mytoken import BOT_TOKEN, DADATA_SECRET_KEY, DADATA_TOKEN
from vars import DESCRIPTION, PUSHEEN


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
    if len(locations) == 0:
        msg = bot.send_message(
            message.chat.id,
            'Нет добавленных геолокаций.\n\n'
            'Добавьте первую с помощью команды /add, '
            'или прикрепив геопозицию.'
        )
        return True
    return False


def main():
    bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
    dadata = Dadata(DADATA_TOKEN, DADATA_SECRET_KEY)

    try:
        with open('db.json') as f:
            users = json.load(f)
    except:
        users = {}

    @bot.message_handler(commands=['start'])
    def welcome_handler(message):
        """Добавление нового пользователя в базу данных"""
        send_help(message)
        _id = str(message.from_user.id)
        create_user(_id, users)

    @bot.message_handler(commands=['help'])
    def send_help(message):
        """Вывод описания бота"""
        msg = bot.send_message(message.chat.id, DESCRIPTION)

    @bot.message_handler(content_types=['location', 'venue'])
    def location_handler(message):
        """Обработка сообщения с геопозицией"""
        msg = bot.send_message(
            message.chat.id, 'Выберите действие:',
            reply_to_message_id=message.message_id,
            reply_markup=get_keyboard(
                2,
                ['Добавить локацию', 'Показать ближайшие'],
                ['add', 'near']
            )
        )

    @bot.callback_query_handler(func=lambda query: query.data == 'add')
    def callback_handler(callback_query):
        """Обработка добавления геопозиции"""
        new_location(callback_query.message.reply_to_message)

    @bot.message_handler(commands=['add'])
    def add_user_locations(message):
        """Обработка команды добавления геопозиции"""
        msg = bot.send_message(message.chat.id, 'Введите адрес, отправьте геопозицию или прикрепите фото:')
        bot.register_next_step_handler(msg, new_location)

    def new_location(message):
        """Создание новой геопозиции"""
        _id = str(message.from_user.id)
        loc_id = str(uuid.uuid4())
        number = len(users[_id]['locations'])
        location = {
            'title': f'Геопозиция #{number+1}'
        }

        if message.content_type == 'text':
            result = dadata.clean('address', message.text)
            if result is not None:
                location['address'] = result['result']
                location['location'] = {'latitude': result["geo_lat"],
                                        'longitude': result["geo_lon"]}
            else:
                location['title'] = message.text
            users[_id]['locations'][loc_id] = location

        elif message.content_type == 'location':
            geo_lat, geo_lon = message.json["location"]["latitude"], message.json["location"]["longitude"]
            result = dadata.geolocate(name='address', lat=geo_lat, lon=geo_lon)

            if len(result) > 0:
                location['address'] = result[0]['value']
            else:
                location['address'] = f'{message.json["location"]["latitude"]}, ' \
                                      f'{message.json["location"]["longitude"]}'
            location['location'] = message.json['location']

            users[_id]['locations'][loc_id] = location

        elif message.content_type == 'venue':
            location['title'] = message.json['venue']['title']
            location['address'] = message.json['venue']['address']
            location['location'] = message.json['location']
            users[_id]['locations'][loc_id] = location

        elif message.content_type == 'photo':
            location['photo'] = message.json['photo']
            users[_id]['locations'][loc_id] = location

        else:
            add_user_locations(message)

        menu_location(message, loc_id)

    def menu_location(message, loc_id):
        """Конфигурация геопозиции"""
        _id = str(message.from_user.id)
        location = users[_id]['locations'][loc_id]
        msg1, msg2 = print_location(message.chat.id, location)
        msg = msg2 or msg1
        bot.edit_message_reply_markup(
            message.chat.id,
            msg.message_id,
            reply_markup=get_keyboard(
                1,
                ['Изменить название',
                 'Изменить адрес',
                 'Изменить изображение',
                 'Изменить геопозицию'],
                [f'title#{loc_id}',
                 f'address#{loc_id}',
                 f'photo#{loc_id}',
                 f'position#{loc_id}']
            )
        )

    def print_location(chat_id, location):
        """Вывод геопозиции"""
        if 'photo' in location:
            msg1 = bot.send_photo(
                chat_id,
                location['photo'][0]['file_id'],
                location['title']
            )

        else:
            msg1 = bot.send_message(chat_id, location['title'])

        if 'location' in location:
            msg2 = bot.send_venue(
                chat_id,
                location['location']['latitude'],
                location['location']['longitude'],
                location['title'],
                location['address']
            )

        else:
            msg2 = None

        return msg1, msg2

    @bot.callback_query_handler(
        func=lambda query:
        query.data.split('#')[0] in ['title', 'address', 'photo', 'position']
    )
    def callback_handler(query):
        """Редактирование геопозиции"""
        data, loc_id = query.data.split('#')
        if data == 'title':
            msg = bot.send_message(query.message.chat.id, 'Введите новое название:\n')
            bot.register_next_step_handler(msg, change_title, loc_id)
        if data == 'address':
            msg = bot.send_message(query.message.chat.id, 'Отправьте новый адрес:\n')
            bot.register_next_step_handler(msg, change_address, loc_id)
        if data == 'photo':
            msg = bot.send_message(query.message.chat.id, 'Отправьте новое изображение:\n')
            bot.register_next_step_handler(msg, change_photo, loc_id)
        if data == 'position':
            msg = bot.send_message(query.message.chat.id, 'Отправьте новую геопозицию:\n')
            bot.register_next_step_handler(msg, change_location, loc_id)

    def change_title(message, loc_id):
        """Изменение названия"""
        if message.content_type == 'text':
            users[str(message.from_user.id)]['locations'][loc_id]['title'] = message.text
            bot.send_message(message.chat.id, 'Название успешно изменено!')
        else:
            bot.send_message(message.chat.id, 'Что-то пошло не так :(')
        menu_location(message, loc_id)

    def change_address(message, loc_id):
        """Изменение адреса"""
        if message.content_type == 'text':
            users[str(message.from_user.id)]['locations'][loc_id]['address'] = message.text
            bot.send_message(message.chat.id, 'Адрес успешно изменен!')
        else:
            bot.send_message(message.chat.id, 'Что-то пошло не так :(')
        menu_location(message, loc_id)

    def change_photo(message, loc_id):
        """Изменение изображения"""
        if message.content_type == 'photo':
            users[str(message.from_user.id)]['locations'][loc_id]['photo'] = message.json['photo']
            bot.send_message(message.chat.id, 'Изображение успешно изменено!')
        else:
            bot.send_message(message.chat.id, 'Что-то пошло не так :(')
        menu_location(message, loc_id)

    def change_location(message, loc_id):
        """Изменение геопозиции"""
        if message.content_type == 'location':
            users[str(message.from_user.id)]['locations'][loc_id]['location'] = message.json['location']
            bot.send_message(message.chat.id, 'Геопозиция успешно изменена!')
        elif message.content_type == 'venue':
            users[str(message.from_user.id)]['locations'][loc_id]['title'] = message.json['venue']['title']
            users[str(message.from_user.id)]['locations'][loc_id]['address'] = message.json['venue']['address']
            users[str(message.from_user.id)]['locations'][loc_id]['location'] = message.json['location']
            bot.send_message(message.chat.id, 'Геопозиция успешно изменена!')
        else:
            bot.send_message(message.chat.id, 'Что-то пошло не так :(')
        menu_location(message, loc_id)

    @bot.message_handler(commands=['list'])
    def send_user_locations(message):
        """Вывод списка геопозиций пользователя"""
        _id = str(message.from_user.id)
        locations = users[_id]['locations']

        if check_locations(locations, bot, message):
            return

        send_location_page(message)

    @bot.callback_query_handler(func=lambda call: call.data.split('#')[0] == 'location')
    def characters_page_callback(call):
        page = int(call.data.split('#')[1])
        msg1_id = int(call.data.split('#')[2])
        msg2_id = call.message.message_id

        ids = [msg1_id] if msg1_id == msg2_id else [msg1_id, msg2_id]
        for m_id in ids:
            bot.delete_message(
                call.message.chat.id,
                m_id
            )
        send_location_page(call.message, page)

    def send_location_page(message, page=1):
        locations = [x for key, x in users[str(message.chat.id)]['locations'].items()]
        msg1, msg2 = print_location(message.chat.id, locations[page - 1])

        if len(locations) > 1:
            paginator = InlineKeyboardPaginator(
                len(locations),
                current_page=page,
                data_pattern='location#{page}#' + str(msg1.message_id)
            )

            msg = msg2 or msg1
            bot.edit_message_reply_markup(
                msg.chat.id,
                msg.message_id,
                reply_markup=paginator.markup,
            )

    @bot.message_handler(commands=['reset'])
    def add_user_locations(message):
        """Обработка команды очистки данных пользователя"""
        _id = str(message.from_user.id)
        locations = users[_id]['locations']
        if check_locations(locations, bot, message):
            return

        msg = bot.send_message(
            message.chat.id,
            'Удалить все сохраненные геопозиции без возможности восстановления?',
            reply_to_message_id=message.message_id,
            reply_markup=get_keyboard(
                2,
                ['Точно, удалить', 'Нет, стой'],
                ['yes', 'no']
            )
        )

    @bot.callback_query_handler(func=lambda query: query.data == 'yes')
    def callback_handler(callback_query):
        """Удаляет геопозиции пользователя"""
        _id = str(callback_query.from_user.id)
        del users[_id]
        create_user(_id, users)
        bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
        bot.send_message(callback_query.message.chat.id, 'Сохраненные геопозиции успешно удалены!')

    @bot.callback_query_handler(func=lambda query: query.data == 'no')
    def callback_handler(callback_query):
        """Отмена команды /reset"""
        bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)

    @bot.message_handler(commands=['setradius'])
    def radius_handler(message):
        """Обработчик команды изменения радиуса"""
        msg = bot.send_message(message.chat.id, 'Укажите расстояние (10 - 1500):')
        bot.register_next_step_handler(msg, set_radius)

    def set_radius(message):
        try:
            radius = int(message.text)
            if 10 <= radius <= 1500:
                _id = str(message.from_user.id)
                users[_id]['radius'] = radius
                bot.send_message(message.chat.id, f'Установлен радиус {radius} метров')
            else:
                radius_handler(message)
        except Exception:
            radius_handler(message)

    @bot.callback_query_handler(func=lambda query: query.data == 'near')
    def callback_handler(callback_query):
        """Вывод ближайших геопозиций"""
        msg = bot.send_message(callback_query.message.chat.id, 'В  процессе реализации...')

    @bot.message_handler(commands=['secret'])
    def secret(message):
        """Секретный метод"""
        msg = bot.send_sticker(message.chat.id, PUSHEEN['surprised'])

    bot.infinity_polling(True)

    with open('db.json', 'w') as f:
        json.dump(users, f)


if __name__ == '__main__':
    main()
