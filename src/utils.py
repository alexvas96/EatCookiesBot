import datetime as dt
import re
from typing import Optional

import pandas as pd
from loguru import logger
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import INTERVAL
from sqlalchemy.orm import Session
from sqlalchemy.sql.functions import concat

from database import ENGINE, session_scope
from database.tables import Place, Poll, PollVote


REGEX_NORMALIZATION = re.compile(r'[.\s-]')
POLL_ID = 'poll_id'


class PlacesInfo:
    """Класс предназначен для хранения прочитанной из БД информации о местах для заказов."""

    def __init__(self) -> None:
        self.places: Optional[pd.DataFrame] = None
        self.names_regex: Optional[re.Pattern] = None
        self.not_delivery_ids = []
        self.update_places()

    def update_places(self) -> None:
        with session_scope() as session:
            query = session.query(Place.name, Place.url).filter(Place.is_delivery == True)
            df = pd.read_sql(query.statement, ENGINE)

            if df.empty:
                logger.info('Данные о местах не найдены')
                return

            df['normalized_name'] = (df.name
                                     .str.lower()
                                     .str.replace(pat=REGEX_NORMALIZATION, repl='', regex=True)
                                     )
            self.places = df.set_index('normalized_name').sort_index()
            self.names_regex = re.compile('(' + '|'.join(self.places.index) + ')')

            query_not_delivery = session.query(Place.id).filter(Place.is_delivery == False)
            self.not_delivery_ids = [r for r, in query_not_delivery.all()]

        logger.info(self.__class__.__name__ + ': updated')


def get_utc_now() -> dt.datetime:
    """Получить текущую дату и время по часовому поясу UTC."""
    return dt.datetime.utcnow().replace(second=0, microsecond=0)


def get_sign(value: int) -> str:
    """Строковое представление знака числа."""
    if value >= 0:
        return '+'

    if value < 0:
        return '-'

    raise TypeError


def get_polls_votes(session: Session) -> pd.DataFrame:
    """Возвращает таблицу с информацией о количестве голосов за варианты опросов."""
    cols_to_analyze = (
        Poll.chat_id,
        Poll.id.label(POLL_ID),
        Poll.start_date,
        Poll.open_period,
        PollVote.option_number,
    )

    time_condition = (
        func.timezone('utc', func.now()) >= Poll.start_date +
        func.cast(concat(Poll.open_period, ' SECONDS'), INTERVAL)
    )

    polls_to_process_query = (
        session
        .query(*cols_to_analyze, func.count(PollVote.option_number).label('num_votes'))
        .filter(Poll.is_closed == False, time_condition)
        .outerjoin(PollVote, Poll.id == PollVote.poll_id)
        .group_by(*cols_to_analyze)
    )

    return pd.read_sql(polls_to_process_query.statement, ENGINE)


def get_polls_winners(df: pd.DataFrame) -> pd.DataFrame:
    """Возвращает таблицу, каждая строка которой содержит информацию об опросе и номер варианта-
    победителя."""
    if df.empty:
        return df.set_index(POLL_ID)

    df = df.sort_values(
        by=[POLL_ID, 'num_votes'],
        ascending=[True, False],
    )

    gb_polls = df.groupby(POLL_ID, group_keys=False)
    candidates = gb_polls.apply(lambda x: x[x.num_votes == x.num_votes.max()])

    return candidates.groupby(POLL_ID).agg(lambda x: x.sample(1))
