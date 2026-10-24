import pytest
from health_insurance_claims.models import User
from health_insurance_claims.extensions import db

def test_valid_login(client, seeded_db):
    resp = client.post("/login", data={
        "username": "aasha",
        "password": "Password123!"
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Welcome back, Aasha Rao!" in resp.data

def test_invalid_login(client, seeded_db):
    resp = client.post("/login", data={
        "username": "aasha",
        "password": "WrongPassword!"
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Invalid username or password" in resp.data

def test_logout(client, seeded_db):
    client.post("/login", data={"username": "aasha", "password": "Password123!"})
    resp = client.get("/logout", follow_redirects=True)
    assert resp.status_code == 200
    assert b"You have been securely logged out" in resp.data

def test_unauthenticated_access_redirects(client, seeded_db):
    resp = client.get("/dashboard")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]

def test_password_hash_security(app, seeded_db):
    with app.app_context():
        user = User.query.filter_by(username="aasha").first()
        assert user.password_hash != "Password123!"
        assert user.password_hash.startswith("scrypt:") or user.password_hash.startswith("pbkdf2:")
        assert user.check_password("Password123!") is True
        assert user.check_password("wrong") is False
