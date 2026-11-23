"""contact_inbox

Crea las tablas del buzón de contacto: contact_threads y contact_messages.

Revision ID: c7e2a41d9b05
Revises: 9bdb2082f183
Create Date: 2026-11-23 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7e2a41d9b05'
down_revision: Union[str, Sequence[str], None] = '9bdb2082f183'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('contact_threads',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('subject', sa.String(length=300), nullable=False),
    sa.Column('contact_email', sa.String(length=320), nullable=False),
    sa.Column('contact_name', sa.String(length=200), nullable=True),
    sa.Column('status', sa.String(length=12), server_default='open', nullable=False),
    sa.Column('is_read', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('last_message_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_contact_threads_id'), 'contact_threads', ['id'], unique=False)
    op.create_index(op.f('ix_contact_threads_contact_email'), 'contact_threads', ['contact_email'], unique=False)
    op.create_index(op.f('ix_contact_threads_status'), 'contact_threads', ['status'], unique=False)
    op.create_index(op.f('ix_contact_threads_last_message_at'), 'contact_threads', ['last_message_at'], unique=False)

    op.create_table('contact_messages',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('thread_id', sa.Integer(), nullable=False),
    sa.Column('direction', sa.String(length=8), nullable=False),
    sa.Column('resend_email_id', sa.String(length=64), nullable=True),
    sa.Column('message_id', sa.String(length=500), nullable=True),
    sa.Column('in_reply_to', sa.String(length=500), nullable=True),
    sa.Column('from_addr', sa.String(length=320), nullable=False),
    sa.Column('to_addr', sa.String(length=320), nullable=True),
    sa.Column('subject', sa.String(length=300), nullable=True),
    sa.Column('body_text', sa.Text(), nullable=True),
    sa.Column('auth_summary', sa.String(length=80), nullable=True),
    sa.Column('sent_by', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['sent_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['thread_id'], ['contact_threads.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_contact_messages_id'), 'contact_messages', ['id'], unique=False)
    op.create_index(op.f('ix_contact_messages_thread_id'), 'contact_messages', ['thread_id'], unique=False)
    op.create_index(op.f('ix_contact_messages_resend_email_id'), 'contact_messages', ['resend_email_id'], unique=True)
    op.create_index(op.f('ix_contact_messages_message_id'), 'contact_messages', ['message_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_contact_messages_message_id'), table_name='contact_messages')
    op.drop_index(op.f('ix_contact_messages_resend_email_id'), table_name='contact_messages')
    op.drop_index(op.f('ix_contact_messages_thread_id'), table_name='contact_messages')
    op.drop_index(op.f('ix_contact_messages_id'), table_name='contact_messages')
    op.drop_table('contact_messages')
    op.drop_index(op.f('ix_contact_threads_last_message_at'), table_name='contact_threads')
    op.drop_index(op.f('ix_contact_threads_status'), table_name='contact_threads')
    op.drop_index(op.f('ix_contact_threads_contact_email'), table_name='contact_threads')
    op.drop_index(op.f('ix_contact_threads_id'), table_name='contact_threads')
    op.drop_table('contact_threads')
