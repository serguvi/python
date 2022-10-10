import telebot
import requests
import vertica_python
import time
import re
import base64
import pika
import json
import copy
from datetime import datetime, timedelta
from threading import Thread
from io import BytesIO, StringIO
from PIL import Image
from bs4 import BeautifulSoup
from logger_assistant import *


class BotMessage:
    def __init__(self, method, **kwargs):
        kwargs["method"] = method

        if kwargs.get("chat_id", False) is False and kwargs.get("message", False):
            kwargs["chat_id"] = kwargs["message"].chat.id

        self.kwargs = kwargs
        put_message_to_chat_group(self)

    def send(self):
        if self.kwargs['method'] == 'send_message':
            self._send_message()
        if self.kwargs['method'] == 'send_photo':
            self._send_photo()
        if self.kwargs['method'] == 'reply_to':
            self._reply_to()

    def _send_message(self):
        if 'disable_web_page_preview' in self.kwargs and 'parse_mode' in self.kwargs:
            bot.send_message(self.kwargs['chat_id'], self.kwargs['text'],
                             parse_mode=self.kwargs['parse_mode'],
                             disable_web_page_preview=self.kwargs['disable_web_page_preview'])
        else:
            bot.send_message(self.kwargs['chat_id'], self.kwargs['text'], disable_web_page_preview=True)

    def _send_photo(self):
        bot.send_photo(self.kwargs['chat_id'], photo=self.kwargs['photo'],
                       reply_to_message_id=self.kwargs['reply_to_message_id'])

    def _reply_to(self):
        if self.kwargs.get('reply_markup', False):
            bot.reply_to(self.kwargs['message'], self.kwargs['text'], reply_markup=self.kwargs['reply_markup'])
        else:
            bot.reply_to(self.kwargs['message'], self.kwargs['text'])


class Chat:
    def __init__(self):
        self.messages = []
        self.last_send_time = datetime.now()

    def add(self, message: BotMessage):
        self.messages.append([message, datetime.now(), 0])

    def pop(self, message_list):
        if message_list in self.messages:
            self.messages.pop(self.messages.index(message_list))


def put_message_to_chat_group(message: BotMessage):
    if message.kwargs["chat_id"] in chat_messages:
        chat = chat_messages[message.kwargs["chat_id"]]
    else:
        chat = Chat()
        chat_messages[message.kwargs["chat_id"]] = chat
    chat.add(message)


def send_messages_to_chats():
    while True:
        if len(chat_messages) != 0:
            chat_copy = copy.copy(chat_messages)
            for chat_id in chat_copy:
                chat = chat_copy[chat_id]
                for message_list in chat.messages:
                    message = message_list[0]
                    time = message_list[1]
                    difference = datetime.now() - chat.last_send_time
                    if difference.seconds >= 3 and time <= datetime.now():
                        chat.last_send_time = datetime.now()
                        try:
                            message.send()
                            chat_messages[chat_id].pop(message_list)
                            logger.info(f"Отправлено сообщение в чат: {chat_id},"
                                        f" параметры сообщения: {message.kwargs}.")
                        except Exception as e:
                            logger.error(f"Не получилось отправить сообщение, параметры:"
                                         f" {message.kwargs}. Ошибка: {get_exception()}")
                            message_list[1] = datetime.now() + timedelta(seconds=15)
                            message_list[2] += 1
                            if message_list[2] >= 3:
                                logger.error(f"Сообщение пыталось отправиться 3 раза с периодичностью в 15 секунд."
                                             f" Не получилось, удаляем. Параметры: {message.kwargs}.")
                                chat_messages[chat_id].pop(message_list)


def update_chat_id(ch_type, chat_id, ch_login, ch_title, otp):
    logger.info(
        f'updateChatID: ch_type: {ch_type}, chat_id: {chat_id}, ch_login: {ch_login}, ch_title: {ch_title}, otp: {otp}')

    res = 0

    if ch_type in ['group', 'supergroup', 'channel']:
        sql = """MERGE INTO запрос""".format(ch_login=ch_login, ch_type=ch_type, ch_title=ch_title, chat_id=chat_id)

        try:
            with vertica_python.connect(**vertica_conn_info) as connection:
                cur = connection.cursor()
                cur.execute(sql)
                rows = cur.fetchall()
                connection.commit()
                logger.info('Update Group ChatID rows: %s' % (rows))
                if len(rows) > 0 and len(rows[0]) > 0 and rows[0][0] > 0:
                    res = 1
                logger.info(f"Result: {[row for row in rows]}")
        except Exception as e:
            logger.error("Ошибка подключения к вертике: " + get_exception())

    if ch_type == 'private':
        sql = f"""UPDATE запрос"""

        try:
            with vertica_python.connect(**vertica_conn_info) as connection:
                cur = connection.cursor()
                cur.execute(sql)
                rows = cur.fetchall()
                connection.commit()
                logger.info('Update Group ChatID rows: %s' % (rows))
                if len(rows) > 0 and len(rows[0]) > 0 and rows[0][0] > 0:
                    res = 1
                logger.info(f"Result: {[row for row in rows]}")
        except Exception as e:
            logger.error("Ошибка подключения к вертике: " + get_exception())

    return res


def get_meas_id(message_text):
    logger.info("Получаем ID события из сообщения.")
    match = re.search("ID события:\s*(.{8}-.{4}-.{4}-.+)", message_text)
    if match:
        event_id = match.group(1).strip()
        logger.info(f"ID события: {event_id}.")
    else:
        logger.warning("ID события в сообщении не найдено.")
        return
    logger.info("Подключяемся к вертике для получения MEAS_ID показателя из события.")
    select = f"select ... from ... where id = '{event_id}'"
    try:
        with vertica_python.connect(**vertica_conn_info) as connection:
            cur = connection.cursor()
            cur.execute(select)
            meas_id = cur.fetchone()[0]
    except Exception as e:
        logger.error("Ошибка подключения к вертике: " + get_exception())
        return False
    return meas_id


def get_meas_id_from_link(message, is_entity=True):
    logger.info("Получаем MEAS_ID из сообщения.")
    match = None
    if is_entity:
        for entity in message.entities:
            if entity.type == 'text_link':
                match = re.search('meas_id=(\d+)', entity.url)
                if match:
                    break
    else:
        match = re.search('meas_id=(\d+)', message.text)
    if match:
        meas_id = match.group(1)
        logger.info(f"MEAS_ID: {meas_id}.")
        return meas_id
    else:
        logger.warning("MEAS_ID в сообщении не найдено.")
        return


def send_tlg_msg(ch, method, properties, body):
    try:
        m = json.loads(body)
        logger.info('Receive message: %s' % m)

        sev_s = ''
        if 'severity' in m:
            sev_s = SEV_ICON[m['severity']]

        if 'props' in m:
            if 'severity' in m['props']:
                sev_s = SEV_ICON[str(m['props']['severity'])]

        if 'to' in m and 'text' in m:
            t = '%s\t%s' % (sev_s, m['text'])
            BotMessage("send_message", chat_id=m['to'], text=t, parse_mode='HTML', disable_web_page_preview=True)
    except Exception as ex:
        logger.error('Message not sent: ' + get_exception())


def get_event_id_from_link(message, is_entity=True):
    logger.info("Получаем EVENT_ID из сообщения.")
    match = None
    if is_entity:
        for entity in message.entities:
            if entity.type == 'text_link':
                match = re.search('ev_id=(\w+-\w+-\w+-\w+-\w+)', entity.url)
                if match:
                    break
    else:
        match = re.search('ev_id=(\w+-\w+-\w+-\w+-\w+)', message.text)
    if match:
        event_id = match.group(1)
        logger.info(f"EVENT_ID: {event_id}.")
        return event_id
    else:
        logger.warning("EVENT_ID в сообщении не найдено.")
        return


def get_event_state(event_id):
    logger.info(f"Подключяемся к вертике для получения состояния события: {event_id}.")
    select = f"select ... from ... where id = '{event_id}'"
    try:
        logger.info(f"Получаем состояние события: {event_id}")
        with vertica_python.connect(**vertica_conn_info) as connection:
            cur = connection.cursor()
            cur.execute(select)
            answer = cur.fetchone()[0]
            state = STATE_NAME.get(answer, answer)
            logger.info(f"Полученное состояние: {state}")
    except Exception as e:
        logger.error("Ошибка подключения к вертике: " + get_exception())
        return
    return state


def get_event_history_state(event_id):
    logger.info(f"Подключяемся к вертике для получения истории состояний события: {event_id}.")
    select = f"select ... from ... where event_id = '{event_id}'"
    try:
        logger.info(f"Получаем историю состояний события: {event_id}")
        with vertica_python.connect(**vertica_conn_info) as connection:
            cur = connection.cursor()
            cur.execute(select)
            history_state = "История состояний события: \n"
            rows = cur.fetchall()
            if rows:
                history_state += rows[0][2].strftime("%d.%m.%Y %H:%M:%S") + " - ОТКРЫТО." + "\n"
                for row in rows:
                    if row[1]:
                        history_state += row[0].strftime("%d.%m.%Y %H:%M:%S") + " - " + str(
                            STATE_NAME.get(row[1], row[1])) + ".\n"
                logger.info(f"Полученная {history_state}")
            else:
                logger.error(f"Событие {event_id} в базе не найдено.")
                history_state = f"Событие {event_id} в базе не найдено."

    except Exception as e:
        logger.error("Ошибка подключения к вертике: " + get_exception())
        return
    return history_state


def run_bot():
    while True:
        try:
            logger.info("Запускаем бота.")
            bot.polling()
        except Exception as e:
            logger.error("Ошибка процесса polling: " + get_exception())
            time.sleep(15)


def check_dashboard_events():
    logger.info("Запускаем чтение событий из RABBITMQ")
    # Следующие 2 строки нужны, чтобы удалить постоянную клавиатуру
    # keys = telebot.types.ReplyKeyboardRemove()
    # bot.send_message(comments_group_id, "Удаляю клавиатуру", reply_markup=keys)

    connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True, passive=True)  # use existed queue
    channel.basic_consume(queue=QUEUE_NAME, auto_ack=True, on_message_callback=send_tlg_msg)

    while True:
        try:
            channel.start_consuming()
        except Exception as e:
            logger.error("Ошибка процесса rabbit: " + get_exception())
            time.sleep(15)


def check_state_and_severity_event(message):
    if message.text[:1] in SEV_ICON.values():
        severity = ascii(message.text[:1])
        if severity == ascii(SEV_ICON['0']):
            logger.info("Событие открыто со статусом CRITICAL")
            logger.info("Отправляем график")
            result = send_custom_graphic(message, hours=3, is_original_message=True)
            if result is None:
                return
        logs_remover(script_location, logger)
        return True
    else:
        return


def get_custom_graphic_image(message, hours):
    meas_id = get_meas_id_from_link(message)
    if meas_id is None:
        meas_id = get_meas_id_from_link(message, False)
    if meas_id:
        logger.info(f"MEAS_ID: {meas_id}")
        logger.info("Выполняем запрос для получения графика")
        try:
            logger.info(f"URL: {GET_IMAGE_HOST}/custom_graphic/{hours}/{meas_id}")
            r = requests.get(f"{GET_IMAGE_HOST}/custom_graphic/{hours}/{meas_id}", timeout=(10, 60), verify=False)
            logger.info(f"Статус запроса графика: {r.status_code}")
        except Exception as e:
            logger.error("Ошибка получения графика: " + get_exception())
            return False
        soup = BeautifulSoup(r.text, 'html.parser')
        img = soup.find('img')
        return img['src'][22:]
    else:
        if meas_id is None:
            logger.warning("MEAS_ID не найден.")
            return
        else:
            return False


def get_statuses_image(message):
    meas_id = get_meas_id_from_link(message)
    if meas_id is None:
        meas_id = get_meas_id_from_link(message, False)
    if meas_id:
        logger.info(f"MEAS_ID: {meas_id}")
        logger.info("Выполняем запрос для получения статусов")
        try:
            logger.info(f"URL: {GET_IMAGE_HOST}/statuses/{meas_id}")
            r = requests.get(f"{GET_IMAGE_HOST}/statuses/{meas_id}", timeout=(10, 60), verify=False)
            logger.info(f"Статус запроса статусов: {r.status_code}")
            soup = BeautifulSoup(r.text, 'html.parser')
            img = soup.find('img')
            return img['src'][22:]
        except Exception as e:
            logger.error(e)
            logger.error(get_exception())
            return False
    else:
        if meas_id is None:
            logger.warning("MEAS_ID не найден.")
            return
        else:
            return False


def send_custom_graphic(message, hours, is_original_message=False):
    logger.info("Получаем картинку графика")
    if is_original_message:
        data = get_custom_graphic_image(message, hours)
    else:
        data = get_custom_graphic_image(message.reply_to_message, hours)
    if data:
        data += "=="
        data_bytes = data.encode('ascii')
        img_bytes = base64.b64decode(data_bytes)
        image = Image.open(BytesIO(img_bytes))
        if image:
            BotMessage("send_photo", chat_id=message.chat.id, photo=image, reply_to_message_id=message.message_id)
            return True
    else:
        if data is None:
            logger.warning("У события нет показателя.")
            BotMessage("reply_to", message=message, text="У события нет показателя.")
        else:
            BotMessage("reply_to", message=message, text="Ошибка получения графика.")
            return False


def send_statuses(message):
    logger.info("Получаем картинку статусов")
    data = get_statuses_image(message.reply_to_message)
    if data:
        data += "=="
        data_bytes = data.encode('ascii')
        img_bytes = base64.b64decode(data_bytes)
        image = Image.open(BytesIO(img_bytes))
        if image:
            BotMessage("send_photo", chat_id=message.chat.id, photo=image, reply_to_message_id=message.message_id)
    else:
        if data is None:
            logger.warning("У события нет показателя.")
            BotMessage("reply_to", message=message, text="У события нет показателя.")
        else:
            BotMessage("reply_to", message=message, text="Ошибка получения статусов.")


def send_keyboard(message):
    graphic_button = telebot.types.InlineKeyboardButton('График', callback_data='1')
    statuses_button = telebot.types.InlineKeyboardButton('Статусы', callback_data='2')
    state_button = telebot.types.InlineKeyboardButton('Состояние', callback_data='6')
    keys = telebot.types.InlineKeyboardMarkup([[graphic_button, statuses_button, state_button]])
    BotMessage("reply_to", message=message, text="Выберите дополнительную информацию:", reply_markup=keys)


def send_state(message):
    event_id = get_event_id_from_link(message)
    if event_id is None:
        event_id = get_event_id_from_link(message, False)
    if event_id:
        state = get_event_state(event_id)
        if state:
            BotMessage("reply_to", message=message, text=f"Состояние события: {state}")
        else:
            BotMessage("reply_to", message=message, text="Ошибка получения состояния события.")
    else:
        logger.error("Не получилось получить событие из сообщения.")
        BotMessage("reply_to", message=message, text="Ошибка получения состояния события.")


def send_history_state(original_message):
    event_id = get_event_id_from_link(original_message)
    if event_id is None:
        event_id = get_event_id_from_link(original_message, False)
    if event_id:
        history_state = get_event_history_state(event_id)
        if history_state:
            BotMessage("reply_to", message=original_message, text=history_state)
        else:
            BotMessage("reply_to", message=original_message, text="Ошибка получения истории состояний события.")
    else:
        logger.error("Не получилось получить событие из сообщения.")
        BotMessage("reply_to", message=original_message, text="Ошибка получения истории состояний события.")


def send_graphic_keyboard(message):
    graphic3_button = telebot.types.InlineKeyboardButton('3 часа', callback_data='3')
    graphic24_button = telebot.types.InlineKeyboardButton('24 часа', callback_data='4')
    graphic168_button = telebot.types.InlineKeyboardButton('1 неделя', callback_data='5')
    keys = telebot.types.InlineKeyboardMarkup([[graphic3_button, graphic24_button, graphic168_button]])
    BotMessage("reply_to", message=message.reply_to_message, text="Выберите вариант графика:", reply_markup=keys)


RABBITMQ_HOST = '...'
QUEUE_NAME = '...'

GET_IMAGE_HOST = "..."

TELEGRAM_TOKEN = "..."
CHANNEL_ADMIN_ID = 777000

chat_messages = {}

vertica_conn_info = {
    'db_type': 'vertica',
    'conn_type': 'direct',
    'host': '...',
    'port': 5433,
    'ssl': False,
    'user': '...',
    'password': '...',
    'database': '...',
    'read_timeout': 600,
    'unicode_error': 'strict',
    'session_label': '...',
    'connection_load_balance': True,
    'backup_server_node': ['...', '...']
}

SEV_ICON = {
    '0': '\U0001f534',
    '5': '\U0001f525',
    '10': '\u26a0',
    '15': '\u2744',
    '20': '\U0001f34f',
    '-1': '\U0001f5d2',
    '-2': '\U0001f52e',
    '-4': '\U0001f527',
    '-20': '\U0001f535',
    '-30': '\u26aa'
}

SEV_NAME = {
    '0': 'CRITICAL',
    '5': 'MAJOR',
    '10': 'MINOR',
    '15': 'WARNING',
    '20': 'NORMAL',
    '-1': 'INFO',
    '-2': 'UNKNOWN',
    '-4': 'DOWNTIME',
    '-20': 'NO_DATA',
    '-30': 'CLOSED'
}

STATE_NAME = {
    'OPEN': 'ОТКРЫТО',
    'ACKNOWLEDGED': 'ПРИНЯТО',
    'IN_PROGRESS': 'В РАБОТЕ',
    'RESOLVED': 'ИСПРАВЛЕНО',
    'CLOSED': 'ЗАКРЫТО'
}

script_location = get_script_location()
script_name = get_script_name()
log_path = make_and_get_logs_path()

logger = get_logger("telebot", log_path)
logger_other_messages = get_logger("other_messages", log_path)
logger_bot_messages = get_logger("bot_messages", log_path)
logger_button_presses = get_logger("button_presses", log_path)

bot = telebot.TeleBot(TELEGRAM_TOKEN)


@bot.message_handler(commands=['k'])
def keyboard(message):
    if message.from_user.id != CHANNEL_ADMIN_ID:
        logger_other_messages.info(message.json)
    else:
        logger_bot_messages.info(message.json)
    if message.reply_to_message:
        try:
            send_keyboard(message.reply_to_message)
        except Exception as e:
            logger.error("Ошибка отправления клавиатуры: " + get_exception())
    else:
        BotMessage("reply_to", message=message, text="Команда принимается только в ответ на сообщение с событием.")


@bot.message_handler(commands=['state'])
def state(message):
    if message.from_user.id != CHANNEL_ADMIN_ID:
        logger_other_messages.info(message.json)
    else:
        logger_bot_messages.info(message.json)
    if message.reply_to_message:
        try:
            send_state(message.reply_to_message)
        except Exception as e:
            logger.error("Ошибка отправления статуса события: " + get_exception())
    else:
        BotMessage("reply_to", message=message, text="Команда принимается только в ответ на сообщение с событием.")


@bot.message_handler(commands=['info'])
def info_bot(message):
    if message.from_user.id != CHANNEL_ADMIN_ID:
        logger_other_messages.info(message.json)
    else:
        logger_bot_messages.info(message.json)
    BotMessage("reply_to", message=message, text=f"ID чата: {message.chat.id}")


@bot.message_handler(commands=['reg'])
def reg_bot(message):
    BotMessage("reply_to", message=message, text=f"ID чата: {message.chat.id}")
    if message.from_user.id != CHANNEL_ADMIN_ID:
        logger_other_messages.info(message.json)
    else:
        logger_bot_messages.info(message.json)

    ch_id = message.chat.id
    ch_type = message.chat.type
    ch_title = ''
    ch_login = None
    otp = None
    if ch_type in ['group', 'supergroup', 'channel']:
        ch_title = message.chat.title
        ch_login = ch_title
    if ch_type == 'private':
        ch_title = '%s %s' % (message.from_user.first_name, message.from_user.last_name)
        ch_login = None
        m = re.match('^\/reg\s+(.+)$', message.text, re.DOTALL)
        if m:
            otp = m.group(1)

    r = update_chat_id(ch_type, ch_id, ch_login, ch_title, otp)
    if r > 0:
        BotMessage("send_message", chat_id=ch_id, text="Чат '%s' зарегистрирован" % ch_title)
        bot.send_message(ch_id, text="Чат '%s' зарегистрирован" % ch_title)
    else:
        BotMessage("send_message", chat_id=ch_id, text="При регистрации произошла ошибка")


@bot.message_handler(commands=['regChannel'])
def reg_channel_bot(message):
    if message.__dict__.get("forward_from_chat", False):
        BotMessage("reply_to", message=message, text=f"ID чата: {message.forward_from_chat.id}")
        if message.from_user.id != CHANNEL_ADMIN_ID:
            logger_other_messages.info(message.json)
        else:
            logger_bot_messages.info(message.json)

        ch_id = message.forward_from_chat.id
        ch_type = message.forward_from_chat.type
        ch_title = ''
        ch_login = None
        otp = None
        if ch_type in ['group', 'supergroup', 'channel']:
            ch_title = message.forward_from_chat.title
            ch_login = ch_title
        if ch_type == 'private':
            ch_title = '%s %s' % (message.from_user.first_name, message.from_user.last_name)
            ch_login = None
            m = re.match('^\/reg\s+(.+)$', message.text, re.DOTALL)
            if m:
                otp = m.group(1)

        r = update_chat_id(ch_type, ch_id, ch_login, ch_title, otp)
        if r > 0:
            BotMessage("send_message", chat_id=ch_id, text="Чат '%s' зарегистрирован" % ch_title)
            bot.send_message(ch_id, text="Чат '%s' зарегистрирован" % ch_title)
        else:
            BotMessage("send_message", chat_id=ch_id, text="При регистрации произошла ошибка")


@bot.message_handler(func=lambda message: True, content_types=['text'])
def check_text_messages(message):
    if message.from_user.id != CHANNEL_ADMIN_ID:
        logger_other_messages.info(
            f"{message.from_user.first_name} ({message.from_user.username}), текст: {[message.text]} json:{message.json}")
    else:
        result = check_state_and_severity_event(message)
        if result:
            send_keyboard(message)
        logger_bot_messages.info(
            f"{message.from_user.first_name} ({message.from_user.username}), текст: {[message.text]} json:{message.json}")


@bot.callback_query_handler(func=lambda call: call.data == '1')
def callback_inline_graphic(message):
    bot.answer_callback_query(message.id, show_alert=True, text="Запрос принят")
    log_line = f"{message.from_user.first_name} ({message.from_user.username}) нажал на кнопку 'График' для сообщения: {message.message.json}"
    logger_button_presses.info(log_line)
    keyboard_message = message.message
    send_graphic_keyboard(keyboard_message)
    original_message = message.message.reply_to_message
    send_state(original_message)


@bot.callback_query_handler(func=lambda call: call.data == '2')
def callback_inline_statuses(message):
    bot.answer_callback_query(message.id, show_alert=True, text="Запрос принят")
    log_line = f"{message.from_user.first_name} ({message.from_user.username}) нажал на кнопку 'Статусы' для сообщения: {message.message.json}"
    logger_button_presses.info(log_line)
    keyboard_message = message.message
    send_statuses(keyboard_message)


@bot.callback_query_handler(func=lambda call: call.data == '3')
def callback_inline_graphic3(message):
    bot.answer_callback_query(message.id, show_alert=True, text="Запрос принят. Ожидайте ~15с")
    log_line = f"{message.from_user.first_name} ({message.from_user.username}) нажал на кнопку '3 часа' для сообщения: {message.message.json}"
    logger_button_presses.info(log_line)
    keyboard_message = message.message.reply_to_message
    send_custom_graphic(keyboard_message, 3, True)


@bot.callback_query_handler(func=lambda call: call.data == '4')
def callback_inline_graphic24(message):
    bot.answer_callback_query(message.id, show_alert=True, text="Запрос принят. Ожидайте ~20с")
    log_line = f"{message.from_user.first_name} ({message.from_user.username}) нажал на кнопку '24 часа'" \
               f" для сообщения: {message.message.json}"
    logger_button_presses.info(log_line)
    keyboard_message = message.message.reply_to_message
    send_custom_graphic(keyboard_message, 24, True)


@bot.callback_query_handler(func=lambda call: call.data == '5')
def callback_inline_graphic168(message):
    bot.answer_callback_query(message.id, show_alert=True, text="Запрос принят. Ожидайте ~30с")
    log_line = f"{message.from_user.first_name} ({message.from_user.username}) нажал на кнопку '1 неделя'" \
               f" для сообщения: {message.message.json}"
    logger_button_presses.info(log_line)
    keyboard_message = message.message.reply_to_message
    send_custom_graphic(keyboard_message, 168, True)


@bot.callback_query_handler(func=lambda call: call.data == '6')
def callback_inline_state(message):
    bot.answer_callback_query(message.id, show_alert=True, text="Запрос принят.")
    log_line = f"{message.from_user.first_name} ({message.from_user.username}) нажал на кнопку 'Состояние'" \
               f" для сообщения: {message.message.json}"
    logger_button_presses.info(log_line)
    keyboard_message = message.message.reply_to_message
    send_history_state(keyboard_message)


@bot.edited_message_handler(func=lambda message: True)
def edited_messages(message):
    if message.from_user.id != CHANNEL_ADMIN_ID:
        logger_other_messages.warning(
            f"Сообщение изменили: {message.from_user.first_name} ({message.from_user.username}), "
            f"текст: {[message.text]} json:{message.json}")
    else:
        logger_bot_messages.warning(
            f"Сообщение изменили: {message.from_user.first_name} ({message.from_user.username}), "
            f"текст: {[message.text]} json:{message.json}")


if __name__ == "__main__":
    logger.info("================")
    logger.info("Старутем приложение. Создаём экзмепляр бота.")

    logger.info("Создаём экзмепляры потоков.")
    t1 = Thread(target=run_bot)
    t2 = Thread(target=check_dashboard_events)
    t3 = Thread(target=send_messages_to_chats)
    t1.setDaemon(True)
    t2.setDaemon(True)
    t3.setDaemon(True)
    logger.info("Запускаем потоки.")
    t1.start()
    t2.start()
    t3.start()

    while True:
        pass
