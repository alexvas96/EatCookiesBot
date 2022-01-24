from contextlib import contextmanager
from typing import Generator

from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.session import Session, sessionmaker

from settings import DB_HOST, DB_NAME, DB_PASSWORD, DB_USER


QUERY_WINDOW_SIZE = 100

ENGINE = create_engine(
    f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}',
    # echo=True,
)

Base = declarative_base()

DBSession = sessionmaker(
    binds={
        Base: ENGINE,
    },
    expire_on_commit=False,
)


class BaseTable(Base):
    __abstract__ = True

    id = Column(Integer, nullable=False, unique=True, primary_key=True, autoincrement=True)


class BaseTableWithStringID(Base):
    __abstract__ = True

    id = Column(String, nullable=False, unique=True, primary_key=True)


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
