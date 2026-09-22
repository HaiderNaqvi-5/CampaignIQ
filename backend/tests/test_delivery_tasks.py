from types import SimpleNamespace
from uuid import uuid4

import pytest


class FakeSession:
    def __init__(self, recipient, campaign, contact, step):
        self.objects = {
            recipient.id: recipient,
            campaign.id: campaign,
            contact.id: contact,
            step.id: step,
        }

    def get(self, model, object_id):
        return self.objects.get(object_id)

    def commit(self):
        return None

    def close(self):
        return None


def _delivery_objects():
    contact = SimpleNamespace(id=uuid4(), email="person@example.com")
    campaign = SimpleNamespace(id=uuid4())
    step = SimpleNamespace(id=uuid4(), step_order=1)
    recipient = SimpleNamespace(
        id=uuid4(),
        campaign_id=campaign.id,
        contact_id=contact.id,
        step_id=step.id,
        status="GENERATED",
        subject="A subject",
        body="A body",
        sent_at=None,
        error=None,
    )
    return recipient, campaign, contact, step


@pytest.mark.parametrize("should_fail", [False, True])
def test_initial_delivery_isolated_per_recipient(monkeypatch, should_fail):
    from app.jobs import tasks
    from app.services import email_provider

    recipient, campaign, contact, step = _delivery_objects()
    session = FakeSession(recipient, campaign, contact, step)
    monkeypatch.setattr(tasks, "_get_sync_session", lambda: session)
    monkeypatch.setattr(tasks, "_schedule_next_step", lambda *_args: None)
    monkeypatch.setattr(tasks, "_derive_campaign_send_status", lambda *_args: None)

    class Provider:
        def send(self, *_args):
            if should_fail:
                raise RuntimeError("mailbox rejected message")

    monkeypatch.setattr(email_provider, "get_email_provider", lambda: Provider())
    result = tasks.send_recipient_task.run(str(recipient.id))

    assert result["status"] == ("FAILED" if should_fail else "SENT")
    assert recipient.status == ("FAILED" if should_fail else "SENT")
    if should_fail:
        assert "mailbox rejected" in recipient.error
    else:
        assert recipient.sent_at is not None
        assert recipient.error is None

