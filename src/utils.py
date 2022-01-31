import datetime as dt


def get_utc_now() -> dt.datetime:
    """Получить текущую дату и время по часовому поясу UTC."""
    return dt.datetime.utcnow().replace(second=0, microsecond=0)


def get_sign(value: int) -> str:
    if value >= 0:
        return '+'

    if value < 0:
        return '-'

    raise TypeError
