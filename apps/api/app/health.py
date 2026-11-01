from fastapi import APIRouter, Request, Response
from pydantic import BaseModel
from sqlalchemy import text

router = APIRouter(tags=["health"])


class Health(BaseModel):
    status: str


@router.get("/healthz", response_model=Health, summary="Liveness")
async def healthz() -> Health:
    return Health(status="ok")


@router.get("/readyz", response_model=Health, summary="Readiness (checks the database)")
async def readyz(request: Request, response: Response) -> Health:
    try:
        async with request.app.state.session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        response.status_code = 503
        return Health(status="database_unavailable")
    return Health(status="ready")
