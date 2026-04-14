import pytest
from cw_trading_system.database import init_db, create_all, drop_all, get_session


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Initialize in-memory test database and create tables."""
    init_db("sqlite:///:memory:")
    create_all()
    yield
    drop_all()


@pytest.fixture(autouse=True)
def db_session():
    """Provide a fresh DB session for each test."""
    session = get_session()
    try:
        yield session
        session.rollback()
    finally:
        session.close()
