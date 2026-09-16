"""users.phone ixtiyoriy (email-only ro'yxatdan o'tish)

Revision ID: a1b2c3d4e5f6
Revises: c98eac218cec
Create Date: 2026-09-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'c98eac218cec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('users', 'phone', existing_type=sa.String(length=20), nullable=True)
    op.create_check_constraint(
        'ck_users_phone_or_email',
        'users',
        '(phone IS NOT NULL) OR (email IS NOT NULL)',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('ck_users_phone_or_email', 'users', type_='check')
    op.alter_column('users', 'phone', existing_type=sa.String(length=20), nullable=False)
