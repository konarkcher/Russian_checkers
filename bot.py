import telebot
import _thread
import pickle
import os
import eng_locale as locale
from bot_config import TOKEN
from checkers import Game

bot = telebot.TeleBot(TOKEN, threaded=False)
sessions = {}


def console_talker():
    while True:
        print(
            "Input 'stop' to stop server, 'info' for players online\n>>> ",
            end='')

        command = input()
        if command == 'stop':
            bot.stop_polling()
            break
        elif command == 'info':
            print(len(sessions), 'player(s) online')


def bot_reply(moves_done):
    if not moves_done:
        return ''

    if len(moves_done) == 1:
        reply = [locale.bot_move]
    else:
        reply = [locale.bot_moves]

    reply += ['({}, {}), '.format(pos, target) for pos, target in moves_done]

    return ''.join(reply)[:-2] + '\n'


def make_markup(game, can_change):
    moves = sorted(game.button_variants())
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)

    markup.add(*[telebot.types.KeyboardButton(option) for option in moves])
    if can_change:
        markup.row(locale.change_checkr)

    return markup


@bot.message_handler(commands=['start'])
def start_game(message):
    global sessions
    if message.chat.id in sessions:
        bot.send_message(message.chat.id, locale.use_finish)
        return

    sessions[message.chat.id] = 's'

    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
    key_white = telebot.types.KeyboardButton(locale.white)
    key_black = telebot.types.KeyboardButton(locale.white)
    markup.row(key_white, key_black)

    bot.send_message(message.chat.id, locale.choose_color, reply_markup=markup)


@bot.message_handler(func=lambda message: message.text in (locale.white,
                                                           locale.black))
def create_game_object(message):
    global sessions
    if sessions.get(message.chat.id) != 's':
        bot.send_message(message.chat.id, locale.wrong_command)
        return

    if message.text == locale.white:
        sessions[message.chat.id] = Game(enemy_white=True)
        reply = ''
    else:
        sessions[message.chat.id] = Game(enemy_white=False)
        moves_done = sessions[message.chat.id].black_first_move()
        reply = bot_reply(moves_done)

    picture = open('tmp.png', 'rb')
    bot.send_photo(message.chat.id, picture,
                   reply + locale.hello_message,
                   reply_markup=make_markup(sessions[message.chat.id], False))


@bot.message_handler(regexp='[A-H][1-8]')
def move_handle(message):
    global sessions
    if message.chat.id not in sessions:
        bot.send_message(message.chat.id, locale.use_start)
        return

    if sessions[message.chat.id] == 's':
        bot.send_message(message.chat.id, locale.choose_color_first)
        return

    replies = dict(zip(range(-3, 4), locale.replies))

    res, moves_done = sessions[message.chat.id].external_session(message.text)

    if res in (-3, 2):
        picture = open('tmp.png', 'rb')

        bot.send_photo(message.chat.id, picture,
                       bot_reply(moves_done) + replies[res],
                       reply_markup=telebot.types.ReplyKeyboardRemove())
        bot.send_message(message.chat.id, 'Invite text')  # TODO: fix

        sessions.pop(message.chat.id)
    elif res in (-2, -1):
        bot.send_message(message.chat.id, replies[res])
    elif res in (0, 3):
        picture = open('tmp.png', 'rb')
        bot.send_photo(message.chat.id, picture,
                       bot_reply(moves_done) + replies[res],
                       reply_markup=make_markup(sessions[message.chat.id],
                                                False))
    elif res == 1:
        bot.send_message(message.chat.id, replies[res],
                         reply_markup=make_markup(sessions[message.chat.id],
                                                  True))
    else:
        print('Error in move_handle!!!')


@bot.message_handler(func=lambda message: message.text == locale.change_checkr)
def change_checker(message):
    global sessions
    if not isinstance(sessions.get(message.chat.id), Game):
        bot.send_message(message.chat.id, locale.wrong_command)
        return

    game = sessions[message.chat.id]
    if game.murder == -1 and game.chosen_checker != -1:
        game.chosen_checker = -1
        bot.send_message(message.chat.id, locale.replies[3],
                         reply_markup=make_markup(sessions[message.chat.id],
                                                  False))
    else:
        bot.send_message(message.chat.id, locale.wrong_command)


@bot.message_handler(commands=['finish'])
def finish_game(message):
    global sessions
    if message.chat.id in sessions:
        sessions.pop(message.chat.id)

        bot.send_message(message.chat.id, locale.finished,
                         reply_markup=telebot.types.ReplyKeyboardRemove())
    else:
        bot.send_message(message.chat.id, locale.no_games)


@bot.message_handler(commands=['help'])
def help_reply(message):
    bot.send_message(message.chat.id, locale.help_message)


@bot.message_handler(content_types=['text'])
def reply_all(message):
    bot.send_message(message.chat.id, locale.wrong_command)


def main():
    global sessions
    if os.path.isfile('dump.pickle'):
        with open('dump.pickle', 'rb') as f:
            try:
                sessions = pickle.load(f)
            except (pickle.UnpicklingError, ValueError):
                print("Unpickling Error!")  # TODO: log message
                return
    else:
        print("Dump wasn't found!")  # TODO: log message

    _thread.start_new_thread(console_talker, ())

    bot.polling(none_stop=True, timeout=100)

    with open('dump.pickle', 'wb') as f:
        try:
            pickle.dump(sessions, f)
        except pickle.PicklingError:
            print("Pickling Error!")  # TODO: log message
            return

    print('Finished!', len(sessions), 'session(s) dumped')


if __name__ == '__main__':
    main()
