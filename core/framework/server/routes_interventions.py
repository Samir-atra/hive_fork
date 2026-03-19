import logging

from aiohttp import web

from framework.schemas.intervention import AuditLog, Intervention

logger = logging.getLogger(__name__)

# Basic in-memory store for interventions. In a real system, this would be persisted.
_interventions: dict[str, Intervention] = {}


async def handle_list_interventions(request: web.Request) -> web.Response:
    """GET /api/interventions — list all interventions."""
    return web.json_response([i.model_dump(mode="json") for i in _interventions.values()])


async def handle_get_intervention(request: web.Request) -> web.Response:
    """GET /api/interventions/{id} — get a single intervention by ID."""
    iid = request.match_info["id"]
    if iid not in _interventions:
        return web.json_response({"error": "Not found"}, status=404)
    return web.json_response(_interventions[iid].model_dump(mode="json"))


async def handle_create_intervention(request: web.Request) -> web.Response:
    """POST /api/interventions — create a new intervention."""
    data = await request.json()
    try:
        inv = Intervention(**data)
        inv.audit_trail.append(AuditLog(action="created", actor="system"))
        _interventions[inv.id] = inv
        return web.json_response(inv.model_dump(mode="json"), status=201)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)


async def handle_approve_intervention(request: web.Request) -> web.Response:
    """POST /api/interventions/{id}/approve — approve an intervention."""
    iid = request.match_info["id"]
    if iid not in _interventions:
        return web.json_response({"error": "Not found"}, status=404)

    data = await request.json() if request.can_read_body else {}
    actor = data.get("actor", "business_user")
    reason = data.get("reason")

    inv = _interventions[iid]
    inv.approve(actor=actor, reason=reason)
    return web.json_response(inv.model_dump(mode="json"))


async def handle_reject_intervention(request: web.Request) -> web.Response:
    """POST /api/interventions/{id}/reject — reject an intervention."""
    iid = request.match_info["id"]
    if iid not in _interventions:
        return web.json_response({"error": "Not found"}, status=404)

    data = await request.json() if request.can_read_body else {}
    actor = data.get("actor", "business_user")
    reason = data.get("reason")

    inv = _interventions[iid]
    inv.reject(actor=actor, reason=reason)
    return web.json_response(inv.model_dump(mode="json"))


async def handle_escalate_intervention(request: web.Request) -> web.Response:
    """POST /api/interventions/{id}/escalate — escalate an intervention."""
    iid = request.match_info["id"]
    if iid not in _interventions:
        return web.json_response({"error": "Not found"}, status=404)

    data = await request.json() if request.can_read_body else {}
    actor = data.get("actor", "business_user")
    reason = data.get("reason")

    inv = _interventions[iid]
    inv.escalate(actor=actor, reason=reason)
    return web.json_response(inv.model_dump(mode="json"))


def register_routes(app: web.Application) -> None:
    """Register intervention routes."""
    app.router.add_get("/api/interventions", handle_list_interventions)
    app.router.add_post("/api/interventions", handle_create_intervention)
    app.router.add_get("/api/interventions/{id}", handle_get_intervention)
    app.router.add_post("/api/interventions/{id}/approve", handle_approve_intervention)
    app.router.add_post("/api/interventions/{id}/reject", handle_reject_intervention)
    app.router.add_post("/api/interventions/{id}/escalate", handle_escalate_intervention)
