import datetime
import re

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

from database import session_scope
from database.tables import ChatTimezone
from mailing import TIME_PATTERN
from translation import default_translation as translation
from utils import get_sign


SIGN_PATTERN = r'(?P<sign>\+|-|)'
TZ_REGEX = re.compile('^' + SIGN_PATTERN + TIME_PATTERN + '$')


class TimezoneStates(StatesGroup):
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

        await TimezoneStates.waiting_for_choice.set()

    @staticmethod
    async def on_cancel(msg: types.Message, state: FSMContext) -> None:
        await msg.answer(translation.action_canceled, reply_markup=types.ReplyKeyboardRemove())
        await state.finish()

    @classmethod
    async def option_chosen(cls, msg: types.Message, state: FSMContext) -> None:
        msg_text = msg.text

        if msg_text == translation.change:
            await msg.answer(translation.tz_enter)
            await TimezoneStates.next()

        elif msg_text == translation.cancel:
            await cls.on_cancel(msg, state)

        else:
            await msg.answer(translation.choose_from_keyboard)

    @classmethod
    async def tz_chosen(cls, msg: types.Message, state: FSMContext) -> None:
        if msg.text == translation.cancel:
            await cls.on_cancel(msg, state)
            return

        m = TZ_REGEX.match(msg.text)

        if not m:
            await msg.answer(translation.invalid_input_format)
            return

        sign = 1 if m.group('sign') in ('', '+') else -1
        h = int(m.group('h'))
        m = int(m.group('m')[1:] or 0)

        offset = datetime.time(hour=h, minute=m)

        with session_scope() as session:
            record = session.query(ChatTimezone).filter(ChatTimezone.chat_id == msg.chat.id).one()
            record.sign, record.offset = sign, offset

        await msg.answer(
            f'{translation.tz_changed}: UTC {get_sign(sign)}{offset.strftime("%H:%M")}.',
            reply_markup=types.ReplyKeyboardRemove(),
        )

        await state.finish()
