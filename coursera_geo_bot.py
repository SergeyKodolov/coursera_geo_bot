import logging
import os
from typing import List

from flask import Flask, request

import telebot
from telebot import types
from telegram_bot_pagination import InlineKeyboardPaginator

import keyboard
from data_process import location_process, user_process, request_validation, near_location_process
from vars import DESCRIPTION, PUSHEEN

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)


# Валидация запросов пользователя

def validation_process(user_request, valid_func):
    """Процесс проверки запроса пользователя"""
    if type(user_request) is types.Message:
        chat_id = user_request.chat.id
    else:
        chat_id = user_request.message.chat.id

    error = valid_func(chat_id)
    if error:
        bot.send_message(**error)
        return
    return 1


def user_validation(func):
    """Проверка существования пользователя"""

    def wrapper(user_request):
        if validation_process(user_request, request_validation.check_user):
            return func(user_request)

    return wrapper


def locations_validation(func):
    """Проверка существования геопозиций пользователя"""

    def wrapper(user_request):
        if validation_process(user_request, request_validation.check_locations):
            return func(user_request)

    return wrapper


def location_validation(func):
    """Проверка существования геопозиции при вызове callback-кнопки"""

    def wrapper(user_request: types.CallbackQuery):
        chat_id = user_request.message.chat.id
        loc_id = user_request.data.split('#')[1]
        error = request_validation.check_location(chat_id, loc_id)
        if error:
            delete_location_page(user_request)
            bot.send_message(**error)
        else:
            return func(user_request)

    return wrapper


# Печать сообщений

def print_location(message: types.Message, loc_id: int) -> List[types.Message]:
    """Вывод карточки геопозиции"""
    reply_messages = location_process.print_location(loc_id)
    chat_id = message.chat.id

    send_msgs = []
    for msg in reply_messages:
        if msg:
            if len(msg) == 1:
                send_msgs.append(bot.send_message(chat_id, *msg))
            elif len(msg) == 2:
                send_msgs.append(bot.send_photo(chat_id, *msg))
            elif len(msg) == 4:
                send_msgs.append(bot.send_venue(chat_id, *msg))

    return send_msgs


def print_menu(message: types.Message, loc_id: int, send_msgs: List):
    """Вывод кнопок меню для карточки геопозиции"""
    msg1_id = -1
    if len(send_msgs) == 2:
        msg1_id = send_msgs[0].message_id

    bot.edit_message_reply_markup(
        message.chat.id,
        send_msgs[-1].message_id,
        reply_markup=location_process.get_location_menu(loc_id, msg1_id)
    )


def delete_location_page(callback: types.CallbackQuery):
    """Удаление текущей карточки геопозиции"""
    chat_id = callback.message.chat.id
    msg1_id = int(callback.data.split('#')[2])
    if msg1_id != -1:
        bot.delete_message(chat_id, msg1_id)
    msg2_id = callback.message.message_id
    bot.delete_message(chat_id, msg2_id)


def send_location_page(message, locations_ids=None, page=1, user_location=None):
    """Выводит карточку геопозиции из списка геопозиций"""
    user_id = message.chat.id
    locations_ids = locations_ids or location_process.get_location_ids(user_id)
    if locations_ids and len(locations_ids) < page:
        page = 1
    msgs = print_location(message, locations_ids[page - 1])
    print_paginator(msgs, page, user_location, locations_ids)


def print_paginator(msgs: List[types.Message], page: int, user_location: str, locations_ids: List[int]):
    """Выводит переключатель карточек геопозиций"""
    if len(locations_ids) > 1:
        msg1_id = msgs[0].message_id if len(msgs) != 1 else -1

        paginator = InlineKeyboardPaginator(
            len(locations_ids),
            current_page=page,
            data_pattern='location#{page}#'
                         f'{msg1_id}#'
                         f'{user_location}'
        )

        bot.edit_message_reply_markup(
            msgs[-1].chat.id,
            msgs[-1].message_id,
            reply_markup=paginator.markup,
        )


def print_requested_page(callback: types.CallbackQuery):
    """Выводит запрашиваемую карточку геопозиции из списка всех"""
    str_user_location = callback.data.split('#')[3]
    page = int(callback.data.split('#')[1])

    if str_user_location == 'None':
        send_location_page(callback.message, page=page)
    else:
        print_requested_page_near(callback, str_user_location, page)


def print_requested_page_near(callback: types.CallbackQuery, user_loc: str, page: int):
    """Выводит запрашиваемую карточку из списка ближайших"""
    user_id = str(callback.message.chat.id)
    user_location = (
        float(user_loc.split('*')[0]),
        float(user_loc.split('*')[1])
    )

    near_locations_ids = near_location_process.get_ids(user_id, user_location)
    send_location_page(
        callback.message,
        near_locations_ids,
        page=page,
        user_location=user_loc
    )


# Описание хэндлеров

@bot.message_handler(commands=['start'])
def welcome_handler(message: types.Message):
    """Добавление нового пользователя в базу данных"""
    help_handler(message)
    user_process.check(message.from_user.id)


@bot.message_handler(commands=['help'])
def help_handler(message: types.Message):
    """Вывод описания бота"""
    bot.send_message(message.chat.id, DESCRIPTION)


@bot.message_handler(content_types=['location', 'venue'])
def location_handler(message: types.Message):
    """Ответ на сообщение пользователя с геопозицией"""
    bot.send_message(
        message.chat.id, 'Выберите действие:',
        reply_to_message_id=message.message_id,
        reply_markup=keyboard.get_keyboard(
            2,
            ['Добавить геопозицию', 'Показать ближайшие'],
            ['add', 'near']
        )
    )


@bot.callback_query_handler(func=lambda query: query.data == 'add')
@user_validation
def callback_handler(callback_query: types.CallbackQuery):
    """Обработка кнопки добавления геопозиции"""
    new_location_handler(callback_query.message.reply_to_message)


@bot.message_handler(commands=['add'])
@user_validation
def add_user_location(message: types.Message):
    """Обработка команды добавления геопозиции"""
    msg = bot.send_message(
        message.chat.id,
        'Введите адрес, отправьте геопозицию или прикрепите фото:'
    )
    bot.register_next_step_handler(msg, new_location_handler)


def new_location_handler(message: types.Message):
    """Обработка добавления геопозиции"""
    new_loc_id = location_process.new_location(message)
    if new_loc_id > -1:
        msgs = print_location(message, new_loc_id)
        print_menu(message, new_loc_id, msgs)
    else:
        add_user_location(message)


@bot.callback_query_handler(
    func=lambda query:
    query.data.split('#')[0] in ['title', 'address', 'photo', 'position']
)
@user_validation
@locations_validation
@location_validation
def callback_handler(callback_query: types.CallbackQuery):
    """Редактирование геопозиции"""
    data, loc_id, msg1_id = callback_query.data.split('#')

    text = {
        'title': 'Введите новое название:\n',
        'address': 'Отправьте новый адрес:\n',
        'photo': 'Отправьте новое изображение:\n',
        'position': 'Отправьте новую геопозицию:\n'
    }

    msg = bot.send_message(callback_query.message.chat.id, text[data])
    bot.register_next_step_handler(msg, change_information, loc_id, data)


def change_information(message: types.Message, loc_id: int, data: str):
    """Изменение карточки геопозиции"""
    response = None
    if message.content_type == 'text' and data == 'title':
        response = location_process.change_title(loc_id, message.text)
    elif message.content_type == 'text' and data == 'address':
        response = location_process.change_address(loc_id, message.text)
    elif message.content_type == 'photo' and data == 'photo':
        response = location_process.change_photo(loc_id, message.json['photo'][0])
    elif message.content_type in ['location', 'venue'] and data == 'position':
        response = location_process.change_location(loc_id, message)

    if response:
        bot.send_message(message.chat.id, response)
        msgs = print_location(message, loc_id)
        print_menu(message, loc_id, msgs)
    else:
        bot.send_message(message.chat.id, 'Что-то пошло не так :(')


@bot.callback_query_handler(
    func=lambda query:
    query.data.split('#')[0] == 'delete'
)
@user_validation
@locations_validation
@location_validation
def callback_handler(callback_query: types.CallbackQuery):
    """Запрос на удаление геопозиции"""
    chat_id = callback_query.message.chat.id
    message_id = callback_query.message.message_id
    loc_id = callback_query.data.split('#')[1]
    response = location_process.delete_location(loc_id)
    if response:
        delete_location_page(callback_query)
        bot.send_message(chat_id, response)


@bot.message_handler(commands=['list'])
@user_validation
@locations_validation
def send_user_locations(message: types.Message):
    """Вывод списка геопозиций пользователя"""
    send_location_page(message)


@bot.callback_query_handler(func=lambda call: call.data.split('#')[0] == 'location')
@user_validation
@locations_validation
def location_page_callback(call: types.CallbackQuery):
    """Выводит карточку геопозиции, выбранную пользователем"""
    delete_location_page(call)
    print_requested_page(call)


@bot.callback_query_handler(func=lambda query: query.data == 'near')
@user_validation
@locations_validation
def callback_handler(query):
    """Вывод ближайших геопозиций"""
    user_id = str(query.message.chat.id)
    user_location = (
        query.message.reply_to_message.location.latitude,
        query.message.reply_to_message.location.longitude
    )

    near_locations_ids = near_location_process.get_ids(user_id, user_location)
    if len(near_locations_ids) > 0:
        str_user_location = f'{user_location[0]}*{user_location[1]}'
        send_location_page(query.message, near_locations_ids, user_location=str_user_location)
    else:
        bot.send_message(
            query.message.chat.id,
            'Ближайших геопозиций не обнаружено.'
        )


@bot.message_handler(commands=['reset'])
@user_validation
def remove_user_locations(message):
    """Обработка команды очистки данных пользователя"""
    bot.send_message(
        message.chat.id,
        'Удалить все сохраненные данные без возможности восстановления?',
        reply_to_message_id=message.message_id,
        reply_markup=keyboard.get_keyboard(
            2,
            ['Точно, удалить', 'Нет, стой'],
            ['yes', 'no']
        )
    )


@bot.callback_query_handler(func=lambda query: query.data == 'yes')
def callback_handler(callback_query):
    """Удаляет данных пользователя"""
    user_process.delete(callback_query.from_user.id)
    bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    bot.send_message(
        callback_query.message.chat.id,
        'Сохраненные данные успешно удалены!\n\n'
        'Чтобы продолжить работу введите /start'
    )


@bot.callback_query_handler(func=lambda query: query.data == 'no')
def callback_handler(callback_query):
    """Отмена команды /reset"""
    bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)


@bot.message_handler(commands=['setradius'])
@user_validation
def radius_handler(message):
    """Обработчик команды изменения радиуса"""
    msg = bot.send_message(message.chat.id, 'Укажите расстояние (10 - 15000):')
    bot.register_next_step_handler(msg, set_radius)


def set_radius(message: types.Message):
    """Установка радиуса поиска ближайших геопозиций"""
    radius = near_location_process.set_radius(message)
    if radius:
        bot.send_message(message.chat.id, f'Установлен радиус {radius} м')
    else:
        radius_handler(message)


@bot.message_handler(commands=['secret'])
def secret(message):
    """Секретный метод"""
    bot.send_sticker(message.chat.id, PUSHEEN['surprised'])


if __name__ == '__main__':

    if "HEROKU" in list(os.environ.keys()):

        server = Flask(__name__)


        @server.route(f"/{BOT_TOKEN}", methods=['POST'])
        def getMessage():
            bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
            return "!", 200


        @server.route("/")
        def webhook():
            bot.remove_webhook()
            bot.set_webhook(
                url=f"https://coursera-geo-note.herokuapp.com/{BOT_TOKEN}")
            return "?", 200


        server.run(host="0.0.0.0", port=int(os.environ.get('PORT', 80)))

    else:
        # если переменной окружения HEROKU нет, значит это запуск с машины разработчика.
        # Удаляем вебхук на всякий случай, и запускаем с обычным поллингом.
        bot.remove_webhook()
        bot.polling()
