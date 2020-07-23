import telebot
from telegram_bot_pagination import InlineKeyboardPaginator
from vars import BOT_TOKEN, DESCRIPTION, PUSHEEN, EMPTY
from data_process import *
import db


def main(conn):
    bot_token = os.getenv('BOT_TOKEN') or BOT_TOKEN
    bot = telebot.TeleBot(bot_token)

    def is_there_user(message):
        """Проверяет существование пользователя"""
        if not db.is_there_user(conn, message.chat.id):
            bot.send_message(
                message.chat.id,
                'Произошла ошибка :(\n\n'
                'Воспользуйтесь командой /start'
            )
            return False
        return True

    def are_there_locations(message):
        """Проверяет существование местоположений"""
        if not db.are_there_locations(conn, message.chat.id):
            bot.send_message(
                message.chat.id,
                EMPTY
            )
            return False
        return True

    @bot.message_handler(commands=['start'])
    def welcome_handler(message):
        """Добавление нового пользователя в базу данных"""
        send_help(message)

        _id = str(message.from_user.id)
        db.create_user(conn, _id)

    @bot.message_handler(commands=['help'])
    def send_help(message):
        """Вывод описания бота"""
        msg = bot.send_message(message.chat.id, DESCRIPTION)

    @bot.message_handler(content_types=['location', 'venue'])
    def location_handler(message):
        """Обработка сообщения с геопозицией"""
        bot.send_message(
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
        if not is_there_user(callback_query.message):
            return

        new_location(callback_query.message.reply_to_message)

    @bot.message_handler(commands=['add'])
    def add_user_locations(message):
        """Обработка команды добавления геопозиции"""
        if not is_there_user(message):
            return

        msg = bot.send_message(message.chat.id, 'Введите адрес, отправьте геопозицию или прикрепите фото:')
        bot.register_next_step_handler(msg, new_location)

    def new_location(message):
        """Создание новой геопозиции"""
        _id = str(message.from_user.id)
        title = 'Геопозиция'

        # пользователь вводит адрес
        if message.content_type == 'text':
            title, address, location = clean_text(message)
            loc_id = db.create_location(conn, _id, title, address, location)

        # пользователь отправляет геопозицию
        elif message.content_type == 'location':
            address, location = clean_geolocate(message)
            loc_id = db.create_location(conn, _id, title, address, location)

        elif message.content_type == 'venue':
            title = message.json['venue']['title']
            address = message.json['venue']['address']
            location = json.dumps(message.json['location'])
            loc_id = db.create_location(conn, _id, title, address, location)

        # пользователь отправляет изображение
        elif message.content_type == 'photo':
            photo = json.dumps(message.json['photo'][0])
            loc_id = db.create_location(conn, _id, title, photo=photo)

        else:
            add_user_locations(message)
            return

        menu_location(message, loc_id)

    def menu_location(message, loc_id):
        """Конфигурация геопозиции"""
        _id = str(message.from_user.id)
        msg1, msg2 = print_location(message.chat.id, loc_id)
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

    def print_location(chat_id, loc_id):
        """Вывод геопозиции"""
        title, address, location, photo = db.get_location(conn, loc_id)
        if photo:
            msg1 = bot.send_photo(
                chat_id,
                photo['file_id'],
                title
            )

        else:
            msg1 = bot.send_message(chat_id, title)

        if location:
            msg2 = bot.send_venue(
                chat_id,
                location['latitude'],
                location['longitude'],
                title,
                address
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
        if not are_there_locations(query.message):
            return

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
            title = message.text
            db.update_location(conn, loc_id, title)
            bot.send_message(message.chat.id, 'Название успешно изменено!')
        else:
            bot.send_message(message.chat.id, 'Что-то пошло не так :(')
        menu_location(message, loc_id)

    def change_address(message, loc_id):
        """Изменение адреса"""
        if message.content_type == 'text':
            title, address, location = clean_text(message)
            address = None if address == 'null' else address
            location = None if location == 'null' else location

            db.update_location(conn, loc_id, title, address, location)
            bot.send_message(message.chat.id, 'Адрес успешно изменен!')
        else:
            bot.send_message(message.chat.id, 'Что-то пошло не так :(')
        menu_location(message, loc_id)

    def change_photo(message, loc_id):
        """Изменение изображения"""
        if message.content_type == 'photo':
            photo = json.dumps(message.json['photo'][0])
            db.update_location(conn, loc_id, photo=photo)
            bot.send_message(message.chat.id, 'Изображение успешно изменено!')
        else:
            bot.send_message(message.chat.id, 'Что-то пошло не так :(')
        menu_location(message, loc_id)

    def change_location(message, loc_id):
        """Изменение геопозиции"""
        if message.content_type == 'location':
            address, location = clean_geolocate(message)
            address = None if address == 'null' else address
            location = None if location == 'null' else location

            db.update_location(conn, loc_id, address=address, location=location)
            bot.send_message(message.chat.id, 'Геопозиция успешно изменена!')

        elif message.content_type == 'venue':
            title = message.json['venue']['title']
            address = message.json['venue']['address']
            location = json.dumps(message.json['location'])
            db.update_location(conn, loc_id, title, address, location)
            bot.send_message(message.chat.id, 'Геопозиция успешно изменена!')

        else:
            bot.send_message(message.chat.id, 'Что-то пошло не так :(')
        menu_location(message, loc_id)

    @bot.message_handler(commands=['list'])
    def send_user_locations(message):
        """Вывод списка геопозиций пользователя"""
        if not are_there_locations(message):
            return

        send_location_page(message)

    @bot.callback_query_handler(func=lambda call: call.data.split('#')[0] == 'location')
    def location_page_callback(call):
        """Выводит местоположение, выбранное пользователем"""
        if not are_there_locations(call.message):
            return

        page = int(call.data.split('#')[1])
        msg1_id = int(call.data.split('#')[2])
        msg2_id = call.message.message_id

        ids = [msg1_id] if msg1_id == msg2_id else [msg1_id, msg2_id]
        for m_id in ids:
            bot.delete_message(
                call.message.chat.id,
                m_id
            )

        str_user_location = call.data.split('#')[3]

        if str_user_location == 'None':
            send_location_page(call.message, page=page)
        else:
            user_id = str(call.message.chat.id)
            user_location = (
                float(str_user_location.split('*')[0]),
                float(str_user_location.split('*')[1])
            )

            near_locations_ids = process_near_locations(user_id, user_location)

            send_location_page(call.message, near_locations_ids, page=page, user_location=str_user_location)

    @bot.callback_query_handler(func=lambda query: query.data == 'near')
    def callback_handler(query):
        """Вывод ближайших геопозиций"""
        if not are_there_locations(query.message):
            return

        user_id = str(query.message.chat.id)
        user_location = (
            query.message.reply_to_message.location.latitude,
            query.message.reply_to_message.location.longitude
        )

        near_locations_ids = process_near_locations(user_id, user_location)

        if len(near_locations_ids) > 0:
            str_user_location = f'{user_location[0]}*{user_location[1]}'
            send_location_page(query.message, near_locations_ids, user_location=str_user_location)
        else:
            bot.send_message(
                query.message.chat.id,
                'Ближайших геопозиций не обнаружено.'
            )

    def process_near_locations(user_id, user_location):
        """Формирование списка ближайших местоположений"""
        radius = db.get_radius(conn, user_id)

        locations_ids = db.get_locations_ids(conn, user_id)
        near_locations_ids = db.get_near_locations_ids(conn, user_location, locations_ids, radius)
        return near_locations_ids

    def send_location_page(message, locations_ids=None, page=1, user_location=None):
        user_id = message.chat.id
        locations_ids = locations_ids or db.get_locations_ids(conn, user_id)
        msg1, msg2 = print_location(message.chat.id, locations_ids[page - 1])

        if len(locations_ids) > 1:
            paginator = InlineKeyboardPaginator(
                len(locations_ids),
                current_page=page,
                data_pattern='location#{page}#'
                             f'{str(msg1.message_id)}#'
                             f'{user_location}'
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
        if not is_there_user(message):
            return

        bot.send_message(
            message.chat.id,
            'Удалить все сохраненные данные без возможности восстановления?',
            reply_to_message_id=message.message_id,
            reply_markup=get_keyboard(
                2,
                ['Точно, удалить', 'Нет, стой'],
                ['yes', 'no']
            )
        )

    @bot.callback_query_handler(func=lambda query: query.data == 'yes')
    def callback_handler(callback_query):
        """Удаляет данных пользователя"""
        _id = str(callback_query.from_user.id)
        db.delete_user_data(conn, _id)
        bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
        bot.send_message(
            callback_query.message.chat.id,
            'Сохраненные данные успешно удалены!\n\n'
            'Чтобы продолжить работу введите /start')

    @bot.callback_query_handler(func=lambda query: query.data == 'no')
    def callback_handler(callback_query):
        """Отмена команды /reset"""
        bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)

    @bot.message_handler(commands=['setradius'])
    def radius_handler(message):
        if not is_there_user(message):
            return

        """Обработчик команды изменения радиуса"""
        msg = bot.send_message(message.chat.id, 'Укажите расстояние (10 - 15000):')
        bot.register_next_step_handler(msg, set_radius)

    def set_radius(message):
        try:
            radius = int(message.text)
            if 10 <= radius <= 15000:
                _id = str(message.from_user.id)
                db.update_radius(conn, _id, radius)
                bot.send_message(message.chat.id, f'Установлен радиус {radius} м')
            else:
                radius_handler(message)
        except Exception:
            radius_handler(message)

    @bot.message_handler(commands=['secret'])
    def secret(message):
        """Секретный метод"""
        bot.send_sticker(message.chat.id, PUSHEEN['surprised'])

    bot.polling()


if __name__ == '__main__':
    with db.create_connection() as conn:
        db.check_tables(conn)
        main(conn)
