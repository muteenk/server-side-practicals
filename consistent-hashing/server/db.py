from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import String, Uuid, create_engine
from sqlalchemy.orm import Mapped, mapped_column, sessionmaker, DeclarativeBase
from uuid import uuid4

SQLALCHEMY_DATABASE_URL = "sqlite:///./database.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass

class UserProfile(Base):
    __tablename__ = "user_profiles"

    uuid: Mapped[uuid.UUID] = mapped_column(
        Uuid, 
        primary_key=True, 
        default=uuid4
    )
    username: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(100))


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

