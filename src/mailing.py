import datetime
import re

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from sqlalchemy.orm import Query, Session

from database import session_scope
from database.tables import Subscription
from translation import default_translation as translation


HOUR_PATTERN = r'([0-1]?[0-9]|2[0-3])'
TIME_PATTERN = r'\s*(?P<h>' + HOUR_PATTERN + r')(?P<m>:[0-5]\d|)'
TIME_REGEX = re.compile('^' + TIME_PATTERN + '$')


class MailingStates(StatesGroup):
    choice_action = State()
    enter_time = State()


class MailingTime:
    @classmethod
    def subs_query(cls, session: Session, msg: types.Message) -> Query:
        # noinspection PyTypeChecker
        return (session
                .query(Subscription)
                .filter(Subscription.bot_id == msg.bot.id, Subscription.chat_id == msg.chat.id)
                )

    @staticmethod
    async def change(msg: types.Message) -> None:
        with session_scope() as session:
            q = session.query(Subscription.mailing_time)
            q = q.filter(Subscription.chat_id == msg.chat.id, Subscription.bot_id == msg.bot.id)
            mailing_time, = q.one()

        buttons = [
            types.KeyboardButton(text=translation.mailing_change),
            types.KeyboardButton(text=translation.mailing_cancel),
            types.KeyboardButton(text=translation.cancel),
        ]

        if mailing_time is None:
            buttons.pop(1)
            mt_text = translation.not_set
        else:
            mt_text = mailing_time.strftime('%H:%M')

        keyboard = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            one_time_keyboard=True,
            selective=True,
        ).row(*buttons)

        await msg.answer(
            f'🌐 {translation.current_mailing_params}: {mt_text}.',
            reply_markup=keyboard,
        )

        await MailingStates.choice_action.set()

    @classmethod
    async def cancel_mailing(cls, msg: types.Message) -> None:
        """Отмена подписки на ежедневный опрос."""
        with session_scope() as session:
            subs = cls.subs_query(session, msg).one()
            subs.mailing_time = None

        await msg.answer(
            translation.subscription_cancelled,
            reply_markup=types.ReplyKeyboardRemove(),
        )

    @staticmethod
    async def on_cancel(msg: types.Message, state: FSMContext) -> None:
        await msg.answer(translation.action_canceled, reply_markup=types.ReplyKeyboardRemove())
        await state.finish()

    @classmethod
    async def option_chosen(cls, msg: types.Message, state: FSMContext) -> None:
        msg_text = msg.text

        if msg_text == translation.mailing_change:
            await msg.answer(translation.mailing_time_enter)
            await MailingStates.next()

        elif msg_text == translation.mailing_cancel:
            await cls.cancel_mailing(msg)
            await state.finish()

        elif msg_text == translation.cancel:
            await cls.on_cancel(msg, state)

        else:
            await msg.answer(translation.choose_from_keyboard)

    @classmethod
    async def time_chosen(cls, msg: types.Message, state: FSMContext) -> None:
        if msg.text == translation.cancel:
            await cls.on_cancel(msg, state)
            return

        m = TIME_REGEX.match(msg.text)

        if not m:
            await msg.answer(translation.invalid_input_format)
            return

        time_ = datetime.time(hour=int(m.group('h')), minute=int(m.group('m')[1:] or 0))

        with session_scope() as session:
            subs = cls.subs_query(session, msg).one()
            subs.mailing_time = time_

        await msg.answer(
            f'{translation.mailing_time_changed}: {time_.strftime("%H:%M")}.',
            reply_markup=types.ReplyKeyboardRemove(),
        )

        await state.finish()
