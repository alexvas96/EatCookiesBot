
from contextlib import contextmanager
from sqlalchemy import create_engine

from sqlalchemy.orm import sessionmaker
from settings import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD

engine = create_engine(
        f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}',
        echo=True,
    )
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

DBSession = sessionmaker(
    binds={
        Base: engine,
    },
    expire_on_commit=False,
)


@contextmanager
def session_scope():
    """Provides a transactional scope around a series of operations."""
    session = DBSession()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

from sqlalchemy import Column, Integer, ForeignKey, Text, orm, String


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
    place_type = orm.relationship(PlaceType)  # innerjoin=True для использования JOIN вместо LEFT JOIN
