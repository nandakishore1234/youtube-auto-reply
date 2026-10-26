import os

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.database import Base


def create_test_session():
    database_url = os.environ.get("TEST_DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "TEST_DATABASE_URL must point to the isolated test database."
        )

    url = make_url(database_url)

    if url.database != "youtube_ai_replier_test":
        raise RuntimeError(
            "Refusing to run tests against anything other than "
            "youtube_ai_replier_test."
        )

    engine = create_engine(database_url)

    # Register all ORM models with SQLAlchemy.
    import app.models.user
    import app.models.youtube_channel
    import app.models.comment
    import app.models.reply_draft
    import app.models.oauth_credential

    Base.metadata.create_all(bind=engine)

    TestSession = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    return engine, TestSession
