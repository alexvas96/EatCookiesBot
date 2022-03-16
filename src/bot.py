import asyncio
import datetime as dt
from typing import Callable

import pandas as pd
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import BotCommand
from aiogram.types.message import ContentTypes, ParseMode
from sqlalchemy.exc import NoResultFound

from database import session_scope
from database.tables import ChatTimezone, Subscription
from polls import PollActions
from settings import API_TOKEN
from timezone import Timezone, TuneTimezone
from translation import Translation
from utils import REGEX_NORMALIZATION, PlacesInfo


class EatCookiesBot:
    def __init__(self):
        self.bot = Bot(token=API_TOKEN)
        self.dp = Dispatcher(self.bot, storage=MemoryStorage())
        self.translation = Translation()
        self.poll_actions = PollActions(self.bot, translation=self.translation)
        self.places_info = PlacesInfo()

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

    async def cancel_mailing(self, msg: types.Message) -> None:
        """Отмена подписки на ежедневный опрос."""
        with session_scope() as session:
            subs = (session
                    .query(Subscription)
                    .filter(Subscription.bot_id == self.bot.id, Subscription.chat_id == msg.chat.id)
                    .one()
                    )
            subs.mailing_time = None

        await msg.answer(self.translation.subscription_cancelled)

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

        msg_normalized = REGEX_NORMALIZATION.sub('', msg_lower)
        matching_place = self.places_info.names_regex.match(msg_normalized)

        if matching_place:
            place = self.places_info.places.loc[matching_place.group()]
            await self.send_link(chat_id=msg.chat.id, place=place)

    async def handle_lunch_command(self, msg: types.Message) -> None:
        await self.poll_actions.create_lunch_poll(chat_id=msg.chat.id)

    async def get_random_place(self, msg: types.Message) -> None:
        place = self.places_info.places.sample(1).iloc[0]
        await self.send_link(chat_id=msg.chat.id, place=place)

    def register_handlers(self):
        self.dp.register_message_handler(self.start_subscription, commands=['start'])
        self.dp.register_message_handler(self.cancel_mailing, commands=['cancelmailing'])
        self.dp.register_message_handler(Timezone.set_timezone, commands=['tz'])
        self.dp.register_message_handler(
            callback=Timezone.option_chosen,
            state=TuneTimezone.waiting_for_choice,
        )

        self.dp.register_message_handler(
            self.handle_lunch_command,
            lambda msg: msg.text.lower().startswith('!обед'),
        )

        self.dp.register_message_handler(
            self.handle_lunch_command,
            commands=['lunch'],
        )

        self.dp.register_message_handler(self.get_random_place, commands=['random'])
        self.dp.register_message_handler(Timezone.tz_chosen, state=TuneTimezone.waiting_for_tz)
        self.dp.register_message_handler(
            callback=self.handle_thematic_message,
            content_types=ContentTypes.TEXT,
        )
        self.dp.register_message_handler(self.places_info.update_places, commands=['update'])
        self.dp.register_poll_answer_handler(self.poll_actions.process_user_answer)

    async def set_commands(self, *_) -> None:
        commands = [
            BotCommand('/start', 'Начало работы с ботом'),
            BotCommand('/cancelmailing', 'Отмена ежедневной рассылки опроса'),
            BotCommand('/lunch', 'Выбрать место для заказа (создать опрос)'),
            BotCommand('/random', 'Выбрать случайное место для заказа'),
        ]

        await self.bot.set_my_commands(commands=commands)

    def execute(self):
        self.register_handlers()
        loop = asyncio.get_event_loop()

        loop.create_task(
            do_periodic_task(60, self.poll_actions.send_lunch_poll)
        )

        loop.create_task(
            do_periodic_task(30, self.poll_actions.send_polls_results)
        )

        executor.start_polling(self.dp, loop=loop, on_startup=self.set_commands)


async def do_periodic_task(timeout: int, stuff: Callable) -> None:
    """Вызов переданной функции каждые `timeout` секунд.

    :param timeout: период (в секундах).
    :param stuff: функция.
    """
    while True:
        await stuff()
        await asyncio.sleep(timeout)
