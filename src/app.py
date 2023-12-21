
from litestar import Litestar, get, Router
from litestar.contrib.sqlalchemy.plugins import SQLAlchemySerializationPlugin
from litestar.response import File
from litestar.openapi import OpenAPIConfig
from litestar.openapi.spec import Tag
from attrs import define, field

from sqlalchemy import Column, Text, Integer, UniqueConstraint, DateTime
from sqlalchemy.sql import func
from litestar.contrib.sqlalchemy.dto import SQLAlchemyDTO

import pathlib

from litestar.datastructures import State
from litestar.exceptions import ClientException
from litestar.status_codes import HTTP_409_CONFLICT
from sqlalchemy.exc import IntegrityError


from litestar import Litestar
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import logging
LOGGER = logging.getLogger(__name__)

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData

POSTGRES_INDEXES_NAMING_CONVENTION = {
    "ix": "%(column_0_label)s_idx",
    "uq": "%(table_name)s_%(column_0_name)s_uniq_key",
    "ck": "%(table_name)s_%(constraint_name)s_check",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "%(table_name)s_pkey",
}


# declarative base class
class Base(DeclarativeBase):
    pass

Base.metadata.naming_convention = POSTGRES_INDEXES_NAMING_CONVENTION

class QuotesTable(Base):
	__tablename__ = 'quotes'

	id = Column(Integer, primary_key=True, autoincrement=True)
	quote = Column(Text, nullable=False, default="Hello, World!")
	created_tstamp = Column(DateTime(timezone=True), nullable=True, server_default=func.now())
	modified_tstamp = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())

	__table_args__= (UniqueConstraint("quote"),)

QuotesDTO = SQLAlchemyDTO[QuotesTable]

@asynccontextmanager
async def sqlite_connection(app: Litestar) -> AsyncGenerator[None, None]:
    sqlite_engine = getattr(app.state, "sqlite_engine", None)
    if sqlite_engine is None:
        sqlite_engine = create_async_engine("sqlite+aiosqlite:///internetwithviet.db", echo=True)
        app.state.sqlite_engine = sqlite_engine
    LOGGER.debug(f"app.state.sqlite_engine created {app.state.sqlite_engine}")
    async with sqlite_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield
    finally:
        await sqlite_engine.dispose()

sessionmaker = async_sessionmaker(expire_on_commit=False)


async def provide_sqlite_session(state: State) -> AsyncGenerator[AsyncSession, None]:
    async with sessionmaker(bind=state.sqlite_engine) as sqlite_session:
        try:
            async with sqlite_session.begin():
                yield sqlite_session
        except IntegrityError as exc:
            raise ClientException(
                status_code=HTTP_409_CONFLICT,
                detail=str(exc),
            ) from exc

from sqlalchemy import select, func

@get("/", summary="Handler function that returns a greeting dictionary.")
async def hello_world() -> dict[str, str]:
    """Handler function that returns a greeting dictionary."""
    return {"hello": "world"}

from litestar.controller import Controller

async def get_all_quotes(sqlite_session: AsyncSession) -> list[QuotesTable]:
    query = select(QuotesTable)
    result = await sqlite_session.execute(query)
    return result.scalars().all()

from datetime import datetime


@define
class BaseResponse:
    ts: datetime = datetime.utcnow()

from typing import Generic, TypeVar
T = TypeVar("T")



@define
class GetAllQuotesResponse(Generic[T]):
    quotes: list[T]

class QuotesAPI(Controller):
    path = '/quote'
    tags = ['Quotes']

    @get('/all')
    async def get_all_quotes(self, sqlite_session: AsyncSession) -> list[QuotesTable]:
        return await get_all_quotes(sqlite_session)
    
    @get('/all-not-working', return_dto=QuotesDTO)
    async def get_all_quotes_not_working(self, sqlite_session: AsyncSession) -> GetAllQuotesResponse:
        res = GetAllQuotesResponse(quotes=await get_all_quotes(sqlite_session))
        LOGGER.critical(f"sherlock {res}")
        return res

api_router = Router(
    path="/api", 
    route_handlers=[QuotesAPI],   
)

app = Litestar(
    [hello_world, api_router],
    openapi_config=OpenAPIConfig(
        title="Internet With Viet Backend",
        version='0.1',
        tags=[
            Tag(name="Quotes", description="Routes to interact with Quotes data")
        ],
    ),
    dependencies={
        "sqlite_session": provide_sqlite_session,
    }, # DI into  
    lifespan=[sqlite_connection], # connection lasts lifespan of application
    plugins=[SQLAlchemySerializationPlugin()],
)