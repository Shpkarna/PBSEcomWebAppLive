"""SQL Server-backed product repository implementation (Phase 7)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.data.repositories.mssql_base import MSSQLRepositoryBase
from app.domain.contracts.product_repository import ProductRepository


class MSSQLProductRepository(MSSQLRepositoryBase, ProductRepository):
    """SQL Server implementation for product persistence and media storage."""

    _ALLOWED_SORT_FIELDS = {"created_at", "name", "sell_price", "stock_quantity"}

    def exists_by_sku(self, sku: str) -> bool:
        return self.find_one_doc("products", {"sku": sku}) is not None

    def create(self, product_doc: dict) -> dict:
        doc = dict(product_doc)
        now = datetime.utcnow()
        doc.setdefault("created_at", now)
        doc.setdefault("updated_at", now)
        return self.insert_one_doc("products", doc)

    def list_products(
        self,
        category: str | None,
        sort_field: str,
        sort_dir: int,
        skip: int,
        limit: int,
    ) -> list[dict]:
        sort_key = sort_field if sort_field in self._ALLOWED_SORT_FIELDS else "created_at"
        if category:
            rows = self._execute(
                (
                    f"SELECT * FROM products WHERE LOWER(category) = LOWER(?) "
                    f"ORDER BY {sort_key} {'DESC' if sort_dir < 0 else 'ASC'} "
                    f"OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
                ),
                [category, int(skip), int(limit)],
                fetchall=True,
            )
            spec = self._spec("products")
            return [self._row_to_doc(spec, row) for row in rows or [] if row]

        return self.find_many_docs(
            "products",
            {},
            order_by=sort_key,
            descending=sort_dir < 0,
            skip=skip,
            limit=limit,
        )

    def get_by_id(self, product_id: str) -> Optional[dict]:
        return self.find_one_doc("products", {"id": product_id})

    def get_by_barcode(self, barcode: str) -> Optional[dict]:
        return self.find_one_doc("products", {"barcode": barcode})

    def update_product(self, product_id: str, updates: dict) -> Optional[dict]:
        matched = self.update_one_doc("products", {"id": product_id}, updates)
        if not matched:
            return None
        return self.get_by_id(product_id)

    def delete_product(self, product_id: str) -> bool:
        return self.delete_many_docs("products", {"id": product_id}) > 0

    def increment_stock(self, product_id: str, qty_delta: int) -> None:
        self._execute(
            "UPDATE products SET stock_quantity = stock_quantity + ?, updated_at = ? WHERE id = ?",
            [int(qty_delta), datetime.utcnow(), product_id],
        )

    def upload_media(
        self,
        product_id: str,
        filename: str,
        content: bytes,
        content_type: str,
        media_type: str,
        created_by: str,
    ) -> dict:
        stored = self.insert_one_doc(
            "product_media",
            {
                "product_id": product_id,
                "filename": filename,
                "content_type": content_type,
                "media_type": media_type,
                "size": len(content),
                "created_at": datetime.utcnow(),
                "created_by": created_by,
                "data": content,
            },
        )
        return {"id": stored["id"], "media_type": media_type}

    def add_media_ids_to_product(self, product_id: str, image_ids: list[str], video_ids: list[str]) -> None:
        product = self.get_by_id(product_id)
        if not product:
            return
        next_image_ids = list(product.get("image_media_ids", []))
        next_video_ids = list(product.get("video_media_ids", []))
        next_image_ids.extend(image_ids)
        next_video_ids.extend(video_ids)
        self.update_one_doc(
            "products",
            {"id": product_id},
            {
                "image_media_ids": next_image_ids,
                "video_media_ids": next_video_ids,
                "updated_at": datetime.utcnow(),
            },
        )

    def list_media(self, product_id: str) -> list[dict]:
        docs = self.find_many_docs(
            "product_media",
            {"product_id": product_id},
            order_by="created_at",
            descending=True,
        )
        return [
            {
                "id": doc["id"],
                "filename": doc.get("filename", ""),
                "content_type": doc.get("content_type", "application/octet-stream"),
                "media_type": doc.get("media_type", "image"),
                "size": doc.get("size", 0),
                "created_at": doc.get("created_at"),
                "url": f"/api/products/media/file/{doc['id']}",
            }
            for doc in docs
        ]

    def get_media_content(self, media_id: str) -> Optional[tuple[bytes, str]]:
        media = self.find_one_doc("product_media", {"id": media_id})
        if not media:
            return None
        return bytes(media.get("data") or b""), media.get("content_type", "application/octet-stream")
