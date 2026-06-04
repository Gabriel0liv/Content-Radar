# Import all models so Base has them registered before env.py imports Base
from src.db.session import Base
from src.models.content_item import ContentItem, ContentItemEvent  # noqa
