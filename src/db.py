from contextlib import contextmanager
from typing import Generator

from sqlalchemy import Column, ForeignKey, Integer, String, create_engine, orm
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.session import Session

from settings import DB_HOST, DB_NAME, DB_PASSWORD, DB_USER


ENGINE = create_engine(
    f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}',
    echo=True,
)

Base = declarative_base()

DBSession = orm.sessionmaker(
    binds={
        Base: ENGINE,
    },
    expire_on_commit=False,
)


QUERY_WINDOW_SIZE = 100


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Provides a transactional scope around a series of operations."""
    session: Session = DBSession()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


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
