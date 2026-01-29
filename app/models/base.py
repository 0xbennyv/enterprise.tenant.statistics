# app/models/__init__.py

from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

# Import your models here to ensure they are registered with Base
