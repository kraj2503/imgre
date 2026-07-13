"""Create initial prompt and image schemas

Revision ID: be6f37b5adfc
Revises:
Create Date: 2026-07-13 00:32:03.725433

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'be6f37b5adfc'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create prompts table
    op.create_table(
        'prompts',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('trend_summary', sa.JSON(), nullable=True),
        sa.Column('aesthetic_score', sa.Float(), nullable=True),
        sa.Column('psychology_score', sa.Float(), nullable=True),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )

    # Create images table
    op.create_table(
        'images',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('prompt_id', sa.Integer(), nullable=False),
        sa.Column('file_path', sa.String(length=1024), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('is_best', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['prompt_id'], ['prompts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('images')
    op.drop_table('prompts')
