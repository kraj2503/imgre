# Export models to ensure they are registered on the Base metadata
from app.database import Base
from app.models.prompt import Prompt
from app.models.image import Image

__all__ = ["Base", "Prompt", "Image"]
