from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Notes


async def orm_add_note(session: AsyncSession, user_id: int, data: dict):
    async with session.begin():
        obj = Notes(
            user_id=user_id,
            description=data['note'],
        )
        session.add(obj)
        await session.commit()


async def orm_get_notes(session: AsyncSession, user_id: int):
    result = await session.execute(
        select(Notes).filter_by(user_id=user_id)
    )
    notes = result.scalars().all()
    return notes


async def orm_get_note(session: AsyncSession, user_id: int, note_id: int):
    result = await session.execute(
        select(Notes).filter_by(id=note_id, user_id=user_id)
    )
    note = result.scalar()
    return note


async def orm_update_note(session: AsyncSession, user_id: int,  note_id: int, data):
    async with session.begin():
        await session.execute(
            update(Notes)
            .where(Notes.id == note_id, Notes.user_id == user_id)
            .values(description=data["note"])
        )
        await session.commit()


async def orm_delete_note(session: AsyncSession, user_id: int, note_id: int):
    async with session.begin():
        await session.execute(
            delete(Notes).where(Notes.id == note_id, Notes.user_id == user_id)
        )
        await session.commit()
