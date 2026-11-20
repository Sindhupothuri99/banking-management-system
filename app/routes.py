from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from decimal import Decimal, InvalidOperation
from secrets import randbelow

from app.models import db, User, Account, Transaction

main = Blueprint("main", __name__)


# Home Page
@main.route("/")
def index():
    return render_template("index.html")


# Customer Registration
@main.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or len(password) < 8:
            flash("Enter valid details. Password must have at least 8 characters.")
            return redirect(url_for("main.register"))

        if User.query.filter_by(email=email).first():
            flash("Email already registered.")
            return redirect(url_for("main.register"))

        try:
            user = User(name=name, email=email)
            user.set_password(password)

            account = Account(
                account_number=str(randbelow(9000000000) + 1000000000),
                balance=Decimal("0.00"),
                user=user
            )

            db.session.add(user)
            db.session.add(account)
            db.session.commit()

            flash("Registration successful. Please log in.")
            return redirect(url_for("main.login"))

        except Exception:
            db.session.rollback()
            flash("Registration failed. Please try again.")

    return render_template("register.html")


# Login - Admin and Customer
@main.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)

            # Redirect according to user role
            if user.role == "admin":
                return redirect(url_for("main.admin_dashboard"))

            return redirect(url_for("main.dashboard"))

        flash("Invalid email or password.")

    return render_template("login.html")


# Customer Dashboard
@main.route("/dashboard")
@login_required
def dashboard():
    if current_user.role == "admin":
        return redirect(url_for("main.admin_dashboard"))

    account = current_user.account

    if not account:
        flash("Bank account not found.")
        return redirect(url_for("main.index"))

    return render_template("dashboard.html", account=account)


# Deposit Money
@main.route("/deposit", methods=["POST"])
@login_required
def deposit():
    if current_user.role == "admin":
        flash("Admins cannot perform customer transactions.")
        return redirect(url_for("main.admin_dashboard"))

    try:
        amount = Decimal(request.form.get("amount", "0"))

        if not amount.is_finite() or amount <= 0 or amount > Decimal("1000000"):
            raise ValueError()

        account = current_user.account

        if not account:
            flash("Bank account not found.")
            return redirect(url_for("main.index"))

        account.balance += amount

        transaction = Transaction(
            account_id=account.id,
            transaction_type="DEPOSIT",
            amount=amount,
            description="Money deposited"
        )

        db.session.add(transaction)
        db.session.commit()

        flash("Deposit successful.")

    except (InvalidOperation, ValueError, TypeError):
        db.session.rollback()
        flash("Enter a valid deposit amount.")

    except Exception:
        db.session.rollback()
        flash("Deposit failed.")

    return redirect(url_for("main.dashboard"))


# Withdraw Money
@main.route("/withdraw", methods=["POST"])
@login_required
def withdraw():
    if current_user.role == "admin":
        flash("Admins cannot perform customer transactions.")
        return redirect(url_for("main.admin_dashboard"))

    try:
        amount = Decimal(request.form.get("amount", "0"))
        account = current_user.account

        if not account:
            flash("Bank account not found.")
            return redirect(url_for("main.index"))

        if not amount.is_finite() or amount <= 0:
            raise ValueError()

        if amount > account.balance:
            flash("Insufficient balance.")
            return redirect(url_for("main.dashboard"))

        account.balance -= amount

        transaction = Transaction(
            account_id=account.id,
            transaction_type="WITHDRAWAL",
            amount=amount,
            description="Money withdrawn"
        )

        db.session.add(transaction)
        db.session.commit()

        flash("Withdrawal successful.")

    except (InvalidOperation, ValueError, TypeError):
        db.session.rollback()
        flash("Enter a valid withdrawal amount.")

    except Exception:
        db.session.rollback()
        flash("Withdrawal failed.")

    return redirect(url_for("main.dashboard"))


# Fund Transfer
@main.route("/transfer", methods=["POST"])
@login_required
def transfer():
    if current_user.role == "admin":
        flash("Admins cannot perform customer transactions.")
        return redirect(url_for("main.admin_dashboard"))

    try:
        amount = Decimal(request.form.get("amount", "0"))
        receiver_number = request.form.get("account_number", "").strip()

        sender = current_user.account

        if not sender:
            flash("Bank account not found.")
            return redirect(url_for("main.index"))

        receiver = Account.query.filter_by(
            account_number=receiver_number
        ).first()

        if not amount.is_finite() or amount <= 0:
            raise ValueError()

        if not receiver or receiver.id == sender.id:
            flash("Invalid receiver account.")
            return redirect(url_for("main.dashboard"))

        if amount > sender.balance:
            flash("Insufficient balance.")
            return redirect(url_for("main.dashboard"))

        sender.balance -= amount
        receiver.balance += amount

        db.session.add(Transaction(
            account_id=sender.id,
            transaction_type="TRANSFER",
            amount=amount,
            description=f"Transfer to {receiver_number}"
        ))

        db.session.add(Transaction(
            account_id=receiver.id,
            transaction_type="RECEIVED",
            amount=amount,
            description=f"Received from {sender.account_number}"
        ))

        db.session.commit()

        flash("Transfer successful.")

    except (InvalidOperation, ValueError, TypeError):
        db.session.rollback()
        flash("Enter a valid transfer amount.")

    except Exception:
        db.session.rollback()
        flash("Transfer failed.")

    return redirect(url_for("main.dashboard"))


# Transaction History
@main.route("/transactions")
@login_required
def transactions():
    if current_user.role == "admin":
        return redirect(url_for("main.admin_dashboard"))

    account = current_user.account

    if not account:
        flash("Bank account not found.")
        return redirect(url_for("main.index"))

    records = Transaction.query.filter_by(
        account_id=account.id
    ).order_by(Transaction.created_at.desc()).all()

    return render_template("transactions.html", records=records)


# Logout
@main.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have logged out.")
    return redirect(url_for("main.login"))


# Admin Dashboard
@main.route("/admin")
@login_required
def admin_dashboard():

    if current_user.role != "admin":
        flash("Access denied. Admin only.")
        return redirect(url_for("main.dashboard"))

    total_users = User.query.count()
    total_accounts = Account.query.count()
    total_transactions = Transaction.query.count()

    users = User.query.order_by(User.id.desc()).all()

    accounts = Account.query.order_by(Account.id.desc()).all()

    transactions = Transaction.query.order_by(
        Transaction.created_at.desc()
    ).limit(10).all()

    return render_template(
        "admin.html",
        total_users=total_users,
        total_accounts=total_accounts,
        total_transactions=total_transactions,
        users=users,
        accounts=accounts,
        transactions=transactions
    )
# Admin - View Individual Customer Information
@main.route("/admin/customer/<int:user_id>")
@login_required
def admin_customer_detail(user_id):

    if current_user.role != "admin":
        flash("Access denied. Admin only.")
        return redirect(url_for("main.dashboard"))

    customer = db.session.get(User, user_id)

    if not customer:
        flash("Customer not found.")
        return redirect(url_for("main.admin_dashboard"))

    account = customer.account

    records = []

    if account:
        records = Transaction.query.filter_by(
            account_id=account.id
        ).order_by(Transaction.created_at.desc()).all()

    return render_template(
        "customer_detail.html",
        customer=customer,
        account=account,
        records=records
    )