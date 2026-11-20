"""baseline_missing_tables

Pone bajo control de Alembic lo que hasta ahora creaba Base.metadata.create_all():
tablas expeditions, impact_tiles, navigator_envelopes, user_impact_hexes y las
columnas nodes.logo_frame, nodes.unlocked_frames, nodes.description y
users.preferred_language.

Es idempotente: en producción (donde todo eso ya existe) no hace nada, y en una
base de datos nueva lo crea. Cada objeto se comprueba antes de crearlo.

Revision ID: 9bdb2082f183
Revises: 968e228cdad4
Create Date: 2026-11-20 11:09:59.209469

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9bdb2082f183'
down_revision: Union[str, Sequence[str], None] = '968e228cdad4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(name: str) -> bool:
    # Inspector nuevo en cada llamada para no arrastrar caché de tablas recién creadas
    return sa.inspect(op.get_bind()).has_table(name)


def _has_column(table: str, column: str) -> bool:
    if not _has_table(table):
        return False
    cols = sa.inspect(op.get_bind()).get_columns(table)
    return any(c["name"] == column for c in cols)


def upgrade() -> None:
    """Crea solo lo que falte."""
    if not _has_table('expeditions'):
        op.create_table('expeditions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('slug', sa.String(length=40), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('task_type', sa.String(length=40), nullable=True),
        sa.Column('goal_value', sa.Integer(), nullable=False),
        sa.Column('current_value', sa.Integer(), nullable=False),
        sa.Column('reward_frame', sa.String(length=40), nullable=True),
        sa.Column('reward_badge_id', sa.String(length=40), nullable=True),
        sa.Column('starts_at', sa.DateTime(), nullable=False),
        sa.Column('ends_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_expeditions_id'), 'expeditions', ['id'], unique=False)
        op.create_index(op.f('ix_expeditions_slug'), 'expeditions', ['slug'], unique=True)

    if not _has_table('impact_tiles'):
        op.create_table('impact_tiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('slug', sa.String(length=40), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_impact_tiles_id'), 'impact_tiles', ['id'], unique=False)
        op.create_index(op.f('ix_impact_tiles_slug'), 'impact_tiles', ['slug'], unique=True)

    if not _has_table('navigator_envelopes'):
        op.create_table('navigator_envelopes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('expedition_slug', sa.String(length=40), nullable=False),
        sa.Column('tile_slug', sa.String(length=40), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('trigger', sa.String(length=20), nullable=True),
        sa.Column('hex_count_at_ready', sa.Integer(), nullable=True),
        sa.Column('task_count_at_ready', sa.Integer(), nullable=True),
        sa.Column('ready_at', sa.DateTime(), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('validated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'expedition_slug', name='uq_user_expedition_envelope')
        )
        op.create_index(op.f('ix_navigator_envelopes_expedition_slug'), 'navigator_envelopes', ['expedition_slug'], unique=False)
        op.create_index(op.f('ix_navigator_envelopes_id'), 'navigator_envelopes', ['id'], unique=False)
        op.create_index(op.f('ix_navigator_envelopes_user_id'), 'navigator_envelopes', ['user_id'], unique=False)

    if not _has_table('user_impact_hexes'):
        op.create_table('user_impact_hexes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('tile_slug', sa.String(length=40), nullable=False),
        sa.Column('hex_code', sa.String(length=10), nullable=False),
        sa.Column('color', sa.String(length=20), nullable=False),
        sa.Column('source', sa.String(length=40), nullable=False),
        sa.Column('expedition_slug', sa.String(length=40), nullable=True),
        sa.Column('lat', sa.Float(), nullable=True),
        sa.Column('lon', sa.Float(), nullable=True),
        sa.Column('unlocked_at', sa.DateTime(), nullable=False),
        sa.Column('validated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'tile_slug', 'hex_code', name='uq_user_tile_hex')
        )
        op.create_index(op.f('ix_user_impact_hexes_expedition_slug'), 'user_impact_hexes', ['expedition_slug'], unique=False)
        op.create_index(op.f('ix_user_impact_hexes_id'), 'user_impact_hexes', ['id'], unique=False)
        op.create_index(op.f('ix_user_impact_hexes_tile_slug'), 'user_impact_hexes', ['tile_slug'], unique=False)
        op.create_index(op.f('ix_user_impact_hexes_user_id'), 'user_impact_hexes', ['user_id'], unique=False)

    if not _has_column('nodes', 'logo_frame'):
        op.add_column('nodes', sa.Column('logo_frame', sa.String(length=40), nullable=True))
    if not _has_column('nodes', 'unlocked_frames'):
        op.add_column('nodes', sa.Column('unlocked_frames', sa.Text(), nullable=True))
    if not _has_column('nodes', 'description'):
        op.add_column('nodes', sa.Column('description', sa.Text(), nullable=True))

    # Producción tiene DEFAULT 'es' en esta columna; se replica para que una base nueva sea igual
    if not _has_column('users', 'preferred_language'):
        op.add_column(
            'users',
            sa.Column('preferred_language', sa.String(length=10), nullable=True, server_default='es'),
        )


def downgrade() -> None:
    """Intencionadamente vacío.

    Esta migración adopta objetos que en producción ya existían y contienen datos.
    No se puede saber qué creó ella y qué estaba antes, así que no se borra nada
    para evitar perder tablas o columnas con datos reales.
    """
    pass
