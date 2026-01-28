from typing import Generic, TypeVar, Type, List, Optional, Any
from sqlalchemy.orm import Session
from database import Base

T = TypeVar('T', bound=Base)

class BaseRepository(Generic[T]):
    def __init__(self, session: Session, model: Type[T]):
        self.session = session
        self.model = model

    def get_by_id(self, id: int) -> Optional[T]:
        return self.session.query(self.model).get(id)

    def get_all(self) -> List[T]:
        return self.session.query(self.model).all()

    def add(self, entity: T) -> T:
        self.session.add(entity)
        self.session.flush() # Flush to get ID if needed, commit should be handled by UnitOfWork or Service
        return entity

    def update(self, entity: T) -> T:
        # SQLAlchemy objects attached to session track changes automatically.
        # This explicit method can be used if detached.
        return self.session.merge(entity)

    def delete(self, id: int) -> bool:
        entity = self.get_by_id(id)
        if entity:
            self.session.delete(entity)
            return True
        return False
        
    def count(self) -> int:
        return self.session.query(self.model).count()


