import json
import telebot
from telebot import types
from vars import TOKEN, DESCRIPTION, PUSHEEN


def get_keyboard(buttons, row):
    """Инициализирует клавиатуру обработки геопозиуии от пользователя"""
    keyboard = types.InlineKeyboardMarkup(row_width=row)
    buttons = [types.InlineKeyboardButton(text=c, callback_data=c)
               for c in buttons]
    keyboard.add(*buttons)
    return keyboard


def main(db):
    bot = telebot.TeleBot(TOKEN)

    try:
        with open('db.json') as f:
            db = json.load(f)
    except:
        db = {}

    @bot.message_handler(commands=['start'])
    def create_user(message):
        """Добавление нового пользователя в базу данных"""
        send_help(message)
        _id = message.from_user.id
        if _id not in db:
            db[_id] = {
                'locations': [],
                'radius': 500
            }

    @bot.message_handler(commands=['help', 'start'])
    def send_help(message):
        """Вывод описания бота"""
        msg = bot.send_message(message.chat.id, DESCRIPTION)

    def new_location(message):
        """Создание новой геопозиции"""
        _id = message.from_user.id
        if message.content_type == 'text':
            db[_id]['locations'].append({
                'id': len(db[_id]['locations']),
                'address': message.text
            })
        elif message.content_type == 'location':
            db[_id]['locations'].append({
                'id': len(db[_id]['locations']),
                'location': message.location
            })
        elif message.content_type == 'photo':

            db[_id]['locations'].append({'photo': message.photo})
        else:
            add_user_locations(message)
        edit_location(message, db[_id]['locations'][-1])

    def edit_location(message, location):
        """Конфигурация геопозиции"""
        msg = print_location(message, location)
        bot.edit_message_reply_markup(msg.chat.id,
                                      msg.message_id,
                                      reply_markup=get_keyboard([
                                          'Изменить адрес',
                                          'Изменить изображение',
                                          'Изменить геопозицию'
                                      ], 1))

    def print_location(message, location):
        """Вывод геопозиции"""
        if 'picture' in location:
            msg = bot.send_photo(message.chat.id,
                                 location['picture'],
                                 location['address'])
        else:
            msg = bot.send_message(message.chat.id,
                                   location['address'])
        if 'location' in location:
            msg = bot.send_location(message.chat.id,
                                    location['location'].latitude,
                                    location['location'].longitude)
        return msg

    @bot.message_handler(content_types=['location'])
    def location_handler(message):
        """Обработка сообщения с геопозицией"""
        message_id = message.message_id
        msg = bot.send_message(message.chat.id, 'Выберите действие:',
                               reply_to_message_id=message_id,
                               reply_markup=get_keyboard([
                                   'Добавить локацию',
                                   'Показать ближайшие'
                               ], 2))

    @bot.callback_query_handler(func=lambda query: query.data == 'Показать ближайшие')
    def callback_handler(callback_query):
        """Вывод ближайших геопозиций"""
        msg = bot.send_message(callback_query.message.chat.id, 'В  процессе реализации...')

    @bot.callback_query_handler(func=lambda query: query.data == 'Добавить локацию')
    def callback_handler(callback_query):
        """Обработка добавления геопозиции"""
        pass

    @bot.message_handler(commands=['add'])
    def add_user_locations(message):
        """Обработка команды добавления геопозиции"""
        msg = bot.send_message(message.chat.id, 'Введите адрес, отправьте геопозицию или прикрепите фото:')
        bot.register_next_step_handler(msg, new_location)

    @bot.message_handler(commands=['list'])
    def send_user_locations(message):
        """Вывод списка геопозиций пользователя"""
        _id = message.from_user.id
        locations = db[_id]['locations']
        if len(locations) == 0:
            msg = bot.send_message(message.chat.id,
                                   'Нет добавленных геолокаций.\n\n'
                                   'Добавьте первую с помощью команды /add, '
                                   'или прикрепив геопозицию.')
            return

        for location in locations[:10]:  # TODO перелистывание если больше 10ти
            print_location(message, location)

    @bot.message_handler(commands=['secret'])
    def secret(message):
        """Секретный метод"""
        msg = bot.send_sticker(message.chat.id, PUSHEEN['surprised'])

    bot.polling()


if __name__ == '__main__':
    try:
        db = {}
        main(db)
    finally:
        with open('db.json', 'w') as f:
            json.dump(db, f)
