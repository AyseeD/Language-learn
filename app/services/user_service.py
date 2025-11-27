from werkzeug.security import generate_password_hash, check_password_hash
from sqlmodel import Session, select
from app.database.models import User
from app.database.schemas import UserCreate, UserUpdate
from typing import Optional


class UserService:

    @staticmethod
    def create_user(session: Session, user_data: UserCreate) -> User:
        hashed_password = generate_password_hash(user_data.password)

        # SQLModel works just like Pydantic + SQLAlchemy combined!
        user = User(
            name=user_data.name,
            username=user_data.username,
            password_hash=hashed_password,
            role_code=user_data.role_code
        )

        session.add(user)
        session.commit()
        session.refresh(user)

        return user

    @staticmethod
    def get_user_by_id(session: Session, user_id: int) -> Optional[User]:
        return session.get(User, user_id)

    @staticmethod
    def get_user_by_username(session: Session, username: str) -> Optional[User]:
        statement = select(User).where(User.username == username)
        return session.exec(statement).first()

    @staticmethod
    def verify_password(user: User, password: str) -> bool:
        return check_password_hash(user.password_hash, password)

    @staticmethod
    def update_user(session: Session, user: User, user_data: UserUpdate) -> User:
        update_data = user_data.model_dump(exclude_unset=True)

        if 'password' in update_data:
            update_data['password_hash'] = generate_password_hash(update_data.pop('password'))

        for key, value in update_data.items():
            setattr(user, key, value)

        user.updated_at = datetime.utcnow()
        session.add(user)
        session.commit()
        session.refresh(user)

        return user
