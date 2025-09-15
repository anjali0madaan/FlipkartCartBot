# Session management models for Flipkart automation
# Integration reference: blueprint:python_database

from datetime import datetime, timedelta
import os
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class UserSession(Base):
    """Store user session data and browser profiles for automation."""
    __tablename__ = 'user_sessions'
    
    id = Column(Integer, primary_key=True)
    user_identifier = Column(String(100), unique=True, nullable=False)  # email or mobile
    session_name = Column(String(100), nullable=False)
    profile_path = Column(String(500), nullable=False)  # Chrome user data directory path
    cookies_data = Column(Text)  # Serialized cookies as backup
    local_storage_data = Column(Text)  # Serialized local storage
    session_valid = Column(Boolean, default=True)
    last_used = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=30))
    
    def __repr__(self):
        return f'<UserSession {self.user_identifier}>'
    
    def is_valid(self):
        """Check if session is still valid and not expired."""
        return bool(self.session_valid) and self.expires_at > datetime.utcnow()
    
    def update_last_used(self):
        """Update the last used timestamp."""
        self.last_used = datetime.utcnow()

class LoginAttempt(Base):
    """Track login attempts and OTP verification."""
    __tablename__ = 'login_attempts'
    
    id = Column(Integer, primary_key=True)
    user_identifier = Column(String(100), nullable=False)
    attempt_type = Column(String(20), nullable=False)  # 'email' or 'mobile'
    otp_requested = Column(Boolean, default=False)
    otp_verified = Column(Boolean, default=False)
    success = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<LoginAttempt {self.user_identifier} - {self.success}>'

# Database setup
def get_db_session():
    """Create database session using Replit environment variables."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    
    engine = create_engine(database_url, pool_recycle=300, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()

def init_database():
    """Initialize database tables."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    
    engine = create_engine(database_url, pool_recycle=300, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    print("Database tables created successfully")