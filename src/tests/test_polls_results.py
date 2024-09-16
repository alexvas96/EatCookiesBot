import pandas as pd
from hypothesis import HealthCheck, given, settings

from tests.mock.poll_votes import polls_votes
from utils import get_polls_winners


@given(polls_votes())
@settings(suppress_health_check=(HealthCheck.too_slow,))
def test_polls_results(df: pd.DataFrame) -> None:
    res = get_polls_winners(df)
    assert res.index.name == 'poll_id'
    assert res.index.is_unique
