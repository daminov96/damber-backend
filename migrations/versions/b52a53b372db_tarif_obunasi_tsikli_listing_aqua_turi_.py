"""tarif obunasi tsikli, listing Aqua turi va old_price, qidiruv filtrlari

Revision ID: b52a53b372db
Revises: f9c28c405ecf
Create Date: 2026-08-03 13:44:37.199540

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b52a53b372db'
down_revision: Union[str, Sequence[str], None] = 'f9c28c405ecf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('listings', sa.Column('old_price', sa.Numeric(precision=14, scale=2), nullable=True))
    # listing_type enum allaqachon mavjud — CREATE TYPE emas, ADD VALUE
    op.execute("ALTER TYPE listing_type ADD VALUE IF NOT EXISTS 'Aqua'")

    op.add_column('users', sa.Column('plan_until', sa.Date(), nullable=True))
    # plan_billing_cycle enum turi plan_purchases.billing_cycle orqali allaqachon
    # mavjud — create_type=False, aks holda CREATE TYPE ikkinchi marta ishga tushib
    # DuplicateObjectError beradi (bu sessiyada bir necha marta uchragan naqsh).
    op.add_column(
        'users',
        sa.Column(
            'plan_period',
            postgresql.ENUM('monthly', 'yearly', name='plan_billing_cycle', create_type=False),
            nullable=True,
        ),
    )
    op.add_column('users', sa.Column('plan_rate', sa.Numeric(precision=14, scale=2), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'plan_rate')
    op.drop_column('users', 'plan_period')
    op.drop_column('users', 'plan_until')
    op.drop_column('listings', 'old_price')
    # Postgres enum qiymatini DROP qilib bo'lmaydi — 'Aqua' listing_type turida qoladi.
