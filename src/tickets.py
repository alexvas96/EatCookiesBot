import aiohttp
from aiogram import Bot
from loguru import logger
from pydantic import BaseModel, Extra, conlist
from sqlalchemy import select

from database import session_scope
from database.tables import Subscription
from settings import DEPARTMENT_ID, EMPLOYEE_SURNAMES, TICKETS_API_URL


class Direction(BaseModel):
    class Config:
        extra = Extra.forbid

    freelTicket: int
    availableTicket: int
    external_id: str
    speciality: conlist(dict, min_items=1, max_items=1)
    fullName: str
    unique_id: str
    nearestDate: str | None


class TicketsInfo(BaseModel):
    result: list[Direction]


async def get_tickets_info(second_names: list[str]) -> Direction | None:
    data = {
        'method': 'record/getPersons',
        'params': {
            'hospital_id': DEPARTMENT_ID,
        }
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            TICKETS_API_URL, params={'method': 'record/getPersons'}, json=data,
        ) as resp:
            if resp.status >= 400:
                logger.error(f'Ошибка при обработке запроса: {resp.status}')
                return

            resp_data = await resp.text()
            tickets_info = TicketsInfo.parse_raw(resp_data)

    for direction in tickets_info.result:
        if any(direction.fullName.startswith(second_name) for second_name in second_names) \
                and direction.availableTicket > 0:
            return direction


async def check_tickets(bot: Bot):
    direction = await get_tickets_info(EMPLOYEE_SURNAMES)

    if not direction:
        return

    text = (f'{direction.fullName}\n'
            f'Найдено талонов: {direction.availableTicket}\n'
            f'Ближайшая дата записи: {direction.nearestDate}'
            )

    with session_scope() as session:
        stmt = select(Subscription.chat_id).filter(Subscription.bot_id == bot.id)
        chats = session.execute(stmt).scalars()

    for chat_id in chats:
        await bot.send_message(chat_id=chat_id, text=text)
