"""MongoDB-backed product repository implementation."""
from datetime import datetime
from io import BytesIO
from typing import Optional

from bson import ObjectId
from gridfs import GridFSBucket

from app.database import get_collection
from app.domain.contracts.product_repository import ProductRepository


class MongoProductRepository(ProductRepository):
    """MongoDB repository for products."""

    def exists_by_sku(self, sku: str) -> bool:
        return get_collection("products").find_one({"sku": sku}) is not None

    def create(self, product_doc: dict) -> dict:
        doc = dict(product_doc)
        doc["created_at"] = datetime.utcnow()
        doc["updated_at"] = datetime.utcnow()
        result = get_collection("products").insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    def list_products(
        self,
        category: str | None,
        sort_field: str,
        sort_dir: int,
        skip: int,
        limit: int,
    ) -> list[dict]:
        query: dict = {}
        if category:
            query["category"] = {"$regex": f"^{category}$", "$options": "i"}
        cursor = get_collection("products").find(query).sort(sort_field, sort_dir).skip(skip).limit(limit)
        return list(cursor)

    def get_by_id(self, product_id: str) -> Optional[dict]:
        try:
            oid = ObjectId(product_id)
        except Exception as exc:
            raise ValueError("Invalid product ID") from exc
        return get_collection("products").find_one({"_id": oid})

    def get_by_barcode(self, barcode: str) -> Optional[dict]:
        return get_collection("products").find_one({"barcode": barcode})

    # ------------------------------------------------------------------
    # Phase 3: Mutation operations
    # ------------------------------------------------------------------

    def update_product(self, product_id: str, updates: dict) -> Optional[dict]:
        try:
            oid = ObjectId(product_id)
        except Exception:
            return None
        from pymongo import ReturnDocument
        return get_collection("products").find_one_and_update(
            {"_id": oid}, {"$set": updates}, return_document=ReturnDocument.AFTER,
        )

    def delete_product(self, product_id: str) -> bool:
        try:
            oid = ObjectId(product_id)
        except Exception:
            return False
        result = get_collection("products").delete_one({"_id": oid})
        return result.deleted_count > 0

    def increment_stock(self, product_id: str, qty_delta: int) -> None:
        try:
            oid = ObjectId(product_id)
        except Exception:
            return
        get_collection("products").update_one(
            {"_id": oid},
            {"$inc": {"stock_quantity": qty_delta}, "$set": {"updated_at": datetime.utcnow()}},
        )

    # ------------------------------------------------------------------
    # Phase 3: Media operations
    # ------------------------------------------------------------------

    def _media_bucket(self) -> GridFSBucket:
        return GridFSBucket(
            get_collection("product_media").database,
            bucket_name="product_media_files",
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
        try:
            product_oid = ObjectId(product_id)
        except Exception as exc:
            raise ValueError("Invalid product ID") from exc
        now = datetime.utcnow()
        gridfs_file_id = self._media_bucket().upload_from_stream(
            filename, content,
            metadata={
                "product_id": product_id,
                "media_type": media_type,
                "content_type": content_type,
            },
        )
        doc = {
            "product_id": product_oid,
            "filename": filename,
            "content_type": content_type,
            "media_type": media_type,
            "size": len(content),
            "created_at": now,
            "created_by": created_by,
            "gridfs_file_id": gridfs_file_id,
        }
        result = get_collection("product_media").insert_one(doc)
        return {"id": str(result.inserted_id), "media_type": media_type}

    def add_media_ids_to_product(
        self, product_id: str, image_ids: list[str], video_ids: list[str]
    ) -> None:
        try:
            oid = ObjectId(product_id)
        except Exception:
            return
        update_doc: dict = {"$set": {"updated_at": datetime.utcnow()}}
        if image_ids:
            update_doc.setdefault("$push", {})["image_media_ids"] = {"$each": image_ids}
        if video_ids:
            update_doc.setdefault("$push", {})["video_media_ids"] = {"$each": video_ids}
        get_collection("products").update_one({"_id": oid}, update_doc)

    def list_media(self, product_id: str) -> list[dict]:
        try:
            product_oid = ObjectId(product_id)
        except Exception:
            return []
        docs = list(
            get_collection("product_media")
            .find({"product_id": product_oid}, {"data": 0})
            .sort("created_at", -1)
        )
        media = []
        for d in docs:
            media.append({
                "id": str(d["_id"]),
                "filename": d.get("filename", ""),
                "content_type": d.get("content_type", "application/octet-stream"),
                "media_type": d.get("media_type", "image"),
                "size": d.get("size", 0),
                "created_at": d.get("created_at"),
                "url": f"/api/products/media/file/{str(d['_id'])}",
            })
        return media

    def get_media_content(self, media_id: str) -> Optional[tuple[bytes, str]]:
        try:
            media_oid = ObjectId(media_id)
        except Exception:
            return None
        media_doc = get_collection("product_media").find_one({"_id": media_oid})
        if not media_doc:
            return None
        content_type = media_doc.get("content_type", "application/octet-stream")
        if media_doc.get("gridfs_file_id"):
            buf = BytesIO()
            self._media_bucket().download_to_stream(media_doc["gridfs_file_id"], buf)
            return buf.getvalue(), content_type
        return bytes(media_doc.get("data") or b""), content_type
