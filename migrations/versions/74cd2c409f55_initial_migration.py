
"""Initial migration cleanup

Revision ID: 74cd2c409f55
Revises: 
Create Date: 2026-03-24 11:02:54.109913

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = '74cd2c409f55'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # 取得資料庫連線並檢查現有欄位
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_columns = [c['name'] for c in inspector.get_columns('items')]

    # 1. 補齊 items 表中缺失的欄位
    if 'is_deleted' not in existing_columns:
        op.add_column('items', sa.Column('is_deleted', sa.Integer(), server_default='0', nullable=False))
    
    if 'description' not in existing_columns:
        if 'desc' in existing_columns:
            # 如果舊欄位叫 desc，嘗試更名 (Postgres 支援)
            op.alter_column('items', 'desc', new_column_name='description')
        else:
            op.add_column('items', sa.Column('description', sa.Text(), nullable=True))
            
    if 'sub_category_id' not in existing_columns:
        op.add_column('items', sa.Column('sub_category_id', sa.Integer(), sa.ForeignKey('sub_categories.id', ondelete='SET NULL'), nullable=True))

    if 'completed_date' not in existing_columns:
        op.add_column('items', sa.Column('completed_date', sa.String(), nullable=True))

    # 2. 確保其他表的基本結構
    # 這裡我們不處理索引與約束，因為 create_all 已經處理過了。
    pass

def downgrade():
    # 撤銷操作在此情境下不執行，以確保數據安全
    pass
