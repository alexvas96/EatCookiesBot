from aiogram import Bot, Dispatcher, types
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
    if msg.text.lower() == 'привет':
        await msg.answer('Привет!')
    else:
        await msg.answer('Не понимаю, что это значит.')


def main() -> None:
    with session_scope() as s:
        questions = s.query(Place).order_by(Place.id.desc()).all()
        print(questions)
    # executor.start_polling(dp)


if __name__ == '__main__':
    main()
