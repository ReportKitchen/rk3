"""workspace settings jsonb

Revision ID: 538facdc04f9
Revises: 838f456c99d5
Create Date: 2026-07-20 09:08:23.075331

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '538facdc04f9'
down_revision: Union[str, Sequence[str], None] = '838f456c99d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("workspaces", sa.Column(
        "settings", postgresql.JSONB(), nullable=False, server_default="{}"))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("workspaces", "settings")
