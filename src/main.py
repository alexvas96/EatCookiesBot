import asyncio
from datetime import datetime

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types.message import ContentTypes
from sqlalchemy.exc import NoResultFound

from db import QUERY_WINDOW_SIZE, Place, Session, Subscription, session_scope
from settings import API_TOKEN


bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)


@dp.message_handler(commands=['start'])
async def send_welcome(msg: types.Message) -> None:
    with session_scope() as session:
        session: Session
        try:
            session.query(Subscription).filter(Subscription.chat_id == msg.chat.id).one()
        except NoResultFound:
            session.add(
                Subscription(chat_id=msg.chat.id)
            )

    await msg.answer(f'Я бот. Приятно познакомиться, @{msg.from_user.username}')


async def create_lunch_poll(chat_id: int):
    options = []

    with session_scope() as session:
        places = session.query(Place).all()
        for p in places:
            options.append(p.name)

    await bot.send_poll(
        chat_id=chat_id,
        question='Откуда заказываем?',
        options=options,
        is_anonymous=False,
        open_period=300,
    )


@dp.message_handler(content_types=ContentTypes.TEXT)
async def get_text_messages(msg: types.Message) -> None:
    msg_lower = msg.text.lower()

    if msg_lower == 'привет':
        await msg.answer('Привет!')

    elif 'обед' in msg_lower:
        await create_lunch_poll(chat_id=msg.chat.id)


async def periodic(sleep_for: int, hour: int, minute: int) -> None:
    while True:
        await asyncio.sleep(sleep_for)
        now = datetime.now()

        if now.hour == hour and now.minute == minute:
            with session_scope() as session:
                session: Session
                idx = 0
                q = session.query(Subscription)

                while True:
                    start, stop = QUERY_WINDOW_SIZE * idx, QUERY_WINDOW_SIZE * (idx + 1)
                    instances = q.slice(start, stop).all()

                    if instances is None:
                        break

                    for x in instances:
                        await create_lunch_poll(chat_id=x.chat_id)

                    if len(instances) < QUERY_WINDOW_SIZE:
                        break

                    idx += 1


def main() -> None:
    loop = asyncio.get_event_loop()
    loop.create_task(periodic(60, hour=10, minute=30))
    executor.start_polling(dp, loop=loop)


if __name__ == '__main__':
    main()
