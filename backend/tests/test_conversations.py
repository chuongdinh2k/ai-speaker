import pytest
from uuid import uuid4
from app.models.user import User
from app.models.topic import Topic
from app.auth.service import pwd_context, create_access_token

async def seed_user_and_topic(db_session):
    user = User(email=f"u{uuid4()}@test.com", password_hash=pwd_context.hash("pass"), role="user")
    topic = Topic(name=f"Topic {uuid4()}", system_prompt="Be helpful.")
    db_session.add(user)
    db_session.add(topic)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(topic)
    return user, topic, create_access_token(user)

@pytest.mark.asyncio
async def test_create_conversation(client, db_session):
    user, topic, token = await seed_user_and_topic(db_session)
    resp = await client.post("/conversations", json={"topic_id": str(topic.id)},
                             headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 201
    assert resp.json()["topic_id"] == str(topic.id)

@pytest.mark.asyncio
async def test_upsert_returns_same_conversation(client, db_session):
    user, topic, token = await seed_user_and_topic(db_session)
    r1 = await client.post("/conversations", json={"topic_id": str(topic.id)},
                           headers={"Authorization": f"Bearer {token}"})
    r2 = await client.post("/conversations", json={"topic_id": str(topic.id)},
                           headers={"Authorization": f"Bearer {token}"})
    assert r1.json()["id"] == r2.json()["id"]

@pytest.mark.asyncio
async def test_list_conversations(client, db_session):
    user, topic, token = await seed_user_and_topic(db_session)
    await client.post("/conversations", json={"topic_id": str(topic.id)},
                      headers={"Authorization": f"Bearer {token}"})
    resp = await client.get("/conversations", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

@pytest.mark.asyncio
async def test_delete_conversation(client, db_session):
    user, topic, token = await seed_user_and_topic(db_session)
    create = await client.post("/conversations", json={"topic_id": str(topic.id)},
                               headers={"Authorization": f"Bearer {token}"})
    cid = create.json()["id"]
    del_resp = await client.delete(f"/conversations/{cid}", headers={"Authorization": f"Bearer {token}"})
    assert del_resp.status_code == 204
    list_resp = await client.get("/conversations", headers={"Authorization": f"Bearer {token}"})
    assert not any(c["id"] == cid for c in list_resp.json())

@pytest.mark.asyncio
async def test_list_conversations_includes_message_count(client, db_session):
    from app.models.conversation import Conversation
    from app.models.message import Message

    user, topic, token = await seed_user_and_topic(db_session)
    # Create conversation via API
    r = await client.post("/conversations", json={"topic_id": str(topic.id)},
                          headers={"Authorization": f"Bearer {token}"})
    conv_id = r.json()["id"]

    # Seed 3 messages directly
    for i in range(3):
        db_session.add(Message(
            conversation_id=conv_id,
            role="user" if i % 2 == 0 else "assistant",
            content=f"msg {i}",
        ))
    await db_session.commit()

    resp = await client.get("/conversations", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    convs = resp.json()
    match = next(c for c in convs if c["id"] == conv_id)
    assert match["message_count"] == 3


@pytest.mark.asyncio
async def test_update_conversation_context(client, db_session):
    user, topic, token = await seed_user_and_topic(db_session)
    r = await client.post("/conversations", json={"topic_id": str(topic.id)},
                          headers={"Authorization": f"Bearer {token}"})
    conv_id = r.json()["id"]

    payload = {
        "name": "Alex",
        "occupation": "Software engineer",
        "learning_goal": "Job interviews",
        "preferred_tone": "casual",
    }
    resp = await client.patch(
        f"/conversations/{conv_id}/context",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_context"]["name"] == "Alex"
    assert data["user_context"]["preferred_tone"] == "casual"
    assert "Alex" in data["conversation_prompt"]
    assert "Be helpful." in data["conversation_prompt"]


@pytest.mark.asyncio
async def test_update_context_returns_404_for_wrong_user(client, db_session):
    user, topic, token = await seed_user_and_topic(db_session)
    _, _, other_token = await seed_user_and_topic(db_session)
    r = await client.post("/conversations", json={"topic_id": str(topic.id)},
                          headers={"Authorization": f"Bearer {token}"})
    conv_id = r.json()["id"]

    resp = await client.patch(
        f"/conversations/{conv_id}/context",
        json={"name": "Eve", "occupation": "Hacker", "learning_goal": "Intrusion", "preferred_tone": "formal"},
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert resp.status_code == 404
