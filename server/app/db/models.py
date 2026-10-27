"""Modelos de la base de datos: User, Task, Result, Credit."""
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.db.database import Base

def utcnow():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=utcnow)
    tasks = relationship("Task", back_populates="user")
    credits = relationship("Credit", back_populates="user")

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    payload = Column(Text, nullable=False)
    status = Column(String, default="pending")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    assigned_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    user = relationship("User", back_populates="tasks")
    results = relationship("Result", back_populates="task")
    credits = relationship("Credit", back_populates="task")

class Result(Base):
    __tablename__ = "results"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    output = Column(Text, nullable=False)
    compute_time_sec = Column(Float, nullable=True)
    client = Column(String, nullable=True)        # flutter_mobile | gui | cli
    client_mode = Column(String, nullable=True)   # manual | auto
    created_at = Column(DateTime, default=utcnow)
    task = relationship("Task", back_populates="results")

class Credit(Base):
    __tablename__ = "credits"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    amount = Column(Float, nullable=False, default=1.0)
    granted_at = Column(DateTime, default=utcnow, nullable=False)
    user = relationship("User", back_populates="credits")
    task = relationship("Task", back_populates="credits")

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String, nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String, nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=utcnow)
    revoked_at = Column(DateTime, nullable=True)

    user = relationship("User", backref="refresh_tokens")

# === Nodos Ciudadanos ===

from sqlalchemy import Boolean  # si no está ya importado arriba

class Node(Base):
    __tablename__ = "nodes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(80), nullable=False)
    invite_code = Column(String(12), unique=True, index=True, nullable=False)
    logo_url = Column(String, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=utcnow)
    member_count = Column(Integer, default=1, nullable=False)
    is_public = Column(Boolean, default=True, nullable=False)

    members = relationship("NodeMember", back_populates="node", cascade="all, delete-orphan")
    join_requests = relationship("NodeJoinRequest", back_populates="node", cascade="all, delete-orphan")
    creator = relationship("User", foreign_keys=[created_by])


class NodeMember(Base):
    __tablename__ = "node_members"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False, default="member")  # "admin" | "member"
    joined_at = Column(DateTime, default=utcnow)

    node = relationship("Node", back_populates="members")
    user = relationship("User")


class NodeJoinRequest(Base):
    __tablename__ = "node_join_requests"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="pending")  # pending | accepted | rejected
    created_at = Column(DateTime, default=utcnow)

    node = relationship("Node", back_populates="join_requests")
    user = relationship("User")
