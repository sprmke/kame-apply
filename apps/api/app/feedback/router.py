from fastapi import APIRouter, Depends, Request

from app.core.ratelimit import client_ip
from app.core.security import WorkspaceContext, require_action
from app.feedback import service
from app.feedback.schemas import FeedbackCreate, FeedbackRead

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackRead)
async def post_feedback(
    body: FeedbackCreate,
    request: Request,
    ctx: WorkspaceContext = Depends(require_action("data.write")),
):
    settings = request.app.state.settings
    if settings.auth_rate_limit_enabled:
        request.app.state.rate_limiter.check(
            f"feedback:ip:{client_ip(request)}", limit=10, window_seconds=3600
        )
        request.app.state.rate_limiter.check(
            f"feedback:user:{ctx.user_id}", limit=20, window_seconds=86400
        )
    url = await service.submit(
        ctx, settings, category=body.category, message=body.message, page=body.page
    )
    return FeedbackRead(ok=True, issue_url=url)
