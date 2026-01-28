
from sqlalchemy import Column, Integer, String, LargeBinary, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .entities import Base

class Documento(Base):
    __tablename__ = 'documentos'

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    file_data = Column(LargeBinary, nullable=False) # Stores the actual bytes
    upload_date = Column(DateTime, default=datetime.now)
    mime_type = Column(String(100), nullable=True) # e.g., 'application/pdf', 'image/jpeg'
    file_size = Column(Integer, nullable=True) # Size in bytes

    # Relationship back to Vencimiento/Pago will be defined in those models or here if needed.
    # But usually, Vencimiento has foreign key 'documento_id'.
    
    def __repr__(self):
        return f"<Documento(id={self.id}, name={self.filename}, size={self.file_size})>"
