from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Use proper PostgreSQL URL
DATABASE_URL = "postgresql+psycopg2://postgres:mypostgre067@localhost:5432/VirtualMeet"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

Base = declarative_base()
def init_db():
    from app.models.user import User
    from app.models.nutritionist import Nutritionist
    from app.models.appointment import Appointment