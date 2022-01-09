import asyncio
from datetime import datetime

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types.message import ContentTypes

from db import Place, session_scope
from settings import API_TOKEN


bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

chat_ids = set()


@dp.message_handler(commands=['start'])
async def send_welcome(msg: types.Message) -> None:
    chat_ids.add(msg.chat.id)
    await msg.answer(f'Я бот. Приятно познакомиться, @{msg.from_user.username}')


async def create_lunch_poll(chat_id: str):
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
        open_period=600,
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
            for id_ in chat_ids:
                await create_lunch_poll(chat_id=id_)


def main() -> None:
    loop = asyncio.get_event_loop()
    loop.create_task(periodic(60, hour=10, minute=30))
    executor.start_polling(dp, loop=loop)


if __name__ == '__main__':
    main()
