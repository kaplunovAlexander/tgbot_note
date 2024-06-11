from aiogram import F, types, Router
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.formatting import as_list, Bold
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Notes
from database.orm_query import orm_add_note, orm_get_notes, orm_delete_note, orm_get_note, orm_update_note
from filters.chat_types import ChatTypeFilter
from interface.inline import get_callback_btns
from interface.reply import get_keyboard

user_private_router = Router()
user_private_router.message.filter(ChatTypeFilter(['private']))


text = as_list(
    Bold("Команды бота:"),
    "/note - добавить заметку",
    "/get - получить список всех заметок",
    "/help or /menu - получить информацию о командах",
)

USER_KBD = get_keyboard(
    "Добавить заметку",
    "Все заметки",
    "Помощь",
    placeholder="Выберите опцию",
    sizes=(2, 1),
)


def create_notes_markdown(notes):
    markdown_notes = "<b>Ваши заметки:</b>\n\n"
    for i, note in enumerate(notes):
        markdown_notes += (
            f"<b>{i + 1}:</b> \n<pre>{note.description}</pre>"
        )
    return markdown_notes

class CurrentAction(StatesGroup):
    note = State()
    waiting_for_del_id = State()
    waiting_for_change_id = State()

    note_for_change = None


@user_private_router.message(CommandStart())
async def start_cmd(message: types.Message):
    await message.answer(text=text.as_html(), reply_markup=USER_KBD)


@user_private_router.message(F.text.lower().contains("помощь") | F.text.lower().contains("меню"))
@user_private_router.message(Command('menu'))
@user_private_router.message(Command('help'))
async def menu_cmd(message: types.Message):
    await message.answer(text.as_html())


@user_private_router.message(Command('Назад'))
@user_private_router.message(F.text.lower() == 'назад')
async def back(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()

    await message.answer(text=text.as_html(), reply_markup=USER_KBD)


@user_private_router.message(F.text.lower().contains("все заметки"))
@user_private_router.message(Command('get'))
async def get_node_cmd(message: types.Message, session: AsyncSession):
    user_id = message.from_user.id
    notes = await orm_get_notes(session, user_id)

    if not notes:
        await message.answer("У вас пока нет заметок.")
        return

    notes_markdown = create_notes_markdown(notes)

    await message.answer(notes_markdown, parse_mode="HTML", reply_markup=get_callback_btns(btns={
        'Удалить': f'delete_',
        'Изменить': f'change_',
    }))


@user_private_router.callback_query(F.data.startswith(f"delete_"))
async def delete_note_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("Введите ID заметки, которую нужно удалить.")
    await state.set_state(CurrentAction.waiting_for_del_id)


@user_private_router.message(CurrentAction.waiting_for_del_id)
async def delete_note_process(message: types.Message, state: FSMContext, session: AsyncSession):
    user_id = message.from_user.id
    note_id = int(message.text)

    await orm_delete_note(session, user_id, note_id)

    await session.execute(
        update(Notes)
        .where(Notes.user_id == user_id, Notes.id > note_id)
        .values(id=Notes.id - 1)
    )
    await session.commit()

    await message.answer("Заметка удалена")
    await state.clear()


@user_private_router.callback_query(StateFilter(None), F.data.startswith("change_"))
async def change_note_data_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("Введите ID заметки, которую нужно изменить.")
    await state.set_state(CurrentAction.waiting_for_change_id)


@user_private_router.message(CurrentAction.waiting_for_change_id)
async def change_note_process(message: types.Message, state: FSMContext, session: AsyncSession):
    user_id = message.from_user.id
    note_id = int(message.text)
    note_for_change = await orm_get_note(session, user_id, note_id)

    if note_for_change:
        await message.answer("Что вы хотите записать?", reply_markup=get_keyboard("Назад", sizes=(1, 0)))
        await state.update_data(note_for_change=note_for_change)
        await state.set_state(CurrentAction.note)
    else:
        await message.answer("Заметка не найдена. Попробуйте снова.", reply_markup=USER_KBD)
        await state.clear()



@user_private_router.message(StateFilter(None), F.text.lower().contains("добавить заметку"))
@user_private_router.message(Command('note'))
async def note_cmd(message: types.Message, state: FSMContext):
    await message.answer("Что вы хотите записать?", reply_markup=get_keyboard("Назад", sizes=(1, 0)))
    await state.set_state(CurrentAction.note)


@user_private_router.message(CurrentAction.note, F.text)
async def added_note_cmd(message: types.Message, state: FSMContext, session: AsyncSession):
    user_id = message.from_user.id
    await state.update_data(note=message.text)
    data = await state.get_data()

    try:

        note_for_change = CurrentAction.note_for_change

        if note_for_change:
            await orm_update_note(session, user_id, note_for_change.id, data)
            await message.answer("Заметка изменена", reply_markup=USER_KBD)
        else:
            await orm_add_note(session, user_id, data)
            await message.answer("Заметка добавлена", reply_markup=USER_KBD)

        await state.clear()

    except Exception as e:
        await message.answer(
            f"Ошибка: \n{str(e)}\nСообщите об этом в поддержку", reply_markup=USER_KBD
        )
        await state.clear()

    CurrentAction.note_for_change = None


@user_private_router.message()
async def errror_cmd(message: types.Message):
    await message.answer("Введены неверные данные. Пожалуйста, используйте доступные команды.")
