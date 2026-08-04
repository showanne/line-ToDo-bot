"""Quote module upgrade

Revision ID: 3c1b3d7f7f21
Revises: 74cd2c409f55
Create Date: 2026-08-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = '3c1b3d7f7f21'
down_revision = '74cd2c409f55'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)

    quote_columns = [c['name'] for c in inspector.get_columns('quotes')]
    if 'source' not in quote_columns:
        op.add_column('quotes', sa.Column('source', sa.String(), nullable=True))
    if 'speaker' not in quote_columns:
        op.add_column('quotes', sa.Column('speaker', sa.String(), nullable=True))

    quote_tag_tables = inspector.get_table_names()
    if 'quote_tags' not in quote_tag_tables:
        op.create_table(
            'quote_tags',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('user_id', sa.String(), nullable=False),
            sa.Column('name', sa.String(), nullable=False),
        )
    if 'quote_tag_map' not in quote_tag_tables:
        op.create_table(
            'quote_tag_map',
            sa.Column('quote_id', sa.Integer(), sa.ForeignKey('quotes.id', ondelete='CASCADE'), primary_key=True),
            sa.Column('tag_id', sa.Integer(), sa.ForeignKey('quote_tags.id', ondelete='CASCADE'), primary_key=True),
        )


def downgrade():
    pass
