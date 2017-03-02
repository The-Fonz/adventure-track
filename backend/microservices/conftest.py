#
# For pytest
#

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest


# Always override this with proper SQLAlchemy Base object
@pytest.fixture
def base(): pass

# Have to use this in a slightly bizarre way, see:
# http://docs.pytest.org/en/latest/fixture.html#override-a-fixture-with-direct-test-parametrization
@pytest.fixture
def testsession(base):
    "Create test db and session"
    engine = create_engine("postgresql://ca-user:adventure01@localhost/catestdb")
    base.metadata.create_all(engine)
    session_cls = sessionmaker(bind=engine)
    session = session_cls()
    yield session
    # Explicitly close db connection to avoid hang
    session.close()
    # Drop after testing finishes
    base.metadata.drop_all(engine)
