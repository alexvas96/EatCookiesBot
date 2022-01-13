from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database.core import BaseTable


class Subscription(BaseTable):
    __tablename__ = 'subscriptions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(Integer)
    bot_id = Column(Integer)


class PlaceType(BaseTable):
    __tablename__ = 'place_types'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)


class Place(BaseTable):
    __tablename__ = 'places'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(500))
    url = Column(String)
    place_type_id = Column(Integer, ForeignKey('place_types.id'), nullable=False)
    place_type = relationship(PlaceType)


class Poll(BaseTable):
    __tablename__ = 'polls'

    id = Column(String, primary_key=True)
    chat_id = Column(Integer)


class PollVote(BaseTable):
    __tablename__ = 'polls_votes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    poll_id = Column(String)
    user_id = Column(Integer)
    option_number = Column(Integer)
