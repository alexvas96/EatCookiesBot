import pandas as pd
from hypothesis import given

from tests.mock.poll_votes import polls_votes
from utils import get_polls_winners


@given(polls_votes())
def test_polls_results(df: pd.DataFrame) -> None:
    res = get_polls_winners(df)
    assert res.index.name == 'poll_id'
    assert res.index.is_unique


if __name__ == '__main__':
    test_polls_results()
