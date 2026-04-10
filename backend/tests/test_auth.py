import pytest

@pytest.mark.asyncio
async def test_register_success(client):
    resp = await client.post("/auth/register", json={"email": "a@test.com", "password": "pass123"})
    assert resp.status_code == 201
    assert resp.json()["email"] == "a@test.com"
    assert resp.json()["role"] == "user"

@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    await client.post("/auth/register", json={"email": "dup@test.com", "password": "pass123"})
    resp = await client.post("/auth/register", json={"email": "dup@test.com", "password": "pass123"})
    assert resp.status_code == 400

@pytest.mark.asyncio
async def test_login_success(client):
    await client.post("/auth/register", json={"email": "b@test.com", "password": "pass123"})
    resp = await client.post("/auth/login", json={"email": "b@test.com", "password": "pass123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()

@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post("/auth/register", json={"email": "c@test.com", "password": "pass123"})
    resp = await client.post("/auth/login", json={"email": "c@test.com", "password": "wrong"})
    assert resp.status_code == 401

@pytest.mark.asyncio
async def test_me_requires_auth(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 403

@pytest.mark.asyncio
async def test_me_returns_user(client):
    await client.post("/auth/register", json={"email": "d@test.com", "password": "pass123"})
    login = await client.post("/auth/login", json={"email": "d@test.com", "password": "pass123"})
    token = login.json()["access_token"]
    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "d@test.com"
