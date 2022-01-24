from aiogram import types
from aiogram.dispatcher.filters.state import State, StatesGroup

from database import session_scope
from database.tables import ChatTimezone


class TuneTimezone(StatesGroup):
    waiting_for_tz = State()


def get_sign(value: int) -> str:
    if value >= 0:
        return '+'

    if value < 0:
        return '-'

    raise TypeError


async def set_timezone(msg: types.Message) -> None:
    with session_scope() as session:
        sign, offset = (session
                        .query(ChatTimezone.sign, ChatTimezone.offset)
                        .filter(ChatTimezone.chat_id == msg.chat.id)
                        .one()
                        )

        sign = get_sign(sign)

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).row(
        types.KeyboardButton(text='⌨ Ввести часовой пояс в формате ±HH:MM'),
        types.KeyboardButton(text='❌ Отмена'),
    )
    await msg.answer(
        f'🌐 Текущий часовой пояс: UTC {sign}{offset.strftime("%H:%M")}.',
        reply_markup=keyboard,
    )
