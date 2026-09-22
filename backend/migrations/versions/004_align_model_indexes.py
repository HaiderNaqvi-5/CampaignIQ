"""Align database indexes with registered SQLAlchemy metadata."""

from alembic import op


revision = "004_align_model_indexes"
down_revision = "003_remove_legacy_chat_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("idx_users_email", table_name="users")
    op.create_index(
        "ix_campaign_recipients_contact_id",
        "campaign_recipients",
        ["contact_id"],
    )
    op.create_index(
        "ix_campaign_recipients_step_id",
        "campaign_recipients",
        ["step_id"],
    )
    op.create_index("ix_chunks_page_id", "chunks", ["page_id"])
    op.create_index(
        "ix_documents_crawl_job_id",
        "documents",
        ["crawl_job_id"],
    )
    op.create_index("ix_pages_crawl_job_id", "pages", ["crawl_job_id"])


def downgrade() -> None:
    op.drop_index("ix_pages_crawl_job_id", table_name="pages")
    op.drop_index("ix_documents_crawl_job_id", table_name="documents")
    op.drop_index("ix_chunks_page_id", table_name="chunks")
    op.drop_index("ix_campaign_recipients_step_id", table_name="campaign_recipients")
    op.drop_index("ix_campaign_recipients_contact_id", table_name="campaign_recipients")
    op.create_index("idx_users_email", "users", ["email"], unique=True)
