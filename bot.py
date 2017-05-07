import telebot
import _thread
import pickle
import logging
import os
import sys
import eng_locale as locale
from bot_config import TOKEN
from checkers import Game

bot = telebot.TeleBot(TOKEN, threaded=False)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = logging.FileHandler('bot_logs.log', 'a', 'utf-8')
formatter = logging.Formatter('%(levelname)-8s [%(asctime)s] %(message)s')
handler.setFormatter(formatter)
handler.setLevel(logging.INFO)
logger.addHandler(handler)

handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(levelname)-8s %(message)s')
handler.setFormatter(formatter)
handler.setLevel(logging.WARNING)
logger.addHandler(handler)

sessions = {}
stat = [0, 0]  # humanity/machines


def console_talker():
    while True:
        print(
            "Input 'stop' to stop server, 'info' for games info\n>>> ",
            end='')

        command = input()
        if command == 'stop':
            bot.stop_polling()
            break
        elif command == 'info':
            template = '{0} players online; humans won {1[0]}, bot won {1[1]}'
            print(template.format(len(sessions), stat))


def bot_reply(moves_done):
    if not moves_done:
        return ''

    if len(moves_done) == 1:
        reply = [locale.bot_move]
    else:
        reply = [locale.bot_moves]

    reply += ['({}, {}), '.format(pos, target) for pos, target in moves_done]

    return ''.join(reply)[:-2] + '\n'


def make_markup(game, can_change_checker):
    moves = sorted(game.button_variants())
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)

    markup.add(*[telebot.types.KeyboardButton(option) for option in moves])
    if can_change_checker:
        markup.row(locale.change_checker)

    return markup


@bot.message_handler(commands=['start'])
def start_game(message):
    global sessions
    if message.chat.id in sessions:
        bot.send_message(message.chat.id, locale.use_finish)
        return

    sessions[message.chat.id] = 's'

    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
    colors = (locale.white, locale.black)
    markup.row(*(telebot.types.KeyboardButton(color) for color in colors))

    bot.send_message(message.chat.id, locale.choose_color, reply_markup=markup)

    if message.chat.type == 'private':
        logger.info('{} started a session'.format(message.chat.username))
    else:
        logger.info('chat {} started a session'.format(message.chat.title))


@bot.message_handler(regexp='^{}$|^{}$'.format(locale.white, locale.black))
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
    bot.send_photo(message.chat.id, picture, '{}{}'.format(reply, locale.hi),
                   reply_markup=make_markup(sessions[message.chat.id], False))


@bot.message_handler(regexp='^[A-H][1-8]$')
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
                       '{}{}'.format(bot_reply(moves_done), replies[res]),
                       reply_markup=telebot.types.ReplyKeyboardRemove())

        if res == 2:
            stat[0] += 1
            action = 'won'
        else:
            stat[1] += 1
            action = 'lost'

        if message.chat.type == 'private':
            logger.info('{} {} the game'.format(message.chat.username, action))
        else:
            logger.info('chat {} {} the game'.format(message.chat.title,
                                                     action))
        logger.info(
            'Statistics: {0[0]} for humans, {0[1]} for bot'.format(stat))

        picture = open('invite_pic.jpg', 'rb')
        bot.send_photo(message.chat.id, picture,
                       locale.invite_template.format(stat))

        sessions.pop(message.chat.id)
    elif res in (-2, -1):
        bot.send_message(message.chat.id, replies[res])
    elif res in (0, 3):
        picture = open('tmp.png', 'rb')
        bot.send_photo(message.chat.id, picture,
                       '{}{}'.format(bot_reply(moves_done), replies[res]),
                       reply_markup=make_markup(sessions[message.chat.id],
                                                False))
    elif res == 1:
        bot.send_message(message.chat.id, replies[res],
                         reply_markup=make_markup(sessions[message.chat.id],
                                                  True))
    else:
        print('Error in move_handle!!!')


@bot.message_handler(regexp='^{}$'.format(locale.change_checker))
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

    template = '{}{} finished the game prematurely'
    if message.chat.type == 'private':
        logger.info(template.format('', message.chat.username))
    else:
        logger.info(template.format('chat ', message.chat.title))


@bot.message_handler(commands=['help'])
def help_reply(message):
    bot.send_message(message.chat.id, locale.help_message)


@bot.message_handler(content_types=['text'])
def reply_all(message):
    bot.send_message(message.chat.id, locale.wrong_command)


def open_file(path, default_value):
    if os.path.isfile(path):
        with open(path, 'rb') as f:
            try:
                return pickle.load(f)
            except (pickle.UnpicklingError, ValueError):
                logger.error("Unpickling Error with {}!".format(path))
                return default_value
    else:
        logger.warning("Dump {} wasn't found".format(path))
        return default_value


def save_to_file(value, path, log_func):
    with open(path, 'wb') as f:
        try:
            pickle.dump(value, f)
            return False
        except pickle.PicklingError:
            log_func("Pickling Error with {}!\n".format(path))
            return True


def main():
    global sessions
    global stat

    logger.info("Program was started")

    sessions = open_file('dump.pickle', sessions)
    stat = open_file('stat.pickle', stat)

    _thread.start_new_thread(console_talker, ())

    try:
        bot.polling(none_stop=True, timeout=100)
    except Exception as ex:
        logger.error("Bot stopped with exception: {}".format(
            type(ex).__name__))

        save_to_file(sessions, 'critical_dump.pickle', logger.critical)
        save_to_file(stat, 'critical_dump.pickle', logger.critical)

    if save_to_file(sessions, 'dump.pickle', logger.error):
        return
    if save_to_file(stat, 'stat.pickle', logger.error):
        return

    logger.info('Finished! {} session(s) dumped\n'.format(len(sessions)))


if __name__ == '__main__':
    main()
