"""businesses — add slug column

Revision ID: 887ca5894acd
Revises: 9316c55268b5
Create Date: 2026-04-04 21:13:42.384235

"""
import re
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '887ca5894acd'
down_revision: Union[str, Sequence[str], None] = '9316c55268b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def upgrade() -> None:
    # Add column
    op.add_column('businesses', sa.Column('slug', sa.String(), nullable=True))

    # Generate slugs for existing rows
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, business_name FROM businesses ORDER BY review_count DESC"))
    used_slugs: set[str] = set()

    for row in rows:
        base_slug = _slugify(row.business_name)
        if not base_slug:
            base_slug = str(row.id)[:8]

        slug = base_slug
        counter = 2
        while slug in used_slugs:
            slug = f"{base_slug}-{counter}"
            counter += 1

        used_slugs.add(slug)
        conn.execute(
            sa.text("UPDATE businesses SET slug = :slug WHERE id = :id"),
            {"slug": slug, "id": row.id},
        )

    # Create unique index after populating
    op.create_index(op.f('ix_businesses_slug'), 'businesses', ['slug'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_businesses_slug'), table_name='businesses')
    op.drop_column('businesses', 'slug')
