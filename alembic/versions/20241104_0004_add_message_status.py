"""add message status

Revision ID: 20241104_0004
Revises: 20241104_0003
Create Date: 2024-11-04

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20241104_0004'
down_revision = '20241104_0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Добавляем поле status в таблицу messages
    # По умолчанию 'delivered' - сообщение доставлено на сервер
    op.add_column('messages', sa.Column('status', sa.String(20), nullable=False, server_default='delivered'))
    
    # Создаем индекс для быстрого поиска по статусу
    op.create_index('ix_messages_status', 'messages', ['status'])


def downgrade() -> None:
    op.drop_index('ix_messages_status', table_name='messages')
    op.drop_column('messages', 'status')
