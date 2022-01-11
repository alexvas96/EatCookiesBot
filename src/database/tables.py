from sqlalchemy import Column, Integer, String, ForeignKey, orm
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()


class Subscription(Base):
    __tablename__ = 'subscriptions'

    chat_id = Column(Integer, primary_key=True)


class PlaceType(Base):
    __tablename__ = 'place_types'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)


class Place(Base):
    __tablename__ = 'places'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(500))
    url = Column(String)
    place_type_id = Column(Integer, ForeignKey('place_types.id'), nullable=False)
    place_type = orm.relationship(PlaceType)
