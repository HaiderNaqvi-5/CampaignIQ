"""Remove legacy chatbot persistence and widget configuration."""

from alembic import op


revision = "003_remove_legacy_chat_schema"
down_revision = "002_campaigniq_scaffold"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # IF EXISTS supports both databases upgraded from EmbedIQ and fresh
    # CampaignIQ databases whose edited baseline never created these objects.
    op.execute("DROP TABLE IF EXISTS messages CASCADE")
    op.execute("DROP TABLE IF EXISTS conversations CASCADE")
    op.execute(
        "ALTER TABLE brand_settings DROP COLUMN IF EXISTS widget_position"
    )


def downgrade() -> None:
    # Removed chatbot product data is intentionally not recreated.
    pass
