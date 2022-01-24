import asyncio
import datetime as dt
from typing import Callable

from aiogram import Dispatcher, executor, types
from aiogram.types.message import ContentTypes
from sqlalchemy.exc import NoResultFound

from bot import bot, dp
from database import Session, session_scope
from database.tables import ChatTimezone, Subscription
from polls import create_lunch_poll, process_user_answer, send_lunch_poll, send_polls_results
from timezone import set_timezone


async def send_welcome(msg: types.Message) -> None:
    """Начало работы с ботом."""
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

            session.add(
                ChatTimezone(chat_id=msg.chat.id, sign=1, offset=dt.time(hour=3))
            )

    await msg.answer(f'Я бот. Приятно познакомиться, @{msg.from_user.username}.')


async def cancel_mailing(msg: types.Message) -> None:
    """Отмена подписки на ежедневный опрос."""
    with session_scope() as session:
        subs = (session
                .query(Subscription)
                .filter(Subscription.bot_id == bot.id, Subscription.chat_id == msg.chat.id)
                .one()
                )
        subs.mailing_time = None

    await msg.answer('Подписка отменена.')


async def get_text_messages(msg: types.Message) -> None:
    """Обработка пользовательских сообщений."""
    msg_lower = msg.text.lower()

    if msg_lower == 'привет':
        await msg.answer('Привет!')
        return

    splitted_msg = msg_lower.split(' ')

    for x in splitted_msg:
        if x.startswith('обед'):
            await create_lunch_poll(chat_id=msg.chat.id)
            break


async def do_periodic_task(timeout: int, stuff: Callable) -> None:
    """Вызов переданной функции каждые `timeout` секунд.

    :param timeout: период (в секундах).
    :param stuff: функция.
    """
    while True:
        await stuff()
        await asyncio.sleep(timeout)


def register_handlers(dp: Dispatcher):
    dp.register_message_handler(send_welcome, commands=['start'])
    dp.register_message_handler(cancel_mailing, commands=['cancelmailing'])
    dp.register_message_handler(set_timezone, commands=['tz'])
    dp.register_message_handler(get_text_messages, content_types=ContentTypes.TEXT)
    dp.register_poll_answer_handler(process_user_answer)


def main() -> None:
    register_handlers(dp)
    loop = asyncio.get_event_loop()

    loop.create_task(
        do_periodic_task(60, send_lunch_poll)
    )

    loop.create_task(
        do_periodic_task(30, send_polls_results)
    )

    executor.start_polling(dp, loop=loop)


if __name__ == '__main__':
    main()
