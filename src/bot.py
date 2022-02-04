import asyncio
import datetime as dt
from typing import Callable

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types.message import ContentTypes
from sqlalchemy.exc import NoResultFound

from database import session_scope
from database.tables import ChatTimezone, Subscription
from polls import PollActions
from settings import API_TOKEN
from timezone import Timezone, TuneTimezone


class EatCookiesBot:
    def __init__(self):
        self.bot = Bot(token=API_TOKEN)
        self.dp = Dispatcher(self.bot, storage=MemoryStorage())
        self.poll_actions = PollActions(self.bot)

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

        await msg.answer(f'Я бот. Приятно познакомиться, @{msg.from_user.username}.')

    async def cancel_mailing(self, msg: types.Message) -> None:
        """Отмена подписки на ежедневный опрос."""
        with session_scope() as session:
            subs = (session
                    .query(Subscription)
                    .filter(Subscription.bot_id == self.bot.id, Subscription.chat_id == msg.chat.id)
                    .one()
                    )
            subs.mailing_time = None

        await msg.answer('Подписка отменена.')

    async def handle_topic_message(self, msg: types.Message) -> None:
        """Обработка пользовательских сообщений."""
        msg_lower = msg.text.lower()

        if msg_lower == 'привет':
            await msg.answer('Привет!')
            return

        splitted_msg = msg_lower.split(' ')

        for x in splitted_msg:
            if x.startswith('обед'):
                await self.poll_actions.create_lunch_poll(chat_id=msg.chat.id)
                break

    def register_handlers(self):
        self.dp.register_message_handler(self.start_subscription, commands=['start'])
        self.dp.register_message_handler(self.cancel_mailing, commands=['cancelmailing'])
        self.dp.register_message_handler(Timezone.set_timezone, commands=['tz'])
        self.dp.register_message_handler(
            callback=Timezone.option_chosen,
            state=TuneTimezone.waiting_for_choice,
        )
        self.dp.register_message_handler(Timezone.tz_chosen, state=TuneTimezone.waiting_for_tz)
        self.dp.register_message_handler(self.handle_topic_message, content_types=ContentTypes.TEXT)
        self.dp.register_poll_answer_handler(self.poll_actions.process_user_answer)

    def execute(self):
        self.register_handlers()
        loop = asyncio.get_event_loop()

        loop.create_task(
            do_periodic_task(60, self.poll_actions.send_lunch_poll)
        )

        loop.create_task(
            do_periodic_task(30, self.poll_actions.send_polls_results)
        )

        executor.start_polling(self.dp, loop=loop)


async def do_periodic_task(timeout: int, stuff: Callable) -> None:
    """Вызов переданной функции каждые `timeout` секунд.

    :param timeout: период (в секундах).
    :param stuff: функция.
    """
    while True:
        await stuff()
        await asyncio.sleep(timeout)
