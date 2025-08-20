"""merge heads: 9172ff341635 + 70fd5ab9e65b

This is a no-op merge to unify branches.
"""

from alembic import op
import sqlalchemy as sa

# New merge revision id（任意の16桁程度のhexでOK）
revision = "m20250815a001"
# ← 下流に位置する2本のheadを列挙（**タプル**で書く）
down_revision = ("9172ff341635", "70fd5ab9e65b")
branch_labels = None
depends_on = None

def upgrade():
    # no-op
    pass

def downgrade():
    # 単純化のため no-op（必要なら分岐へ戻す処理を書く）
    pass