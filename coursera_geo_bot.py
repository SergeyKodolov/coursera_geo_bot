import json
import time
import uuid

import telebot
from telebot import types
from mytoken import TOKEN
from vars import DESCRIPTION, PUSHEEN


def get_keyboard(buttons, row):
    """Инициализирует клавиатуру обработки геопозиуии от пользователя"""
    keyboard = types.InlineKeyboardMarkup(row_width=row)
    buttons = [types.InlineKeyboardButton(text=c, callback_data=c)
               for c in buttons]
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
        msg = bot.send_message(message.chat.id,
                               'Нет добавленных геолокаций.\n\n'
                               'Добавьте первую с помощью команды /add, '
                               'или прикрепив геопозицию.')
        return True
    return False


def main():
    bot = telebot.TeleBot(TOKEN, threaded=False)

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
        msg = bot.send_message(message.chat.id, 'Выберите действие:',
                               reply_to_message_id=message.message_id,
                               reply_markup=get_keyboard([
                                   'Добавить локацию',
                                   'Показать ближайшие'
                               ], 2))

    @bot.callback_query_handler(func=lambda query: query.data == 'Добавить локацию')
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
            'title': f'Геопозиция #{number}'
        }

        if message.content_type == 'text':
            location['title'] = message.text
            users[_id]['locations'][loc_id] = location

        elif message.content_type == 'location':
            location['location'] = message.json['location']
            location['address'] = f'{message.json["location"]["latitude"]}, ' \
                                  f'{message.json["location"]["longitude"]}'
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
        print_location(message.chat.id, location)
        bot.send_message(message.chat.id,
                         f'`{loc_id}`',
                         reply_markup=get_keyboard([
                             'Изменить название',
                             'Изменить адрес',
                             'Изменить изображение',
                             'Изменить геопозицию'
                         ], 1),
                         parse_mode='MarkdownV2')

    def print_location(chat_id, location):
        """Вывод геопозиции"""
        if 'photo' in location:
            msg = bot.send_photo(chat_id,
                                 location['photo'][0]['file_id'],
                                 location['title'])

        else:
            msg = bot.send_message(chat_id, location['title'])

        if 'location' in location:
            msg = bot.send_venue(chat_id,
                                 location['location']['latitude'],
                                 location['location']['longitude'],
                                 location['title'],
                                 location['address'])
        return msg

    @bot.callback_query_handler(func=lambda query: query.data == 'Изменить название')
    def callback_handler(callback_query):
        """Редактирование названия геопозиции"""
        loc_id = callback_query.message.text
        msg = bot.send_message(callback_query.message.chat.id, 'Введите новое название:\n')
        bot.register_next_step_handler(msg, change_title, loc_id)

    def change_title(message, loc_id):
        if message.content_type == 'text':
            users[str(message.from_user.id)]['locations'][loc_id]['title'] = message.text
            bot.send_message(message.chat.id, 'Название успешно изменено!')
        else:
            bot.send_message(message.chat.id, 'Что-то пошло не так :(')
        menu_location(message, loc_id)

    @bot.callback_query_handler(func=lambda query: query.data == 'Изменить адрес')
    def callback_handler(callback_query):
        """Редактирование адреса геопозиции"""
        loc_id = callback_query.message.text
        msg = bot.send_message(callback_query.message.chat.id, 'Отправьте новый адрес:\n')
        bot.register_next_step_handler(msg, change_address, loc_id)

    def change_address(message, loc_id):
        if message.content_type == 'text':
            users[str(message.from_user.id)]['locations'][loc_id]['address'] = message.text
            bot.send_message(message.chat.id, 'Адрес успешно изменен!')
        else:
            bot.send_message(message.chat.id, 'Что-то пошло не так :(')
        menu_location(message, loc_id)

    @bot.callback_query_handler(func=lambda query: query.data == 'Изменить изображение')
    def callback_handler(callback_query):
        """Редактирование изображения геопозиции"""
        loc_id = callback_query.message.text
        msg = bot.send_message(callback_query.message.chat.id, 'Отправьте новое изображение:\n')
        bot.register_next_step_handler(msg, change_photo, loc_id)

    def change_photo(message, loc_id):
        if message.content_type == 'photo':
            users[str(message.from_user.id)]['locations'][loc_id]['photo'] = message.json['photo']
            bot.send_message(message.chat.id, 'Изображение успешно изменено!')
        else:
            bot.send_message(message.chat.id, 'Что-то пошло не так :(')
        menu_location(message, loc_id)

    @bot.callback_query_handler(func=lambda query: query.data == 'Изменить геопозицию')
    def callback_handler(callback_query):
        """Редактирование координат геопозиции"""
        loc_id = callback_query.message.text
        msg = bot.send_message(callback_query.message.chat.id, 'Отправьте новую геопозицию:\n')
        bot.register_next_step_handler(msg, change_location, loc_id)

    def change_location(message, loc_id):
        if message.content_type == 'location':
            users[str(message.from_user.id)]['locations'][loc_id]['location'] = message.json['location']
            bot.send_message(message.chat.id, 'Геопозиция успешно изменена!')
        elif message.content_type == 'venue':
            users[str(message.from_user.id)]['locations'][loc_id]['location'] = message.json['venue']['title']
            users[str(message.from_user.id)]['locations'][loc_id]['address'] = message.json['venue']['address']
            users[str(message.from_user.id)]['locations'][loc_id]['title'] = message.json['location']
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

        for key, location in locations.items():  # TODO перелистывание если больше 10ти
            print_location(message.chat.id, location)

    @bot.message_handler(commands=['reset'])
    def add_user_locations(message):
        """Обработка команды очистки данных пользователя"""
        _id = str(message.from_user.id)
        locations = users[_id]['locations']
        if check_locations(locations, bot, message):
            return

        msg = bot.send_message(message.chat.id,
                               'Удалить все сохраненные геопозиции без возможности восстановления?',
                               reply_to_message_id=message.message_id,
                               reply_markup=get_keyboard([
                                   'Точно, удалить', 'Нет, стой'
                               ], 2))

    @bot.callback_query_handler(func=lambda query: query.data == 'Точно, удалить')
    def callback_handler(callback_query):
        """Удаляет геопозиции пользователя"""
        _id = str(callback_query.from_user.id)
        del users[_id]
        create_user(_id, users)
        bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
        bot.send_message(callback_query.message.chat.id, 'Сохраненные геопозиции успешно удалены!')

    @bot.callback_query_handler(func=lambda query: query.data == 'Нет, стой')
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

    @bot.callback_query_handler(func=lambda query: query.data == 'Показать ближайшие')
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
