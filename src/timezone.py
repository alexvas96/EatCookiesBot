import re

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

from database import session_scope
from database.tables import ChatTimezone
from translation import Translation
from utils import get_sign


TIME_REGEXP = re.compile(r'^(\+|-|)\s*[0-9]{1,2}(:[0-9]{2}|)$')

translation = Translation()


class TuneTimezone(StatesGroup):
    waiting_for_choice = State()
    waiting_for_tz = State()


class Timezone:
    @staticmethod
    async def set_timezone(msg: types.Message) -> None:
        with session_scope() as session:
            sign, offset = (session
                            .query(ChatTimezone.sign, ChatTimezone.offset)
                            .filter(ChatTimezone.chat_id == msg.chat.id)
                            .one()
                            )

            sign = get_sign(sign)

        keyboard = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            one_time_keyboard=True,
            selective=True,
        ).row(
            types.KeyboardButton(text=translation.change),
            types.KeyboardButton(text=translation.cancel),
        )

        await msg.answer(
            f'🌐 {translation.tz_current}: UTC {sign}{offset.strftime("%H:%M")}.',
            reply_markup=keyboard,
        )

        await TuneTimezone.waiting_for_choice.set()

    @staticmethod
    async def option_chosen(msg: types.Message, state: FSMContext) -> None:
        msg_text = msg.text

        if msg_text == translation.change:
            await msg.answer(translation.tz_enter)
            await TuneTimezone.next()

        elif msg_text == translation.cancel:
            await msg.answer(translation.action_canceled, reply_markup=types.ReplyKeyboardRemove())
            await state.finish()

        else:
            await msg.answer(translation.choose_from_keyboard)

    @staticmethod
    async def tz_chosen(msg: types.Message, state: FSMContext) -> None:
        if not TIME_REGEXP.match(msg.text):
            await msg.answer(translation.invalid_input_format)
            return

        text_tz = msg.text.strip().replace(' ', '')
        print(text_tz)
        await state.finish()
