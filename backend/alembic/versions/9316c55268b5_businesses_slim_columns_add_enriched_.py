"""businesses — slim columns, add enriched, metadata, social urls

Revision ID: 9316c55268b5
Revises: 981fe20a943f
Create Date: 2026-04-04 18:25:42.097023

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9316c55268b5'
down_revision: Union[str, Sequence[str], None] = '981fe20a943f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Step 1: Add new columns
    op.add_column('businesses', sa.Column('categories', sa.String(), nullable=True))
    op.add_column('businesses', sa.Column('instagram_url', sa.String(), nullable=True))
    op.add_column('businesses', sa.Column('tiktok_url', sa.String(), nullable=True))
    op.add_column('businesses', sa.Column('enriched', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('businesses', sa.Column('enriched_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('businesses', sa.Column('metadata', sa.JSON(), nullable=True))

    # Step 2: Migrate data — copy category → categories, build metadata JSON from columns being dropped
    op.execute("""
        UPDATE businesses SET
            categories = category,
            metadata = json_build_object(
                'phone', phone,
                'hours', hours,
                'description', description,
                'thumbnail', thumbnail,
                'subcategory', subcategory,
                'city', city,
                'price_level', price_level
            )
        WHERE category IS NOT NULL
           OR phone IS NOT NULL
           OR hours IS NOT NULL
           OR description IS NOT NULL
           OR thumbnail IS NOT NULL
    """)

    # Step 3: Create new index, drop old
    op.drop_index(op.f('ix_businesses_category'), table_name='businesses')
    op.create_index(op.f('ix_businesses_categories'), 'businesses', ['categories'], unique=False)

    # Step 4: Drop old columns
    op.drop_column('businesses', 'maps_url')
    op.drop_column('businesses', 'city')
    op.drop_column('businesses', 'instagram_handle')
    op.drop_column('businesses', 'category')
    op.drop_column('businesses', 'hours')
    op.drop_column('businesses', 'description')
    op.drop_column('businesses', 'price_level')
    op.drop_column('businesses', 'subcategory')
    op.drop_column('businesses', 'phone')
    op.drop_column('businesses', 'thumbnail')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('businesses', sa.Column('thumbnail', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('businesses', sa.Column('phone', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('businesses', sa.Column('subcategory', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('businesses', sa.Column('price_level', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('businesses', sa.Column('description', sa.TEXT(), autoincrement=False, nullable=True))
    op.add_column('businesses', sa.Column('hours', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('businesses', sa.Column('category', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('businesses', sa.Column('instagram_handle', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('businesses', sa.Column('city', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('businesses', sa.Column('maps_url', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.drop_index(op.f('ix_businesses_categories'), table_name='businesses')
    op.create_index(op.f('ix_businesses_category'), 'businesses', ['category'], unique=False)
    op.drop_column('businesses', 'metadata')
    op.drop_column('businesses', 'enriched_at')
    op.drop_column('businesses', 'enriched')
    op.drop_column('businesses', 'tiktok_url')
    op.drop_column('businesses', 'instagram_url')
    op.drop_column('businesses', 'categories')
