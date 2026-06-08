"""seed default styles

Revision ID: 003_seed_default_styles
Revises: 002
Create Date: 2026-06-08
"""

from alembic import op


revision = "003_seed_default_styles"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO styles (id, name, description, fingerprint, sample_count, total_generated)
        VALUES
          ('default', '默认通用风格', '通用公众号写作风格，可作为未配置风格时的稳定默认值', '{}'::jsonb, 0, 0),
          ('caoz', 'caoz 的梦呓', '短句、直给、带观点密度的科技商业评论风格', '{}'::jsonb, 0, 0),
          ('bdj', '半佛仙人', '反讽密集、故事化拆解、强节奏表达', '{}'::jsonb, 0, 0),
          ('hesheng', '何加盐', '长文叙事、结构化分析、观点层层推进', '{}'::jsonb, 0, 0)
        ON CONFLICT (id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM styles WHERE id IN ('default', 'caoz', 'bdj', 'hesheng')")
