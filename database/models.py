from sqlalchemy import Text, DateTime, func, Integer, event, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase):
    created: Mapped[DateTime] = mapped_column(DateTime, default=func.now())
    updated: Mapped[DateTime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


class Notes(Base):
    __tablename__ = 'note'

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)


@event.listens_for(Notes, 'before_insert')
def set_note_id(mapper, connection, target):
    session = sessionmaker(bind=connection)
    with session() as session:
        last_id_query = select(func.max(Notes.id)).where(Notes.user_id == target.user_id)
        result = session.execute(last_id_query)
        last_id = result.scalar_one_or_none()
        target.id = 1 if last_id is None else last_id + 1
