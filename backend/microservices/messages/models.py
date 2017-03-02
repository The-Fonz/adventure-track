from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB

Base = declarative_base()


class Message(Base):
    "Message from athlete, can contain media"
    __tablename__ = 'message'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime)
    user_id = Column(Integer)
    # Can omit title or body text
    title = Column(Text, nullable=True)
    text = Column(Text, nullable=True)
    # Store original, max. path size is 255 on most systems
    image_original = Column(String(255), nullable=True)
    # Store many different versions of media like
    # {"lowres": "/some-path", "highres": "/some-path"}
    image_versions = Column(JSONB, nullable=True)
    video_original = Column(String(255), nullable=True)
    # Postgres' JSONB is queryable
    video_versions = Column(JSONB, nullable=True)
    audio_original = Column(String(255), nullable=True)
    audio_versions = Column(JSONB, nullable=True)


class ChatMessage(Base):
    "Simple text message for live chat"
    __tablename__ = 'chat_message'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime)
    text = Column(Text)
    # Identify sender using various attributes
    # e.g. typed name, uuid, or other things
    sender = Column(JSONB)
