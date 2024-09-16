import asyncio
import datetime as dt
from typing import Callable

import pandas as pd
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.builtin import CommandStart
from aiogram.types import BotCommand
from aiogram.types.message import ContentTypes, ParseMode
from sqlalchemy.exc import NoResultFound

from database import session_scope
from database.tables import ChatTimezone, Subscription
from mailing import MailingStates, MailingTime
from polls import PollActions
from settings import API_TOKEN, EMPLOYEE_SURNAMES
from tickets import check_tickets, get_tickets_info
from timezone import Timezone, TimezoneStates
from translation import Translation
from utils import REGEX_NORMALIZATION, PlacesInfo


class EatCookiesBot:
    def __init__(self):
        self.bot = Bot(token=API_TOKEN)
        self.dp = Dispatcher(self.bot, storage=MemoryStorage())
        self.translation = Translation()
        self.places_info = PlacesInfo()
        self.poll_actions = PollActions(
            bot=self.bot,
            places_info=self.places_info,
            translation=self.translation,
        )

    async def start_subscription(self, msg: types.Message) -> None:
        """Начало работы с ботом."""
        bot_id = self.bot.id
        chat_id = msg.chat.id

        with session_scope() as session:
            try:
                session.query(Subscription).filter(
                    Subscription.bot_id == bot_id,
                    Subscription.chat_id == chat_id,
                ).one()
            except NoResultFound:
                session.add(
                    Subscription(chat_id=chat_id, bot_id=bot_id)
                )

                session.add(
                    ChatTimezone(chat_id=chat_id, sign=1, offset=dt.time(hour=3))
                )

        await msg.answer(f'Я бот. Приятно познакомиться, {msg.from_user.mention}.')

    async def send_link(self, chat_id: int, place: pd.Series) -> None:
        url_keyboard = types.InlineKeyboardMarkup().row(
            types.InlineKeyboardButton(text=self.translation.go_to_site, url=place.url)
        )
        await self.bot.send_message(
            chat_id=chat_id,
            text=f'«{place["name"]}»',
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=url_keyboard,
        )

    async def handle_thematic_message(self, msg: types.Message) -> None:
        """Обработка пользовательских сообщений."""
        msg_lower = msg.text.lower()

        if msg_lower == 'привет':
            await msg.answer('Привет!')
            return

        if not self.places_info.has_data:
            return

        msg_normalized = REGEX_NORMALIZATION.sub('', msg_lower)
        matching_place = self.places_info.names_regex.match(msg_normalized)

        if matching_place:
            place = self.places_info.places.loc[matching_place.group()]
            await self.send_link(chat_id=msg.chat.id, place=place)

    async def handle_lunch_command(self, msg: types.Message) -> None:
        await self.poll_actions.create_lunch_poll(chat_id=msg.chat.id)

    async def get_random_place(self, msg: types.Message) -> None:
        if self.places_info.has_data:
            place = self.places_info.places.sample(1).iloc[0]
            await self.send_link(chat_id=msg.chat.id, place=place)
        else:
            await msg.answer('Данные не найдены')

    async def update_places(self, *_) -> None:
        """Обновление информации о местах для заказа."""
        self.places_info.update_places()

    async def handle_tickets_command(self, msg: types.Message) -> None:
        direction = await get_tickets_info(EMPLOYEE_SURNAMES)

        if direction:
            text = (f'{direction.fullName}\n'
                    f'Найдено талонов: {direction.availableTicket}\n'
                    f'Ближайшая дата записи: {direction.nearestDate}'
                    )
        else:
            text = 'Талоны не найдены'

        await self.bot.send_message(chat_id=msg.chat.id, text=text)

    def register_handlers(self):
        self.dp.register_message_handler(self.start_subscription, CommandStart())

        self.dp.register_message_handler(Timezone.set_timezone, commands=['tz'])
        self.dp.register_message_handler(
            callback=Timezone.option_chosen,
            state=TimezoneStates.waiting_for_choice,
        )

        self.dp.register_message_handler(MailingTime.change, commands=['mailing'])
        self.dp.register_message_handler(
            callback=MailingTime.option_chosen,
            state=MailingStates.choice_action,
        )
        self.dp.register_message_handler(MailingTime.time_chosen, state=MailingStates.enter_time)

        self.dp.register_message_handler(
            self.handle_lunch_command,
            lambda msg: msg.text.lower().startswith('!обед'),
        )

        self.dp.register_message_handler(
            self.handle_lunch_command,
            commands=['lunch'],
        )

        self.dp.register_message_handler(self.get_random_place, commands=['random'])
        self.dp.register_message_handler(self.handle_tickets_command, commands=['tickets'])
        self.dp.register_message_handler(Timezone.tz_chosen, state=TimezoneStates.waiting_for_tz)
        self.dp.register_message_handler(self.update_places, commands=['update'])
        self.dp.register_message_handler(
            callback=self.handle_thematic_message,
            content_types=ContentTypes.TEXT,
        )
        self.dp.register_poll_answer_handler(self.poll_actions.process_user_answer)

    async def set_commands(self, *_) -> None:
        commands = [
            BotCommand('/start', 'Начало работы с ботом'),
            BotCommand('/lunch', 'Выбрать место для обеда (создать опрос)'),
            BotCommand('/random', 'Выбрать случайное место для обеда'),
            BotCommand('/mailing', 'Управление рассылкой'),
            BotCommand('/tickets', 'Проверить наличие талонов'),
        ]

        await self.bot.set_my_commands(commands=commands)

    async def check_tickets(self) -> None:
        await check_tickets(self.bot)

    def execute(self):
        self.register_handlers()
        loop = asyncio.get_event_loop()

        loop.create_task(
            do_periodic_task(60, self.poll_actions.send_lunch_poll)
        )

        loop.create_task(
            do_periodic_task(30, self.poll_actions.send_polls_results)
        )

        loop.create_task(
            do_periodic_task(30, self.check_tickets)
        )

        executor.start_polling(self.dp, loop=loop, on_startup=self.set_commands)


async def do_periodic_task(timeout: int, stuff: Callable) -> None:
    """Вызов переданной функции каждые `timeout` секунд.

    :param timeout: Период (в секундах).
    :param stuff: Функция.
    """
    while True:
        await stuff()
        await asyncio.sleep(timeout)
