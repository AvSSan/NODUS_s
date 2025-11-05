from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20241104_0002"
down_revision: Union[str, None] = "20240326_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавляем колонку tag как nullable сначала
    op.add_column("users", sa.Column("tag", sa.String(length=32), nullable=True))
    
    # Генерируем теги для существующих пользователей
    # Используем email и id для создания уникального тега
    connection = op.get_bind()
    users = connection.execute(sa.text("SELECT id, email FROM users")).fetchall()
    
    for user_id, email in users:
        # Извлекаем часть email до @
        email_part = email.split('@')[0]
        # Удаляем специальные символы (оставляем только буквы, цифры, подчеркивания)
        import re
        email_part = re.sub(r'[^a-zA-Z0-9_]', '', email_part)
        # Обрезаем до 20 символов и добавляем id
        email_part = email_part[:20]
        tag = f"{email_part}_{user_id}".lower()
        
        # Обновляем пользователя
        connection.execute(
            sa.text("UPDATE users SET tag = :tag WHERE id = :id"),
            {"tag": tag, "id": user_id}
        )
    
    # Делаем колонку не nullable и добавляем индексы
    op.alter_column("users", "tag", nullable=False)
    op.create_index(op.f("ix_users_tag"), "users", ["tag"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_tag"), table_name="users")
    op.drop_column("users", "tag")
