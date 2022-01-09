from aiogram import Bot, Dispatcher, executor, types
from aiogram.types.message import ContentTypes
from db import Place, session_scope
from settings import API_TOKEN


bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(msg: types.Message) -> None:
    await msg.answer(f'Я бот. Приятно познакомиться, {msg.from_user.id}')


@dp.message_handler(content_types=ContentTypes.TEXT)
async def get_text_messages(msg: types.Message) -> None:
    msg_lower = msg.text.lower()

    if msg_lower == 'привет':
        await msg.answer('Привет!')

    elif 'обед' in msg_lower:
        options = []

        with session_scope() as s:
            places = s.query(Place).all()
            for p in places:
                options.append(p.name)

        msg_with_poll = await bot.send_poll(
            chat_id=msg.chat.id,
            question='Откуда заказываем?',
            options=options,
            is_anonymous=False,
            open_period=600,
        )

        print(msg_with_poll.poll.values)

    else:
        await msg.answer('Не понимаю, что это значит.')


def main() -> None:
    executor.start_polling(dp)


if __name__ == '__main__':
    main()
