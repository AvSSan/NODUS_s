"""add message reads

Revision ID: 20241104_0003
Revises: 20241104_0002
Create Date: 2024-11-04

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20241104_0003'
down_revision = '20241104_0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Создаем таблицу для отслеживания прочитанных сообщений
    op.create_table(
        'message_reads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('read_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('message_id', 'user_id', name='uq_message_read')
    )
    
    # Создаем индексы для быстрого поиска
    op.create_index('ix_message_reads_message_id', 'message_reads', ['message_id'])
    op.create_index('ix_message_reads_user_id', 'message_reads', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_message_reads_user_id', table_name='message_reads')
    op.drop_index('ix_message_reads_message_id', table_name='message_reads')
    op.drop_table('message_reads')
