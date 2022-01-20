from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Time
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database.core import Base, BaseTable, BaseTableWithStringID


class Subscription(BaseTable):
    __tablename__ = 'subscriptions'

    chat_id = Column(Integer)
    bot_id = Column(Integer)
    mailing_time = Column(Time)


class PlaceType(BaseTable):
    __tablename__ = 'place_types'

    name = Column(String(100), nullable=False)


class Place(BaseTable):
    __tablename__ = 'places'

    name = Column(String(500))
    url = Column(String)
    place_type_id = Column(Integer, ForeignKey('place_types.id'), nullable=False)
    place_type = relationship(PlaceType)


class Poll(BaseTableWithStringID):
    __tablename__ = 'polls'

    chat_id = Column(Integer)
    start_date = Column(DateTime, default=func.now())
    open_period = Column(Integer)
    is_closed = Column(Boolean, default=False)


class PollOption(BaseTable):
    __tablename__ = 'polls_options'

    poll_id = Column(String)
    position = Column(Integer)
    option_id = Column(Integer)


class PollVote(BaseTable):
    __tablename__ = 'polls_votes'

    poll_id = Column(String)
    user_id = Column(Integer)
    option_number = Column(Integer)


class ChatTimezone(Base):
    __tablename__ = 'chats_timezones'

    chat_id = Column(Integer, nullable=False, unique=True, primary_key=True)
    sign = Column(Integer)
    offset = Column(Time)
