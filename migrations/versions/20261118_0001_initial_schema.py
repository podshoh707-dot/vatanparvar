"""Initial schema: barcha 12 jadval (PostgreSQL + SQLite mos).

Revision ID: 20261118_0001
Revises:
Create Date: 2026-11-18 19:00:00
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261118_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "admins",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=128), nullable=True),
        sa.Column("full_name", sa.String(length=256), nullable=True),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("added_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_admins"),
    )
    op.create_index("ix_admins_telegram_id", "admins", ["telegram_id"], unique=True)
    op.create_index("ix_admins_is_active", "admins", ["is_active"], unique=False)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=128), nullable=True),
        sa.Column("first_name", sa.String(length=256), nullable=True),
        sa.Column("last_name", sa.String(length=256), nullable=True),
        sa.Column("language_code", sa.String(length=16), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_subscribed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("total_answers", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correct_answers", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)
    op.create_index("ix_users_is_active", "users", ["is_active"], unique=False)
    op.create_index("ix_users_is_blocked", "users", ["is_blocked"], unique=False)

    op.create_table(
        "posts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("post_type", sa.String(length=16), nullable=False),
        sa.Column("content_type", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("media_file_id", sa.String(length=512), nullable=True),
        sa.Column("buttons_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("channel_id", sa.String(length=64), nullable=True),
        sa.Column("channel_message_id", sa.BigInteger(), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column("updated_by", sa.BigInteger(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_posts"),
    )
    op.create_index("ix_posts_post_type", "posts", ["post_type"], unique=False)
    op.create_index("ix_posts_status", "posts", ["status"], unique=False)
    op.create_index("ix_posts_channel_message_id", "posts", ["channel_message_id"], unique=False)
    op.create_index("ix_posts_scheduled_at", "posts", ["scheduled_at"], unique=False)
    op.create_index("ix_posts_created_by", "posts", ["created_by"], unique=False)

    op.create_table(
        "test_questions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("option_a", sa.String(length=512), nullable=False),
        sa.Column("option_b", sa.String(length=512), nullable=False),
        sa.Column("option_c", sa.String(length=512), nullable=False),
        sa.Column("option_d", sa.String(length=512), nullable=False),
        sa.Column("correct_option", sa.String(length=1), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("topic", sa.String(length=128), nullable=False),
        sa.Column("difficulty", sa.String(length=16), nullable=False),
        sa.Column("image_file_id", sa.String(length=512), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column("approved_by", sa.BigInteger(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("times_published", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_test_questions"),
    )
    op.create_index("ix_test_questions_topic", "test_questions", ["topic"], unique=False)
    op.create_index("ix_test_questions_difficulty", "test_questions", ["difficulty"], unique=False)
    op.create_index("ix_test_questions_status", "test_questions", ["status"], unique=False)
    op.create_index("ix_test_questions_content_hash", "test_questions", ["content_hash"], unique=True)

    op.create_table(
        "published_tests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.String(length=64), nullable=False),
        sa.Column("channel_message_id", sa.BigInteger(), nullable=False),
        sa.Column("poll_id", sa.String(length=128), nullable=True),
        sa.Column("mode", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("reveal_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revealed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reveal_message_id", sa.BigInteger(), nullable=True),
        sa.Column("total_votes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correct_votes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("wrong_votes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("published_by", sa.BigInteger(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["test_questions.id"],
            name="fk_published_tests_question_id_test_questions",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_published_tests"),
    )
    op.create_index("ix_published_tests_question_id", "published_tests", ["question_id"], unique=False)
    op.create_index("ix_published_tests_channel_message_id", "published_tests", ["channel_message_id"], unique=False)
    op.create_index("ix_published_tests_poll_id", "published_tests", ["poll_id"], unique=True)
    op.create_index("ix_published_tests_status", "published_tests", ["status"], unique=False)
    op.create_index("ix_published_tests_published_at", "published_tests", ["published_at"], unique=False)

    op.create_table(
        "test_answers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("published_test_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("user_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("selected_option", sa.String(length=1), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["published_test_id"],
            ["published_tests.id"],
            name="fk_test_answers_published_test_id_published_tests",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["test_questions.id"],
            name="fk_test_answers_question_id_test_questions",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_test_answers"),
        sa.UniqueConstraint("published_test_id", "user_telegram_id", name="uq_test_answers_published_user"),
    )
    op.create_index("ix_test_answers_published_test_id", "test_answers", ["published_test_id"], unique=False)
    op.create_index("ix_test_answers_question_id", "test_answers", ["question_id"], unique=False)
    op.create_index("ix_test_answers_user_telegram_id", "test_answers", ["user_telegram_id"], unique=False)

    op.create_table(
        "test_attempts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("selected_option", sa.String(length=1), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_test_attempts_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["test_questions.id"],
            name="fk_test_attempts_question_id_test_questions",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_test_attempts"),
    )
    op.create_index("ix_test_attempts_user_id", "test_attempts", ["user_id"], unique=False)
    op.create_index("ix_test_attempts_question_id", "test_attempts", ["question_id"], unique=False)
    op.create_index("ix_test_attempts_answered_at", "test_attempts", ["answered_at"], unique=False)

    op.create_table(
        "scheduled_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_type", sa.String(length=40), nullable=False),
        sa.Column("reference_id", sa.Integer(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(length=128), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_scheduled_jobs"),
    )
    op.create_index("ix_scheduled_jobs_job_type", "scheduled_jobs", ["job_type"], unique=False)
    op.create_index("ix_scheduled_jobs_reference_id", "scheduled_jobs", ["reference_id"], unique=False)
    op.create_index("ix_scheduled_jobs_idempotency_key", "scheduled_jobs", ["idempotency_key"], unique=True)
    op.create_index("ix_scheduled_jobs_run_at", "scheduled_jobs", ["run_at"], unique=False)
    op.create_index("ix_scheduled_jobs_status", "scheduled_jobs", ["status"], unique=False)

    op.create_table(
        "settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("value_type", sa.String(length=24), nullable=False),
        sa.Column("description", sa.String(length=256), nullable=True),
        sa.Column("updated_by", sa.BigInteger(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_settings"),
    )
    op.create_index("ix_settings_key", "settings", ["key"], unique=True)

    op.create_table(
        "activity_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("admin_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=True),
        sa.Column("target_id", sa.String(length=64), nullable=True),
        sa.Column("details_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_activity_logs"),
    )
    op.create_index("ix_activity_logs_admin_telegram_id", "activity_logs", ["admin_telegram_id"], unique=False)
    op.create_index("ix_activity_logs_action", "activity_logs", ["action"], unique=False)
    op.create_index("ix_activity_logs_created_at", "activity_logs", ["created_at"], unique=False)

    op.create_table(
        "broadcasts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("content_type", sa.String(length=16), nullable=False),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("media_file_id", sa.String(length=512), nullable=True),
        sa.Column("buttons_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("total_targets", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sent_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("blocked_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_broadcasts"),
    )
    op.create_index("ix_broadcasts_status", "broadcasts", ["status"], unique=False)

    op.create_table(
        "backup_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("backup_type", sa.String(length=24), nullable=False),
        sa.Column("file_name", sa.String(length=256), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tables_included", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("record_counts_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_backup_history"),
    )


def downgrade() -> None:
    op.drop_table("backup_history")
    op.drop_table("broadcasts")
    op.drop_table("activity_logs")
    op.drop_table("settings")
    op.drop_table("scheduled_jobs")
    op.drop_table("test_attempts")
    op.drop_table("test_answers")
    op.drop_table("published_tests")
    op.drop_table("test_questions")
    op.drop_table("posts")
    op.drop_table("users")
    op.drop_table("admins")
