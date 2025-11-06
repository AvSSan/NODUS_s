"""add_friends_and_pinned_chats

Revision ID: 20241106_0006
Revises: 20241105_0005
Create Date: 2024-11-06 08:00:00.000000

Добавление функционала:
- Таблица friends для списка друзей
- Таблица pinned_chats для закрепленных чатов с лимитом на количество

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20241106_0006'
down_revision: Union[str, None] = '20241105_0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Создаем таблицу friends
    op.create_table(
        'friends',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('friend_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['friend_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'friend_id', name='uq_friends'),
        sa.CheckConstraint('user_id != friend_id', name='check_not_self_friend')
    )
    
    # Создаем индексы для friends
    op.create_index('ix_friends_user_id', 'friends', ['user_id'], unique=False)
    op.create_index('ix_friends_friend_id', 'friends', ['friend_id'], unique=False)
    op.create_index('ix_friends_status', 'friends', ['status'], unique=False)
    
    # Создаем таблицу pinned_chats
    op.create_table(
        'pinned_chats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('chat_id', sa.Integer(), nullable=False),
        sa.Column('pin_order', sa.Integer(), nullable=False),
        sa.Column('pinned_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['chat_id'], ['chats.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'chat_id', name='uq_pinned_chat')
    )
    
    # Создаем индексы для pinned_chats
    op.create_index('ix_pinned_chats_user_id', 'pinned_chats', ['user_id'], unique=False)
    op.create_index('ix_pinned_chats_chat_id', 'pinned_chats', ['chat_id'], unique=False)
    op.create_index('ix_pinned_chats_user_order', 'pinned_chats', ['user_id', 'pin_order'], unique=False)


def downgrade() -> None:
    # Удаляем таблицу pinned_chats
    op.drop_index('ix_pinned_chats_user_order', table_name='pinned_chats')
    op.drop_index('ix_pinned_chats_chat_id', table_name='pinned_chats')
    op.drop_index('ix_pinned_chats_user_id', table_name='pinned_chats')
    op.drop_table('pinned_chats')
    
    # Удаляем таблицу friends
    op.drop_index('ix_friends_status', table_name='friends')
    op.drop_index('ix_friends_friend_id', table_name='friends')
    op.drop_index('ix_friends_user_id', table_name='friends')
    op.drop_table('friends')
