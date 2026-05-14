from sqlalchemy import create_engine, Column, String, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import uuid

# 1. Connect to the database
DATABASE_URL = "sqlite:///crissybot.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# 2. Define the Users table
class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    messages = relationship("Message", back_populates="user")

# 3. Define the Messages table
class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="messages")

# 4. Create the tables if they don't exist
def init_db():
    Base.metadata.create_all(bind=engine)

# 5. Database session helper
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 6. Get or create a user
def get_or_create_user(db, username: str):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        user = User(username=username)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

# 7. Save a message
def save_message(db, user_id: str, role: str, content: str):
    message = Message(user_id=user_id, role=role, content=content)
    db.add(message)
    db.commit()

# 8. Get all messages for a user
def get_user_messages(db, user_id: str):
    messages = db.query(Message)\
        .filter(Message.user_id == user_id)\
        .order_by(Message.created_at)\
        .all()
    return [{"role": m.role, "content": m.content} for m in messages]