from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase

from framework.schemas.intervention import InterventionStatus
from framework.server.routes_interventions import _interventions, register_routes


class TestInterventionsRoutes(AioHTTPTestCase):
    async def get_application(self):
        app = web.Application()
        register_routes(app)
        return app

    def setUp(self):
        super().setUp()
        _interventions.clear()

    def tearDown(self):
        _interventions.clear()
        super().tearDown()

    async def test_create_intervention(self):
        data = {
            "session_id": "sess-123",
            "node_id": "node-abc",
            "summary": "Need approval for refund",
            "business_context": "Customer is VIP",
            "technical_decision": "Refund amount is > 1000",
        }
        resp = await self.client.post("/api/interventions", json=data)
        assert resp.status == 201
        result = await resp.json()
        assert "id" in result
        assert result["status"] == InterventionStatus.PENDING
        assert len(result["audit_trail"]) == 1
        assert result["audit_trail"][0]["action"] == "created"

    async def test_list_interventions(self):
        data = {
            "session_id": "sess-123",
            "node_id": "node-abc",
            "summary": "test",
            "business_context": "test context",
            "technical_decision": "tech detail",
        }
        await self.client.post("/api/interventions", json=data)
        resp = await self.client.get("/api/interventions")
        assert resp.status == 200
        result = await resp.json()
        assert len(result) == 1

    async def test_approve_intervention(self):
        data = {
            "session_id": "sess-123",
            "node_id": "node-abc",
            "summary": "Need approval",
            "business_context": "VIP",
            "technical_decision": "tech",
        }
        resp = await self.client.post("/api/interventions", json=data)
        inv = await resp.json()
        iid = inv["id"]

        resp = await self.client.post(
            f"/api/interventions/{iid}/approve", json={"actor": "ceo", "reason": "Looks good"}
        )
        assert resp.status == 200
        result = await resp.json()
        assert result["status"] == InterventionStatus.APPROVED
        assert len(result["audit_trail"]) == 2
        assert result["audit_trail"][1]["action"] == "approved"
        assert result["audit_trail"][1]["actor"] == "ceo"
        assert result["audit_trail"][1]["details"] == "Looks good"

    async def test_reject_intervention(self):
        data = {
            "session_id": "sess-123",
            "node_id": "node-abc",
            "summary": "Need approval",
            "business_context": "VIP",
            "technical_decision": "tech",
        }
        resp = await self.client.post("/api/interventions", json=data)
        inv = await resp.json()
        iid = inv["id"]

        resp = await self.client.post(f"/api/interventions/{iid}/reject")
        assert resp.status == 200
        result = await resp.json()
        assert result["status"] == InterventionStatus.REJECTED

    async def test_escalate_intervention(self):
        data = {
            "session_id": "sess-123",
            "node_id": "node-abc",
            "summary": "Need approval",
            "business_context": "VIP",
            "technical_decision": "tech",
        }
        resp = await self.client.post("/api/interventions", json=data)
        inv = await resp.json()
        iid = inv["id"]

        resp = await self.client.post(f"/api/interventions/{iid}/escalate")
        assert resp.status == 200
        result = await resp.json()
        assert result["status"] == InterventionStatus.ESCALATED
