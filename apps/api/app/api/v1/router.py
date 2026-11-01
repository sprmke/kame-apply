from fastapi import APIRouter

from app.agent_bridge.router import router as agent_bridge_router
from app.ai.router import router as ai_router
from app.answers.router import router as answers_router
from app.applications.router import router as applications_router
from app.audit.router import router as activity_router
from app.auth.router import auth_router, me_router
from app.autosubmit.router import router as autosubmit_router
from app.extension.router import router as extension_router
from app.feedback.router import router as feedback_router
from app.gaps.router import router as gaps_router
from app.ingest.router import router as ingest_router
from app.interview.router import router as interview_router
from app.matching.router import router as matching_router
from app.notifications.router import router as notifications_router
from app.ops.router import router as ops_router
from app.profiles.router import router as profiles_router
from app.referrals.router import router as referrals_router
from app.responses.router import router as responses_router
from app.resumes.router import router as resumes_router
from app.runs.live_ws import router as live_ws_router
from app.runs.router import router as runs_router
from app.safety.router import router as safety_router
from app.schedules.router import router as schedules_router
from app.sources.router import router as sources_router
from app.strategy.router import router as strategy_router
from app.taxonomy.router import router as taxonomy_router
from app.tracks.router import router as tracks_router
from app.workspaces.router import invitations_router, workspace_router, workspaces_router

router = APIRouter(prefix="/api/v1")

# Module routers are mounted here as phases add them (workspaces, profiles, ...).
router.include_router(auth_router)
router.include_router(me_router)
router.include_router(workspaces_router)
router.include_router(invitations_router)
router.include_router(workspace_router)
router.include_router(ai_router)
router.include_router(activity_router)
router.include_router(profiles_router)
router.include_router(tracks_router)
router.include_router(taxonomy_router)
router.include_router(sources_router)
router.include_router(matching_router)
router.include_router(safety_router)
router.include_router(resumes_router)
router.include_router(applications_router)
router.include_router(answers_router)
router.include_router(schedules_router)
router.include_router(notifications_router)
router.include_router(agent_bridge_router)
router.include_router(extension_router)
router.include_router(feedback_router)
router.include_router(ops_router)
router.include_router(runs_router)
router.include_router(live_ws_router)
router.include_router(ingest_router)
router.include_router(strategy_router)
router.include_router(autosubmit_router)
router.include_router(responses_router)
router.include_router(interview_router)
router.include_router(gaps_router)
router.include_router(referrals_router)
