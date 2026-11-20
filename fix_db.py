from app import create_app
from sqlalchemy import inspect, text

app = create_app()

with app.app_context():
    engine = app.extensions["sqlalchemy"].engine

    inspector = inspect(engine)
    columns = [
        column["name"]
        for column in inspector.get_columns("transactions")
    ]

    with engine.begin() as connection:

        if "description" not in columns:
            connection.execute(text(
                "ALTER TABLE transactions ADD COLUMN description VARCHAR(255)"
            ))
            print("Added description column.")

        if "created_at" not in columns:
            connection.execute(text(
                "ALTER TABLE transactions ADD COLUMN created_at DATETIME"
            ))
            connection.execute(text(
                "UPDATE transactions SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"
            ))
            print("Added created_at column.")

    print("Database repair completed successfully.")