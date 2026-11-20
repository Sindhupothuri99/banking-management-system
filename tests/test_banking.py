import os
import sys
from pathlib import Path

# Add project root to Python import path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# Use a separate in-memory database for testing.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret-key"

from app import create_app
from app.models import db, User, Account, Transaction
from decimal import Decimal

import pytest


@pytest.fixture
def app():
    app = create_app()

    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False
    )

    with app.app_context():
        db.drop_all()
        db.create_all()

        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def create_customer(name, email, password="Password123"):
    user = User(name=name, email=email)
    user.set_password(password)

    account = Account(
        account_number="1234567890" if email == "one@test.com"
        else "9876543210",
        balance=Decimal("1000.00"),
        user=user
    )

    db.session.add(user)
    db.session.commit()

    return user, account


def test_home_page(client):
    response = client.get("/")
    assert response.status_code == 200


def test_customer_registration(client, app):
    response = client.post("/register", data={
        "name": "Test Customer",
        "email": "new@test.com",
        "password": "Password123"
    })

    assert response.status_code == 302

    with app.app_context():
        user = User.query.filter_by(email="new@test.com").first()

        assert user is not None
        assert user.account is not None


def test_customer_login(client, app):
    with app.app_context():
        create_customer("Customer One", "one@test.com")

    response = client.post("/login", data={
        "email": "one@test.com",
        "password": "Password123"
    })

    assert response.status_code == 302
    assert "/dashboard" in response.location


def test_deposit(client, app):
    with app.app_context():
        create_customer("Customer One", "one@test.com")

    client.post("/login", data={
        "email": "one@test.com",
        "password": "Password123"
    })

    client.post("/deposit", data={"amount": "500"})

    with app.app_context():
        account = Account.query.filter_by(
            account_number="1234567890"
        ).first()

        assert account.balance == Decimal("1500.00")


def test_withdrawal(client, app):
    with app.app_context():
        create_customer("Customer One", "one@test.com")

    client.post("/login", data={
        "email": "one@test.com",
        "password": "Password123"
    })

    client.post("/withdraw", data={"amount": "200"})

    with app.app_context():
        account = Account.query.filter_by(
            account_number="1234567890"
        ).first()

        assert account.balance == Decimal("800.00")


def test_fund_transfer(client, app):
    with app.app_context():
        create_customer("Customer One", "one@test.com")
        create_customer("Customer Two", "two@test.com")

    client.post("/login", data={
        "email": "one@test.com",
        "password": "Password123"
    })

    client.post("/transfer", data={
        "account_number": "9876543210",
        "amount": "300"
    })

    with app.app_context():
        sender = Account.query.filter_by(
            account_number="1234567890"
        ).first()

        receiver = Account.query.filter_by(
            account_number="9876543210"
        ).first()

        assert sender.balance == Decimal("700.00")
        assert receiver.balance == Decimal("1300.00")


def test_admin_access(client, app):
    with app.app_context():
        admin = User(
            name="Admin",
            email="admin@test.com",
            role="admin"
        )
        admin.set_password("AdminPassword123")

        db.session.add(admin)
        db.session.commit()

    client.post("/login", data={
        "email": "admin@test.com",
        "password": "AdminPassword123"
    })

    response = client.get("/admin")

    assert response.status_code == 200