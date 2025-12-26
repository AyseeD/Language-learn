from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import DeclarativeBase, relationship, Session
from datetime import datetime
from flask_login import UserMixin

from werkzeug.security import generate_password_hash, check_password_hash

class Base(DeclarativeBase):
    pass


class Role(Base):
    __tablename__ = 'roles'

    code = Column(String(10), primary_key=True)
    name = Column(String(255), unique=True, nullable=False)

    # Relationships
    users = relationship("User", back_populates="role")

    def __repr__(self):
        return '<Role %r>' % self.code


class User(UserMixin, Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    username = Column(String(20), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    # Foreign key to Role
    role_code = Column(String(10), ForeignKey("roles.code", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    role = relationship("Role", back_populates="users")
    transactions = relationship("Transaction", back_populates="user")
    progress = relationship("Progress", back_populates="user")

    def __repr__(self):
        return '<User %r>' % self.username


class Course(Base):
    __tablename__ = 'courses'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False, index=True)

    # Relationships
    transactions = relationship("Transaction", back_populates="course")
    characters = relationship("Character", back_populates="course")

    def __repr__(self):
        return '<Course %r>' % self.name


class Character(Base):
    __tablename__ = 'characters'

    id = Column(Integer, primary_key=True, autoincrement=True)
    kana = Column(String(255), unique=True, nullable=False)
    romaji = Column(String(255), unique=False, nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)

    # Relationships
    course = relationship("Course", back_populates="characters")

    def __repr__(self):
        return '<Character %r>' % self.romaji


class Pricing(Base):
    __tablename__ = 'pricings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    price = Column(Integer, nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)

    def __repr__(self):
        return '<Pricing %r>' % self.id


class Transaction(Base):
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    card_number = Column(String(255), nullable=False)
    price = Column(Integer, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="transactions")
    course = relationship("Course", back_populates="transactions")

    def __repr__(self):
        return '<Transaction %r>' % self.id

class Enrollment(Base):
    __tablename__ = 'enrollments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False)

    def __repr__(self):
        return '<Enrollment %r>' % self.id

class Progress(Base):
    __tablename__ = 'user_progress'

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True, nullable=False)
    character_id = Column(Integer, ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True, nullable=False)
    learned = Column(Boolean, default=False, nullable=False)
    answered = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="progress")
    course = relationship("Course")
    character = relationship("Character")
