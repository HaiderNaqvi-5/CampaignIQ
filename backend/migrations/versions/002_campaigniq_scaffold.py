"""CampaignIQ authentication, CRM cache, and campaign schema."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002_campaigniq_scaffold"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def _uuid():
    return postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.alter_column("users", "password_hash", nullable=True)
    op.add_column("users", sa.Column("google_sub", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.create_index("ix_users_google_sub", "users", ["google_sub"], unique=True)
    op.add_column("brand_settings", sa.Column("writing_style", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")))

    op.create_table("otp_verifications",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("user_id", _uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_otp_verifications_user_id", "otp_verifications", ["user_id"])
    op.create_table("hubspot_connections",
        sa.Column("id", _uuid(), primary_key=True), sa.Column("user_id", _uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("portal_id", sa.String(100), nullable=False), sa.Column("access_token_encrypted", sa.String(2048), nullable=False), sa.Column("refresh_token_encrypted", sa.String(2048), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_table("contacts",
        sa.Column("id", _uuid(), primary_key=True), sa.Column("user_id", _uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("hubspot_id", sa.String(100), nullable=False), sa.Column("email", sa.String(320)), sa.Column("first_name", sa.String(255)), sa.Column("last_name", sa.String(255)), sa.Column("company", sa.String(255)), sa.Column("job_title", sa.String(255)), sa.Column("object_type", sa.String(50), nullable=False, server_default="contact"), sa.Column("raw_properties", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")), sa.Column("last_synced_at", sa.DateTime(timezone=True)))
    op.create_index("ix_contacts_user_id", "contacts", ["user_id"])
    op.create_table("hubspot_lists",
        sa.Column("id", _uuid(), primary_key=True), sa.Column("user_id", _uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("hubspot_id", sa.String(100), nullable=False), sa.Column("name", sa.String(255), nullable=False), sa.Column("last_synced_at", sa.DateTime(timezone=True)))
    op.create_index("ix_hubspot_lists_user_id", "hubspot_lists", ["user_id"])
    op.create_table("campaigns",
        sa.Column("id", _uuid(), primary_key=True), sa.Column("user_id", _uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("bot_id", _uuid(), sa.ForeignKey("bots.id", ondelete="RESTRICT"), nullable=False), sa.Column("name", sa.String(255), nullable=False), sa.Column("topic", sa.Text(), nullable=False), sa.Column("offer", sa.Text()), sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_campaigns_user_id", "campaigns", ["user_id"])
    op.create_index("ix_campaigns_bot_id", "campaigns", ["bot_id"])
    op.create_table("campaign_steps",
        sa.Column("id", _uuid(), primary_key=True), sa.Column("campaign_id", _uuid(), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False), sa.Column("step_order", sa.Integer(), nullable=False), sa.Column("delay_days", sa.Integer(), nullable=False, server_default="0"), sa.Column("instructions", sa.Text(), nullable=False), sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"))
    op.create_index("ix_campaign_steps_campaign_id", "campaign_steps", ["campaign_id"])
    op.create_table("campaign_recipients",
        sa.Column("id", _uuid(), primary_key=True), sa.Column("campaign_id", _uuid(), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False), sa.Column("contact_id", _uuid(), sa.ForeignKey("contacts.id", ondelete="RESTRICT"), nullable=False), sa.Column("step_id", _uuid(), sa.ForeignKey("campaign_steps.id", ondelete="CASCADE"), nullable=False), sa.Column("subject", sa.Text()), sa.Column("body", sa.Text()), sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"), sa.Column("sent_at", sa.DateTime(timezone=True)), sa.Column("error", sa.Text()))
    op.create_index("ix_campaign_recipients_campaign_id", "campaign_recipients", ["campaign_id"])


def downgrade() -> None:
    op.drop_table("campaign_recipients")
    op.drop_table("campaign_steps")
    op.drop_table("campaigns")
    op.drop_table("hubspot_lists")
    op.drop_table("contacts")
    op.drop_table("hubspot_connections")
    op.drop_table("otp_verifications")
    op.drop_column("brand_settings", "writing_style")
    op.drop_index("ix_users_google_sub", table_name="users")
    op.drop_column("users", "is_verified")
    op.drop_column("users", "google_sub")
    op.alter_column("users", "password_hash", nullable=False)
