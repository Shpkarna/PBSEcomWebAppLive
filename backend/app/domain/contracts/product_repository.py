"""Repository contract for product persistence operations."""
from abc import ABC, abstractmethod
from typing import Optional


class ProductRepository(ABC):
    """Storage-agnostic product repository contract."""

    @abstractmethod
    def exists_by_sku(self, sku: str) -> bool:
        """Return True if a product with SKU exists."""

    @abstractmethod
    def create(self, product_doc: dict) -> dict:
        """Persist a new product document and return stored document."""

    @abstractmethod
    def list_products(
        self,
        category: str | None,
        sort_field: str,
        sort_dir: int,
        skip: int,
        limit: int,
    ) -> list[dict]:
        """List products matching filter and sort criteria."""

    @abstractmethod
    def get_by_id(self, product_id: str) -> Optional[dict]:
        """Return product by id. Raise ValueError for invalid identifier."""

    @abstractmethod
    def get_by_barcode(self, barcode: str) -> Optional[dict]:
        """Return product by barcode if present."""

    # ------------------------------------------------------------------
    # Phase 3: Mutation operations
    # ------------------------------------------------------------------

    @abstractmethod
    def update_product(self, product_id: str, updates: dict) -> Optional[dict]:
        """Apply partial updates and return the updated document, or None."""

    @abstractmethod
    def delete_product(self, product_id: str) -> bool:
        """Delete product by id. Return True if a document was deleted."""

    @abstractmethod
    def increment_stock(self, product_id: str, qty_delta: int) -> None:
        """Atomically adjust stock_quantity by *qty_delta*."""

    # ------------------------------------------------------------------
    # Phase 3: Media operations
    # ------------------------------------------------------------------

    @abstractmethod
    def upload_media(
        self,
        product_id: str,
        filename: str,
        content: bytes,
        content_type: str,
        media_type: str,
        created_by: str,
    ) -> dict:
        """Store product media and return metadata dict with 'id' field."""

    @abstractmethod
    def add_media_ids_to_product(
        self, product_id: str, image_ids: list[str], video_ids: list[str]
    ) -> None:
        """Append media IDs to product image/video arrays."""

    @abstractmethod
    def list_media(self, product_id: str) -> list[dict]:
        """Return media metadata list for a product (newest first)."""

    @abstractmethod
    def get_media_content(self, media_id: str) -> Optional[tuple[bytes, str]]:
        """Return (content_bytes, content_type) for media, or None."""
