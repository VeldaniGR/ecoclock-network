"""campaigns_themes

Prepara las campañas superpuestas:
  - expeditions.theme y expeditions.tile_slug (temática y loseta de cada campaña)
  - tasks.theme (temática de cada tarea), rellenada desde el prefijo del nombre
  - expedition_participants (qué usuarios participan en qué campaña), rellenada
    con quienes ya completaron tareas de la temática dentro de las fechas

No cambia por sí sola el comportamiento de los clientes: eso llega después.

Revision ID: e5b3a9c71d28
Revises: c7e2a41d9b05
Create Date: 2026-11-26 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5b3a9c71d28'
down_revision: Union[str, Sequence[str], None] = 'c7e2a41d9b05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- columnas nuevas ---
    op.add_column('expeditions', sa.Column('theme', sa.String(length=40), nullable=True))
    op.add_column('expeditions', sa.Column('tile_slug', sa.String(length=40), nullable=True))
    op.add_column('tasks', sa.Column('theme', sa.String(length=40), nullable=True))
    op.create_index(op.f('ix_tasks_theme'), 'tasks', ['theme'], unique=False)

    # --- participantes por campaña ---
    op.create_table('expedition_participants',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('expedition_id', sa.Integer(), nullable=False),
    sa.Column('joined_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['expedition_id'], ['expeditions.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'expedition_id', name='uq_user_expedition_participant')
    )
    op.create_index(op.f('ix_expedition_participants_id'), 'expedition_participants', ['id'], unique=False)
    op.create_index(op.f('ix_expedition_participants_user_id'), 'expedition_participants', ['user_id'], unique=False)
    op.create_index(op.f('ix_expedition_participants_expedition_id'), 'expedition_participants', ['expedition_id'], unique=False)

    # --- relleno de datos existentes ---
    # Temática de las tareas = prefijo del nombre (arctic, fungi, ndvi, posidonia)
    op.execute("UPDATE tasks SET theme = LEFT(split_part(name, '-', 1), 40) WHERE theme IS NULL")

    # Temática de las dos campañas que ya existen
    op.execute("UPDATE expeditions SET theme = 'fungi' WHERE slug = 'autumn-fungi-2026'")
    op.execute(
        "UPDATE expeditions SET theme = 'arctic', tile_slug = 'arctic' "
        "WHERE slug = 'arctic-winter-2026'"
    )

    # Participantes: quien completó tareas de la temática dentro de las fechas de la campaña
    op.execute(
        """
        INSERT INTO expedition_participants (user_id, expedition_id, joined_at)
        SELECT t.user_id, e.id, MIN(t.completed_at)
        FROM tasks t
        JOIN expeditions e
          ON e.theme IS NOT NULL
         AND t.theme = e.theme
         AND t.completed_at BETWEEN e.starts_at AND e.ends_at
        WHERE t.status = 'done' AND t.user_id IS NOT NULL
        GROUP BY t.user_id, e.id
        ON CONFLICT (user_id, expedition_id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_expedition_participants_expedition_id'), table_name='expedition_participants')
    op.drop_index(op.f('ix_expedition_participants_user_id'), table_name='expedition_participants')
    op.drop_index(op.f('ix_expedition_participants_id'), table_name='expedition_participants')
    op.drop_table('expedition_participants')
    op.drop_index(op.f('ix_tasks_theme'), table_name='tasks')
    op.drop_column('tasks', 'theme')
    op.drop_column('expeditions', 'tile_slug')
    op.drop_column('expeditions', 'theme')
