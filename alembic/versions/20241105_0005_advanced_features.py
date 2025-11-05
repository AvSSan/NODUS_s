"""advanced_features

Revision ID: 20241105_0005
Revises: 20241104_0004
Create Date: 2024-11-05 12:40:00.000000

Добавление расширенных функций:
- Поля reply_to_id, is_deleted, deleted_at, updated_at в messages
- Таблица message_reactions для реакций на сообщения

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20241105_0005'
down_revision: Union[str, None] = '20241104_0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавляем новые поля в таблицу messages
    op.add_column('messages', sa.Column('reply_to_id', sa.Integer(), nullable=True))
    op.add_column('messages', sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('messages', sa.Column('deleted_at', sa.DateTime(), nullable=True))
    op.add_column('messages', sa.Column('updated_at', sa.DateTime(), nullable=True))
    
    # Создаем индексы
    op.create_index('ix_messages_reply_to_id', 'messages', ['reply_to_id'], unique=False)
    op.create_index('ix_messages_is_deleted', 'messages', ['is_deleted'], unique=False)
    
    # Создаем foreign key для reply_to_id
    op.create_foreign_key(
        'fk_messages_reply_to_id',
        'messages', 'messages',
        ['reply_to_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Создаем таблицу message_reactions
    op.create_table(
        'message_reactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('emoji', sa.String(length=10), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('message_id', 'user_id', 'emoji', name='uq_message_reaction')
    )
    
    # Создаем индекс для message_reactions
    op.create_index('ix_message_reactions_message_id', 'message_reactions', ['message_id'], unique=False)


def downgrade() -> None:
    # Удаляем таблицу message_reactions
    op.drop_index('ix_message_reactions_message_id', table_name='message_reactions')
    op.drop_table('message_reactions')
    
    # Удаляем foreign key и индексы из messages
    op.drop_constraint('fk_messages_reply_to_id', 'messages', type_='foreignkey')
    op.drop_index('ix_messages_is_deleted', table_name='messages')
    op.drop_index('ix_messages_reply_to_id', table_name='messages')
    
    # Удаляем колонки из messages
    op.drop_column('messages', 'updated_at')
    op.drop_column('messages', 'deleted_at')
    op.drop_column('messages', 'is_deleted')
    op.drop_column('messages', 'reply_to_id')
