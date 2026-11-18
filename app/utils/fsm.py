"""Barcha admin va foydalanuvchi oqimlari uchun FSM holatlari."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class PostCreateState(StatesGroup):
    waiting_content = State()
    waiting_buttons = State()
    waiting_schedule_time = State()
    confirm = State()


class PostEditState(StatesGroup):
    waiting_new_text = State()
    waiting_new_buttons = State()


class AdCreateState(StatesGroup):
    waiting_content = State()
    waiting_buttons = State()
    waiting_schedule_time = State()
    confirm = State()


class AdEditState(StatesGroup):
    waiting_new_text = State()


class TestCreateState(StatesGroup):
    waiting_question = State()
    waiting_option_a = State()
    waiting_option_b = State()
    waiting_option_c = State()
    waiting_option_d = State()
    waiting_correct = State()
    waiting_explanation = State()
    waiting_topic = State()
    waiting_difficulty = State()
    waiting_image = State()
    confirm = State()


class TestEditState(StatesGroup):
    choosing_field = State()
    waiting_value = State()


class TestSearchState(StatesGroup):
    waiting_query = State()


class TestImportState(StatesGroup):
    waiting_excel_file = State()


class AutoPublishConfigState(StatesGroup):
    waiting_tests_per_day = State()
    waiting_start_time = State()
    waiting_interval_minutes = State()
    waiting_reveal_delay = State()


class AdminManageState(StatesGroup):
    waiting_telegram_id = State()
    waiting_role = State()


class BroadcastState(StatesGroup):
    waiting_content = State()
    waiting_buttons = State()
    confirm = State()


class SettingsEditState(StatesGroup):
    waiting_about_text = State()
    waiting_welcome_text = State()
