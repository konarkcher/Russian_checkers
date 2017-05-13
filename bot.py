import telebot
import _thread
import time
import dropbox
import pickle
import logging
import os
import sys
import eng_locale as locale
from bot_config import BOT_TOKEN, DBX_TOKEN
from checkers import Game

cloud = dropbox.Dropbox(DBX_TOKEN)

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

logger = telebot.logger
logger.setLevel(logging.INFO)

logger.handlers = []

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
do_backups = True


def console_talker():
    while True:
        print(
            ">>> Input 'stop' to stop server, 'info' for games info\n",
            end='')

        command = input()
        if command == 'stop':
            bot.stop_polling()
            break
        elif command == 'info':
            template = '{0} players online; humans won {1[0]}, bot won {1[1]}'
            print(template.format(len(sessions), stat))


def backup():
    time.sleep(60)

    while do_backups:
        save_to_cloud(stat, 'stat.pickle')
        save_to_cloud(sessions, 'dump.pickle')
        time.sleep(60)


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


def get_name(message):
    name = message.chat.username

    if name is None:
        return message.chat.id
    return name


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
        logger.info('{} started a session'.format(get_name(message)))
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

    res, moves_done = sessions[message.chat.id].external_session(message.text)

    if res in (0, 5, 7):
        picture = open('tmp.png', 'rb')

        bot.send_photo(message.chat.id, picture,
                       '{}{}'.format(bot_reply(moves_done), locale.reply[res]),
                       reply_markup=telebot.types.ReplyKeyboardRemove())

        if res == 5:
            stat[0] += 1
            action = 'won the game'
        elif res == 0:
            stat[1] += 1
            action = 'lost the game'
        else:
            action = 'got a draw'

        if message.chat.type == 'private':
            logger.info('{} {}'.format(get_name(message), action))
        else:
            logger.info('chat {} {}'.format(message.chat.title, action))
        logger.info(
            'Statistics: {0[0]} for humans, {0[1]} for bot'.format(stat))

        lore_message()

        sessions.pop(message.chat.id)
    elif res in (1, 2):
        bot.send_message(message.chat.id, locale.reply[res])
    elif res in (3, 6):
        picture = open('tmp.png', 'rb')
        bot.send_photo(message.chat.id, picture,
                       '{}{}'.format(bot_reply(moves_done), locale.reply[res]),
                       reply_markup=make_markup(sessions[message.chat.id],
                                                False))
    elif res == 4:
        bot.send_message(message.chat.id, locale.reply[res],
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
        bot.send_message(message.chat.id, locale.reply[3],
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

        template = '{}{} finished the game prematurely'
        if message.chat.type == 'private':
            logger.info(template.format('', get_name(message)))
        else:
            logger.info(template.format('chat ', message.chat.title))
    else:
        bot.send_message(message.chat.id, locale.no_games)


@bot.message_handler(commands=['help'])
def help_reply(message):
    bot.send_message(message.chat.id, locale.help_ans, parse_mode="Markdown")


@bot.message_handler(commands=['lore'])
def lore_message(message):
    picture = open('invite_pic.jpg', 'rb')
    bot.send_photo(message.chat.id, picture,
                   locale.invite_template.format(stat))


@bot.message_handler(commands=['info'])
def get_info(message):
    if message.from_user.username == 'konarkcher':
        template = '{0} players online; humans won {1[0]}, bot won {1[1]}'
        bot.send_message(message.chat.id, template.format(len(sessions), stat))
    else:
        reply_all(message)


@bot.message_handler(content_types=['text'])
def reply_all(message):
    bot.send_message(message.chat.id, locale.wrong_command)


def get_file(path, default_value):
    try:
        cloud.files_download_to_file(path, "/{}".format(path))
    except dropbox.exceptions.ApiError as e:
        logger.warning(
            "{} while downloading {}".format(type(e.error).__name__, path))

        return default_value

    if os.path.isfile(path):
        with open(path, 'rb') as f:
            try:
                return pickle.load(f)
            except (pickle.UnpicklingError, ValueError):
                logger.error("Unpickling Error with {}!".format(path))
                return default_value
    else:
        logger.warning("Dump {} wasn't found on disk".format(path))
        return default_value


def save_to_cloud(value, path):
    try:
        with open(path, 'wb') as f:
            pickle.dump(value, f)

        cloud.files_delete("/{}".format(path))
        with open(path, "rb") as f:
            cloud.files_upload(f.read(), "/{}".format(path))

        return False
    except pickle.PicklingError:
        logger.error("Pickling Error with {}!\n".format(path))
        return True
    except dropbox.exceptions.ApiError as e:
        logger.error(
            "{} while uploading {}".format(type(e.error).__name__, path))
        return True


def main():
    global sessions
    global stat

    logger.info("Program was started")

    sessions = get_file('dump.pickle', sessions)
    stat = get_file('stat.pickle', stat)

    _thread.start_new_thread(console_talker, ())
    _thread.start_new_thread(backup, ())

    try:
        bot.polling(none_stop=True, timeout=20)
    except Exception as e:
        logger.error("Bot stopped with exception: {}".format(type(e).__name__))

    global do_backups
    do_backups = False

    save_to_cloud(stat, 'stat.pickle')
    if save_to_cloud(sessions, 'dump.pickle'):
        return

    logger.info('Finished! {} session(s) dumped\n'.format(len(sessions)))


if __name__ == '__main__':
    main()
