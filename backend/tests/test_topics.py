import pytest

async def get_token(client, email, password="pass123", role="user"):
    await client.post("/auth/register", json={"email": email, "password": password})
    resp = await client.post("/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"]

async def get_admin_token(client):
    # Register then manually promote to admin via DB in conftest, or use a helper
    # For tests, we'll seed an admin user directly
    from app.models.user import User
    from app.auth.service import pwd_context
    # This is done via the db_session fixture in conftest
    return None  # see note below

@pytest.mark.asyncio
async def test_list_topics_requires_auth(client):
    resp = await client.get("/topics")
    assert resp.status_code == 403

@pytest.mark.asyncio
async def test_list_topics_empty(client):
    token = await get_token(client, "topicuser@test.com")
    resp = await client.get("/topics", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

@pytest.mark.asyncio
async def test_create_topic_requires_admin(client):
    token = await get_token(client, "notadmin@test.com")
    resp = await client.post("/topics", json={"name": "Python"}, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403

@pytest.mark.asyncio
async def test_create_and_list_topic(client, db_session):
    # Seed admin user directly
    from app.models.user import User
    from app.auth.service import pwd_context, create_access_token
    admin = User(email="admin@test.com", password_hash=pwd_context.hash("pass123"), role="admin")
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    token = create_access_token(admin)

    resp = await client.post("/topics", json={"name": "Python", "description": "Python programming", "system_prompt": "You are a Python expert."},
                             headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 201
    assert resp.json()["name"] == "Python"

    user_token = await get_token(client, "reader@test.com")
    list_resp = await client.get("/topics", headers={"Authorization": f"Bearer {user_token}"})
    assert any(t["name"] == "Python" for t in list_resp.json())
