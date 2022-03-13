from typing import Optional

import numpy as np
import pandas as pd
from hypothesis import HealthCheck, settings, strategies as st


MAX_OPTIONS = 10
MAX_VOTES_FOR_OPTION = 5 * MAX_OPTIONS
MAX_POLLS = 10

COLUMNS = ['chat_id', 'poll_id', 'start_date', 'open_period', 'option_number', 'num_votes']


@st.composite
def number_as_string(draw):
    """Строковое представление целого числа."""
    return str(draw(st.integers()))


@st.composite
def fix_len_lists(draw, length: int, elements: Optional[st.SearchStrategy] = None, **kwargs):
    """Список фиксированной длины."""
    if elements is None:
        elements = st.integers()

    return draw(st.lists(elements, min_size=length, max_size=length, **kwargs))


@st.composite
def option_votes_pairs(draw):
    """Генерация пар вида (номер опции, количество голосов)."""
    n = draw(st.integers(min_value=1, max_value=MAX_OPTIONS))  # Количество вариантов ответа
    option_numbers = np.arange(n)

    num_groups_with_duplicates = draw(st.integers(min_value=0, max_value=n))
    groups_for_options = draw(
        st.lists(
            st.integers(min_value=0, max_value=num_groups_with_duplicates),
            min_size=n,
            max_size=n,
        )
    )

    groups_for_options = dict(zip(option_numbers, groups_for_options))
    groups = {0: []}

    for k, v in groups_for_options.items():
        groups.setdefault(v, []).append(k)

    min_votes_items = len(groups[0]) + num_groups_with_duplicates

    rnd_votes_count = draw(
        st.integers(min_value=min_votes_items, max_value=n + num_groups_with_duplicates)
    )

    rnd_votes = draw(
        st.lists(
            st.integers(min_value=0, max_value=rnd_votes_count),
            min_size=min_votes_items,
            max_size=min_votes_items,
            unique=True,
        )
    )

    res = []

    for x in groups.pop(0):
        res.append((x, rnd_votes.pop()))

    for k, v in groups.items():
        value = rnd_votes.pop()
        [res.append((x, value)) for x in v]

    return res


@st.composite
@settings(suppress_health_check=(HealthCheck.too_slow,))  # TODO: убрать
def polls_votes(draw):
    """Генерация моковой выгрузки о количестве голосов за различные варианты в опросах."""
    num_polls = draw(st.integers(min_value=0, max_value=MAX_POLLS))

    columns_strategies = {
        'chat_id': fix_len_lists(num_polls, unique=True),
        'poll_id': fix_len_lists(num_polls, elements=number_as_string(), unique=True),
        'start_date': fix_len_lists(num_polls, elements=st.datetimes()),
        'open_period': fix_len_lists(num_polls, elements=st.integers(min_value=10, max_value=500)),
    }

    df = pd.DataFrame({k: draw(v) for k, v in columns_strategies.items()})
    all_df = pd.DataFrame(columns=COLUMNS)

    if df.empty:
        return all_df

    for _, row in df.iterrows():
        votes = pd.DataFrame(draw(option_votes_pairs()), columns=['option_number', 'num_votes'])
        votes[row.index] = row
        all_df = pd.concat([all_df, votes], axis=0)

    return all_df
