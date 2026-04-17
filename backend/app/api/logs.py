"""Log management APIs (separate from reports)."""
from fastapi import APIRouter, Depends, HTTPException, status
from app.utils.logger import get_logs
from app.utils.security import decode_token, get_token_from_credentials, security

router = APIRouter(prefix="/api/logs", tags=["Logs"])


def get_current_admin(credentials=Depends(security)):
    token = get_token_from_credentials(credentials)
    payload = decode_token(token)
    if not payload or payload.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return payload.get("sub")


@router.get("/audit", summary="Get audit logs (admin only)")
async def get_audit_logs(admin=Depends(get_current_admin), limit: int = 100):
    logs = get_logs(limit)
    return {"count": len(logs), "logs": logs}
