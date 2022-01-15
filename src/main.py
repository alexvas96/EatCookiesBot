import asyncio
import datetime as dt
from typing import Callable

import pytz
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types.message import ContentTypes
from aiogram.utils.exceptions import BotBlocked
from loguru import logger
from sqlalchemy.exc import NoResultFound

from database import QUERY_WINDOW_SIZE, Session, session_scope
from database.tables import Place, Poll, PollVote, Subscription
from settings import API_TOKEN


bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)


@dp.message_handler(commands=['start'])
async def send_welcome(msg: types.Message) -> None:
    with session_scope() as session:
        session: Session
        try:
            session.query(Subscription).filter(
                Subscription.bot_id == bot.id,
                Subscription.chat_id == msg.chat.id,
            ).one()
        except NoResultFound:
            session.add(
                Subscription(chat_id=msg.chat.id, bot_id=bot.id)
            )

    await msg.answer(f'Я бот. Приятно познакомиться, @{msg.from_user.username}')


def on_poll_creating(poll: types.Poll, chat_id: int, session: Session) -> None:
    """Действия после создания опроса."""
    session.add(
        Poll(id=poll.id, chat_id=chat_id, open_period=poll.open_period)
    )


async def create_lunch_poll(chat_id: int) -> None:
    options = []

    with session_scope() as session:
        places = session.query(Place).all()

        for p in places:
            options.append(p.name)

        msg = await bot.send_poll(
            chat_id=chat_id,
            question='Откуда заказываем?',
            options=options,
            is_anonymous=False,
            open_period=300,
        )

        on_poll_creating(poll=msg.poll, chat_id=chat_id, session=session)


@dp.poll_answer_handler()
async def process_user_answer(ans: types.PollAnswer) -> None:
    poll_id = ans.poll_id
    user_id = ans.user.id

    with session_scope() as session:
        session: Session

        if ans.option_ids:
            objs = []

            for option_id in ans.option_ids:
                obj = PollVote(poll_id=poll_id, user_id=user_id, option_number=option_id)
                objs.append(obj)

            session.bulk_save_objects(objs)
        else:
            # отмена голоса
            session.query(PollVote).filter(PollVote.poll_id == poll_id, PollVote.user_id == user_id).delete()


@dp.message_handler(content_types=ContentTypes.TEXT)
async def get_text_messages(msg: types.Message) -> None:
    msg_lower = msg.text.lower()

    if msg_lower == 'привет':
        await msg.answer('Привет!')
        return

    splitted_msg = msg_lower.split(' ')

    for x in splitted_msg:
        if x.startswith('обед'):
            await create_lunch_poll(chat_id=msg.chat.id)
            break


async def send_lunch_poll() -> None:
    now = dt.datetime.utcnow().replace(second=0, microsecond=0)

    with session_scope() as session:
        session: Session
        idx = 0
        query_subs = session.query(Subscription).filter(Subscription.bot_id == bot.id)

        while True:
            start, stop = QUERY_WINDOW_SIZE * idx, QUERY_WINDOW_SIZE * (idx + 1)
            instances = query_subs.slice(start, stop).all()

            if instances is None:
                break

            for x in instances:
                tz = pytz.timezone(x.timezone)

                if x.mailing_time == tz.fromutc(now).time():
                    chat_id = x.chat_id
                    try:
                        await create_lunch_poll(chat_id=chat_id)
                    except BotBlocked:
                        logger.debug('bot id=%d is blocked for chat id=%d, removing' % (bot.id, chat_id))
                        query_subs.filter(Subscription.chat_id == chat_id).delete()

            if len(instances) < QUERY_WINDOW_SIZE:
                break

            idx += 1


async def do_periodic_task(timeout: int, stuff: Callable) -> None:
    """

    :param timeout: период (в секундах).
    :param stuff: функция.
    """
    while True:
        await stuff()
        await asyncio.sleep(timeout)


def main() -> None:
    loop = asyncio.get_event_loop()
    loop.create_task(
        do_periodic_task(60, send_lunch_poll)
    )
    executor.start_polling(dp, loop=loop)


if __name__ == '__main__':
    main()
