import json
from types import SimpleNamespace

from app.services.campaign_prompt import build_campaign_user_prompt


def test_followup_prompt_includes_previous_email_context():
    campaign = SimpleNamespace(topic="Invite to a product demo", offer="No discount")
    step = SimpleNamespace(instructions="Follow up briefly", step_order=2)
    contact = SimpleNamespace(
        first_name="Amina",
        last_name="Khan",
        email="amina@example.com",
        company="Example Co",
        job_title="VP Marketing",
    )

    prompt = build_campaign_user_prompt(
        campaign,
        step,
        contact,
        {"subject": "Demo invitation", "body": "Would a short demo be useful?"},
    )
    payload = json.loads(prompt.split("\n", 1)[1])

    assert payload["step_instructions"] == "Follow up briefly"
    assert payload["previous_email"] == {
        "subject": "Demo invitation",
        "body": "Would a short demo be useful?",
    }

