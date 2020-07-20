import telebot
from vars import TOKEN, DESCRIPTION


def main():
    bot = telebot.TeleBot(TOKEN)

    @bot.message_handler(commands=['help', 'start'])
    def send_welcome(message):
        msg = bot.send_message(message.chat.id, DESCRIPTION)

    bot.polling()


if __name__ == '__main__':
    main()
