import datetime as dt

import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import ENGINE
from database.tables import Poll, PollVote


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
        Poll.id.label('poll_id'),
        Poll.start_date,
        Poll.open_period,
        PollVote.option_number,
    )

    polls_to_process_query = (
        session
        .query(*cols_to_analyze, func.count(PollVote.option_number).label('num_votes'))
        .filter(Poll.is_closed == False)
        .outerjoin(PollVote, Poll.id == PollVote.poll_id)
        .group_by(*cols_to_analyze)
    )

    return pd.read_sql(polls_to_process_query.statement, ENGINE)


def get_polls_winners(df: pd.DataFrame) -> pd.DataFrame:
    """Возвращает таблицу, каждая строка которой содержит информацию об опросе и номер варианта-
    победителя."""
    if df.empty:
        return df.set_index('poll_id')

    df = df.sort_values(
        by=['poll_id', 'num_votes'],
        ascending=[True, False],
    )

    gb_polls = df.groupby('poll_id', group_keys=False)
    candidates = gb_polls.apply(lambda x: x[x.num_votes == x.num_votes.max()])

    return candidates.groupby('poll_id').agg(lambda x: x.sample(1))
