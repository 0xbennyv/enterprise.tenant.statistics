"""update export jobs table

Revision ID: 5a958d8b6b7f
Revises: 061e0df57f94
Create Date: 2026-01-29 23:30:08.244311

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5a958d8b6b7f'
down_revision: Union[str, Sequence[str], None] = '061e0df57f94'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Convert 'id' to integer if it's currently VARCHAR
    op.alter_column(
        'export_jobs',
        'id',
        existing_type=sa.VARCHAR(),
        type_=sa.Integer(),
        postgresql_using="id::integer",
        existing_nullable=False
    )

    # Create a new sequence for auto-increment
    op.execute("CREATE SEQUENCE export_jobs_id_seq OWNED BY export_jobs.id")

    # Set default value for 'id' to use the sequence
    op.execute("ALTER TABLE export_jobs ALTER COLUMN id SET DEFAULT nextval('export_jobs_id_seq')")

    # Make sure the sequence starts after the max existing id
    op.execute("""
        SELECT setval(
            'export_jobs_id_seq', 
            COALESCE((SELECT MAX(id) FROM export_jobs), 0) + 1, 
            false
        )
    """)

    # 5️⃣ Add unique constraint on job_id
    op.add_column('export_jobs', sa.Column('job_id', sa.String(), nullable=False))
    op.create_unique_constraint('uq_export_jobs_job_id', 'export_jobs', ['job_id'])


def downgrade() -> None:
    # Remove unique constraint
    op.drop_constraint('uq_export_jobs_job_id', 'export_jobs', type_='unique')

    # Drop job_id column
    op.drop_column('export_jobs', 'job_id')

    # Remove default sequence on id
    op.execute("ALTER TABLE export_jobs ALTER COLUMN id DROP DEFAULT")
    op.execute("DROP SEQUENCE IF EXISTS export_jobs_id_seq")

    # Optional: convert id back to VARCHAR
    op.alter_column(
        'export_jobs',
        'id',
        existing_type=sa.Integer(),
        type_=sa.VARCHAR(),
        postgresql_using="id::varchar",
        existing_nullable=False
    )