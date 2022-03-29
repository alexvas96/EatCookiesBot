from typing import Optional, Union

import numpy as np
import pandas as pd
from aiogram import Bot, types
from aiogram.types import ParseMode
from aiogram.utils.exceptions import BotBlocked, ChatNotFound
from dateutil.relativedelta import relativedelta
from loguru import logger
from sqlalchemy.orm import Session
from workalendar.europe import Russia

from database import ENGINE, QUERY_WINDOW_SIZE, session_scope
from database.tables import ChatTimezone, Place, Poll, PollOption, PollVote, Subscription
from translation import Translation
from utils import PlacesInfo, get_polls_votes, get_polls_winners, get_utc_now


DEFAULT_POLL_OPEN_PERIOD = 300
MIN_VOTES_FOR_ORDER = 2


def on_poll_creation(
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


class PollActions:
    def __init__(
        self,
        bot: Bot,
        open_period: int = DEFAULT_POLL_OPEN_PERIOD,
        places_info: Optional[PlacesInfo] = None,
        translation: Optional[Translation] = None,
    ) -> None:
        self.bot = bot
        self.open_period = open_period
        self.cal = Russia()
        self.places_info = places_info or PlacesInfo()
        self.translation = translation or Translation()

    async def create_lunch_poll(self, chat_id: int) -> None:
        """Создание и отправка опроса."""
        with session_scope() as session:
            query = (session
                     .query(Place.id, Place.name)
                     .order_by(Place.place_type_id, Place.id)
                     )

            options = pd.read_sql(query.statement, ENGINE)

            msg = await self.bot.send_poll(
                chat_id=chat_id,
                question='Откуда заказываем?',
                options=options.name.to_list(),
                is_anonymous=False,
                open_period=self.open_period,
            )

            on_poll_creation(poll=msg.poll, chat_id=chat_id, session=session, options=options)

    async def send_lunch_poll(self) -> None:
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
                          .filter(Subscription.bot_id == self.bot.id)
                          .join(ChatTimezone, Subscription.chat_id == ChatTimezone.chat_id)
                          )

            while True:
                start, stop = QUERY_WINDOW_SIZE * idx, QUERY_WINDOW_SIZE * (idx + 1)
                instances = query_subs.slice(start, stop).all()

                if instances is None:
                    break

                for (chat_id, mailing_time, sign, offset) in instances:
                    current_time = (
                        now + sign * relativedelta(hours=offset.hour, minutes=offset.minute)
                    )

                    if not self.cal.is_working_day(current_time.date()):
                        continue

                    if mailing_time == current_time.time():
                        try:
                            await self.create_lunch_poll(chat_id=chat_id)
                        except BotBlocked:
                            logger.info('bot id=%d is blocked for chat id=%d, removing' %
                                        (self.bot.id, chat_id))
                            query_subs.filter(Subscription.chat_id == chat_id).delete()

                if len(instances) < QUERY_WINDOW_SIZE:
                    break

                idx += 1

    @staticmethod
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

    async def get_customer(
        self,
        session: Session,
        chat_id: int,
        poll_id: str,
        last_customer_id: int,
    ) -> Union[types.User, None]:
        """Определение пользователя для создания заказа.

        :param session: экземпляр сессии.
        :param chat_id: ID чата.
        :param poll_id: ID опроса.
        :param last_customer_id: ID пользователя, который был выбран в прошлый раз.
        :return: случайный пользователь, проголосовавший за вариант с доставкой,
        который не был выбран в предыдущий раз.
        """
        query = session.query(
            PollVote.user_id,
        ).join(
            PollOption,
            (PollOption.poll_id == PollVote.poll_id) &
            (PollOption.position == PollVote.option_number)
        ).filter(
            PollVote.poll_id == poll_id,
            PollOption.option_id.not_in(self.places_info.not_delivery_ids),
        )

        user_ids = set(x for x, in query.all())

        if last_customer_id in user_ids:
            user_ids.remove(last_customer_id)

        chosen_user = None

        try:
            chat_member = await self.bot.get_chat_member(
                chat_id=chat_id,
                user_id=np.random.choice(list(user_ids))
            )
            chosen_user = chat_member.user
        except ChatNotFound:
            logger.info(f'Нет доступа к чату {chat_id}, пользователь не определен')

        return chosen_user

    async def send_polls_results(self) -> None:
        """Отправка информации о результатах опроса."""
        with session_scope() as session:
            votes = get_polls_votes(session)
            winners = get_polls_winners(votes)
            chats_to_process = winners.chat_id.unique().tolist()

            query_customer = session.query(
                Subscription.chat_id,
                Subscription.last_customer_id,
            ).filter(Subscription.chat_id.in_(chats_to_process))

            last_customers = dict(query_customer.all())
            polls_to_close = []

            for poll_id, row in winners.iterrows():
                chat_id = row.chat_id

                if row.num_votes < MIN_VOTES_FOR_ORDER:
                    await self.bot.send_message(
                        chat_id=chat_id,
                        text=self.translation.not_enough_votes_to_delivery,
                    )
                    polls_to_close.append(poll_id)
                    continue

                name, url, choice_message = (
                    session
                    .query(Place.name, Place.url, Place.choice_message)
                    .join(PollOption, Place.id == PollOption.option_id)
                    .filter(PollOption.poll_id == poll_id,
                            PollOption.position == row.option_number,
                            )
                    .one()
                )

                if choice_message:
                    await self.bot.send_message(
                        chat_id=chat_id,
                        text=choice_message,
                    )
                else:
                    url_keyboard = types.InlineKeyboardMarkup().row(
                        types.InlineKeyboardButton(text=self.translation.go_to_site, url=url)
                    )

                    customer_text = ''

                    user = await self.get_customer(
                        session=session,
                        chat_id=chat_id,
                        poll_id=poll_id,
                        last_customer_id=last_customers[chat_id],
                    )

                    if user:
                        customer_text = f'\n{user.mention}, я выбираю тебя!'
                        last_customers[chat_id] = user

                    await self.bot.send_message(
                        chat_id=chat_id,
                        text=f'Заказываем из *«{name}»*' + customer_text,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=url_keyboard,
                    )

                polls_to_close.append(poll_id)

            subs = session.query(Subscription).filter(
                Subscription.chat_id.in_(chats_to_process)
            )

            # TODO: переписать на bulk_update_mappings
            for row in subs:
                row.last_customer_id = last_customers[row.chat_id]

            # Проставление флага закрытия для обработанных опросов
            session.query(Poll).filter(Poll.id.in_(polls_to_close)).update({Poll.is_closed: True})


def _clean_polls():
    with session_scope() as session:
        polls_to_delete = session.query(Poll.id).filter(Poll.is_closed == True).all()
        polls_to_delete = [x[0] for x in polls_to_delete]

        session.query(PollVote).filter(PollVote.poll_id.in_(polls_to_delete)).delete()
        session.query(PollOption).filter(PollOption.poll_id.in_(polls_to_delete)).delete()
        session.query(Poll).filter(Poll.id.in_(polls_to_delete)).delete()
