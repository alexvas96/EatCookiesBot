from typing import Optional

import pandas as pd
from aiogram import types
from aiogram.types import ParseMode
from aiogram.utils.exceptions import BotBlocked
from dateutil.relativedelta import relativedelta
from loguru import logger
from sqlalchemy import func
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

from bot import bot
from database import ENGINE, QUERY_WINDOW_SIZE, session_scope
from database.tables import ChatTimezone, Place, Poll, PollOption, PollVote, Subscription
from main import get_utc_now


def on_poll_creating(
    poll: types.Poll,
    chat_id: int,
    session: Session,
    options: Optional[pd.DataFrame] = None,
) -> None:
    """Действия после создания опроса."""
    session.add(
        Poll(id=poll.id, chat_id=chat_id, open_period=poll.open_period)
    )
    session.commit()

    if options is not None:
        options = pd.DataFrame({
            'poll_id': poll.id,
            'position': options.index,
            'option_id': options.id,
        })

        options.to_sql(PollOption.__tablename__, ENGINE, if_exists='append', index=False)


async def create_lunch_poll(chat_id: int) -> None:
    """Создание и отправка опроса."""
    with session_scope() as session:
        options = pd.read_sql(session.query(Place.id, Place.name).statement, ENGINE)

        msg = await bot.send_poll(
            chat_id=chat_id,
            question='Откуда заказываем?',
            options=options.name.to_list(),
            is_anonymous=False,
            open_period=300,
        )

        on_poll_creating(poll=msg.poll, chat_id=chat_id, session=session, options=options)


async def send_lunch_poll() -> None:
    """Создание и отправка опроса по расписанию."""
    now = get_utc_now()

    with session_scope() as session:
        idx = 0
        query_subs = (session
                      .query(Subscription.chat_id,
                             Subscription.mailing_time,
                             ChatTimezone.sign,
                             ChatTimezone.offset,
                             )
                      .filter(Subscription.bot_id == bot.id)
                      .join(ChatTimezone, Subscription.chat_id == ChatTimezone.chat_id)
                      )

        while True:
            start, stop = QUERY_WINDOW_SIZE * idx, QUERY_WINDOW_SIZE * (idx + 1)
            instances = query_subs.slice(start, stop).all()

            if instances is None:
                break

            for (chat_id, mailing_time, sign, offset) in instances:
                current_time = now + sign * relativedelta(hours=offset.hour, minutes=offset.minute)
                current_time = current_time.time()

                if mailing_time == current_time:
                    try:
                        await create_lunch_poll(chat_id=chat_id)
                    except BotBlocked:
                        logger.debug('bot id=%d is blocked for chat id=%d, removing' %
                                     (bot.id, chat_id))
                        query_subs.filter(Subscription.chat_id == chat_id).delete()

            if len(instances) < QUERY_WINDOW_SIZE:
                break

            idx += 1


async def process_user_answer(ans: types.PollAnswer) -> None:
    """Добавление/обновление ответа пользователя на опрос."""
    poll_id = ans.poll_id
    user_id = ans.user.id

    with session_scope() as session:
        if ans.option_ids:
            objs = []

            for option_id in ans.option_ids:
                obj = PollVote(poll_id=poll_id, user_id=user_id, option_number=option_id)
                objs.append(obj)

            session.bulk_save_objects(objs)
        else:
            # отмена голоса
            session.query(PollVote).filter(PollVote.poll_id == poll_id,
                                           PollVote.user_id == user_id).delete()


async def send_polls_results() -> None:
    """Отправка информации о результатах опроса."""
    cols_to_analyze = (
        PollVote.poll_id,
        Poll.chat_id,
        Poll.start_date,
        Poll.open_period,
        PollVote.option_number,
    )

    with session_scope() as session:
        polls_to_process_query = (session
                                  .query(*cols_to_analyze,
                                         func.count(PollVote.option_number).label('num_votes')
                                         )
                                  .join(Poll, Poll.id == PollVote.poll_id)
                                  .filter(Poll.is_closed == False)
                                  .group_by(*cols_to_analyze)
                                  )

        df = (pd.read_sql(polls_to_process_query.statement, ENGINE)
              .sort_values(['poll_id', 'num_votes'], ascending=[True, False])
              .groupby('poll_id')
              .first()
              )

        now = get_utc_now()
        polls_to_close = []

        for poll_id, row in df.iterrows():
            if now >= row.start_date + relativedelta(seconds=row.open_period):
                try:
                    name, url, choice_message = (
                        session
                        .query(Place.name, Place.url, Place.choice_message)
                        .join(PollOption, Place.id == PollOption.option_id)
                        .filter(PollOption.poll_id == poll_id,
                                PollOption.position == int(row.option_number)
                                )
                        .one()
                    )
                except NoResultFound:
                    logger.debug(
                        f'poll_id#{poll_id}: Не найдено данных о результате с наибольшим количеством голосов')
                    continue

                if choice_message:
                    await bot.send_message(
                        chat_id=row.chat_id,
                        text=choice_message,
                    )
                else:
                    url_keyboard = types.InlineKeyboardMarkup()
                    url_keyboard.add(types.InlineKeyboardButton(text='Открыть ссылку', url=url))

                    await bot.send_message(
                        chat_id=row.chat_id,
                        text=f'Заказываем из *«{name}»*',
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=url_keyboard,
                    )

                polls_to_close.append(poll_id)

        # Проставление флага закрытия для обработанных опросов
        session.query(Poll).filter(Poll.id.in_(polls_to_close)).update({Poll.is_closed: True})
