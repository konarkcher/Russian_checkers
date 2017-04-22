import telebot
import _thread
from bot_config import TOKEN
from checkers import Game

bot = telebot.TeleBot(TOKEN, threaded=False)
sessions = {}


def console_talker():
    while True:
        print("Input 'stop' to stop server")
        if input() == 'stop':
            bot.stop_polling()
            break


def bot_reply(moves_done):
    if not moves_done:
        return ''

    if len(moves_done) == 1:
        reply = "Bot move:"
    else:
        reply = "Bot moves: "

    for move in moves_done:
        reply += ' ' + str(move)

    return reply + '\n'


def make_markup(game):
    moves = sorted(game.button_variants())
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)

    key_list = []
    buttons_in_row = 0

    for option in moves:
        key_list.append(telebot.types.KeyboardButton(option))  # TODO: E4
        buttons_in_row += 1

        if buttons_in_row == 3:
            markup.row(*key_list)
            key_list = []
            buttons_in_row = 0

    if key_list:
        markup.row(*key_list)

    return markup


@bot.message_handler(commands=['start'])
def start_game(message):
    global sessions
    if message.chat.id in sessions:
        bot.send_message(message.chat.id,
                         "Use '/finish' to finish the game firstly")
        return

    sessions[message.chat.id] = 's'

    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
    key_white = telebot.types.KeyboardButton('White')
    key_black = telebot.types.KeyboardButton('Black')
    markup.row(key_white, key_black)

    bot.send_message(message.chat.id, "Choose the color:", reply_markup=markup)


@bot.message_handler(func=lambda message: message.text in ('White', 'Black'))
def create_game_object(message):
    global sessions
    if sessions.get(message.chat.id) != 's':
        bot.send_message(message.chat.id, "Wrong command!")
        return

    if message.text == 'White':
        sessions[message.chat.id] = Game(enemy_white=True)
        reply = ''
    else:
        sessions[message.chat.id] = Game(enemy_white=False)
        moves_done = sessions[message.chat.id].black_first_move()
        reply = bot_reply(moves_done)

    picture = open('tmp.png', 'rb')
    bot.send_photo(message.chat.id, picture,
                   reply + "Show me what you can!",
                   reply_markup=make_markup(sessions[message.chat.id]))


@bot.message_handler(regexp='[1-8][1-8]')
def move_handle(message):
    global sessions
    if message.chat.id not in sessions:
        bot.send_message(message.chat.id,
                         "Use '/start' to start the game firstly")
        return

    replies = {
        -3: 'You lose :(', -2: 'Wrong target cell!', -1: 'Wrong checker!',
        1: 'Choose checker:', 2: 'Choose target cell:', 3: 'You win!',
        4: 'Choose target cell again!'
    }

    res, moves_done = sessions[message.chat.id].external_session(message.text)

    if res in (-3, 3):
        picture = open('tmp.png', 'rb')
        bot.send_photo(message.chat.id, picture,
                       bot_reply(moves_done) + replies[res])
    elif res in (-2, -1):
        bot.send_message(message.chat.id, replies[res])
    elif res in (1, 4):
        picture = open('tmp.png', 'rb')
        bot.send_photo(message.chat.id, picture,
                       bot_reply(moves_done) + replies[res],
                       reply_markup=make_markup(sessions[message.chat.id]))
    elif res == 2:
        bot.send_message(message.chat.id, replies[res],
                         reply_markup=make_markup(sessions[message.chat.id]))
    else:
        print('Error in move_handle!!!')


@bot.message_handler(commands=['finish'])
def finish_game(message):
    global sessions
    if message.chat.id in sessions:
        sessions.pop(message.chat.id)
        bot.send_message(message.chat.id, "Finished!")
    else:
        bot.send_message(message.chat.id, "You already don't have any games(")


@bot.message_handler(content_types=['text'])
def reply_all(message):
    bot.send_message(message.chat.id, "Wrong command!")


def main():
    global sessions
    #  sessions = backup.get()

    _thread.start_new_thread(console_talker, ())

    bot.polling()

    #  backup.save(sessions)

    print('Finished!')


if __name__ == '__main__':
    main()
