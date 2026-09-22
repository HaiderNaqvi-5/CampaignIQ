import pytest
from app.schemas.campaign import RecipientSelection
from app.services.recipient_resolver import _EMAIL_RE


def test_recipient_selection_requires_exactly_one_mode():
    assert RecipientSelection(all=True).all is True
    assert RecipientSelection(contact_ids=["00000000-0000-0000-0000-000000000001"]).contact_ids
    with pytest.raises(ValueError):
        RecipientSelection()
    with pytest.raises(ValueError):
        RecipientSelection(all=True, list_ids=["00000000-0000-0000-0000-000000000001"])


def test_email_eligibility_requires_a_valid_address():
    assert _EMAIL_RE.match("person@example.com")
    assert not _EMAIL_RE.match("")
    assert not _EMAIL_RE.match("missing-at-domain")
