from datetime import datetime

import pandas as pd
from sqlalchemy import (
    Column, Integer, String, BigInteger, DateTime
)
from sqlalchemy import update as sqlalchemy_update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.future import select
from sqlalchemy.orm import declarative_base, sessionmaker

from config import ELE_URL

Base = declarative_base()


class AsyncDatabaseSession:
    def __init__(self):
        self._session = None
        self._engine = None

    def __getattr__(self, name):
        return getattr(self._session, name)

    async def init(self):
        self._engine = create_async_engine(
            ELE_URL,
            echo=False,  # echo = true to debug
        )

        self._session = sessionmaker(
            self._engine, expire_on_commit=False, class_=AsyncSession
        )()

    async def create_all(self):
        async with self._engine.begin() as conn:
            # await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)


async_db_session = AsyncDatabaseSession()


class ModelAdmin:
    id: int
    __tablename__: str

    @classmethod
    async def create(cls, **kwargs):
        async_db_session.add(cls(**kwargs))
        await async_db_session.commit()

    @classmethod
    async def update(cls, id, **kwargs):
        query = (
            sqlalchemy_update(cls)
            .where(cls.id == id)
            .values(**kwargs)
            .execution_options(synchronize_session="fetch")
        )

        await async_db_session.execute(query)
        await async_db_session.commit()

    @classmethod
    async def get(cls, id):
        query = select(cls).where(cls.id == id)
        results = await async_db_session.execute(query)
        (result,) = results.one()
        return result

    @classmethod
    async def get_df(cls):
        def _read_sql(con, stmt):
            return pd.read_sql(stmt, con)

        async with async_db_session._engine.begin() as conn:
            data = await conn.run_sync(_read_sql, cls.__tablename__)
        return data

    @classmethod
    async def to_csv(cls):
        df = await cls.get_df()
        df.to_csv(f'db_backup/{cls.__tablename__}.csv')


class Tags(Base, ModelAdmin):
    __tablename__ = 'tags'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, default='')
    owner_id = Column(BigInteger)
    content = Column(String, default='')
    uses = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now())

    def __repr__(self):
        return (
            f"<{self.__class__.__name__}("
            f"id={self.id}, "
            f"name={self.name}, "
            f")>"
        )
