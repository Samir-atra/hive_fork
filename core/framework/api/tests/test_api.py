"""Test cases for the FastAPI REST API layer."""

from fastapi.testclient import TestClient

from framework.api.server import app

client = TestClient(app)


def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_agent_crud():
    """Test the Create, Read, Update, Delete flow for Agents."""
    # Create agent
    agent_data = {
        "name": "Test Agent",
        "description": "An agent for testing.",
        "system_prompt": "You are a test agent.",
    }
    res_create = client.post("/agents", json=agent_data)
    assert res_create.status_code == 201
    created_agent = res_create.json()
    assert created_agent["name"] == "Test Agent"
    agent_id = created_agent["id"]

    # Read agent
    res_get = client.get(f"/agents/{agent_id}")
    assert res_get.status_code == 200
    assert res_get.json()["id"] == agent_id

    # Update agent
    update_data = {
        "name": "Updated Agent",
        "description": "Updated description",
    }
    res_update = client.put(f"/agents/{agent_id}", json=update_data)
    assert res_update.status_code == 200
    assert res_update.json()["name"] == "Updated Agent"

    # List agents
    res_list = client.get("/agents")
    assert res_list.status_code == 200
    assert len(res_list.json()) > 0

    # Delete agent
    res_delete = client.delete(f"/agents/{agent_id}")
    assert res_delete.status_code == 204

    # Verify deletion
    res_get_deleted = client.get(f"/agents/{agent_id}")
    assert res_get_deleted.status_code == 404


def test_execution_flow():
    """Test the execution creation and cancellation flow."""
    # Setup agent
    agent_data = {"name": "Exec Agent"}
    res_agent = client.post("/agents", json=agent_data)
    agent_id = res_agent.json()["id"]

    # Create execution
    exec_data = {"task": "Do a flip"}
    res_exec = client.post(f"/agents/{agent_id}/execute", json=exec_data)
    assert res_exec.status_code == 201
    execution = res_exec.json()
    assert execution["task"] == "Do a flip"
    assert execution["agent_id"] == agent_id
    exec_id = execution["id"]

    # Get execution
    res_get = client.get(f"/executions/{exec_id}")
    assert res_get.status_code == 200
    assert res_get.json()["status"] == "running"

    # Cancel execution
    res_cancel = client.post(f"/executions/{exec_id}/cancel")
    assert res_cancel.status_code == 200
    assert res_cancel.json()["status"] == "cancelled"

    # Try cancelling again (should fail)
    res_cancel_again = client.post(f"/executions/{exec_id}/cancel")
    assert res_cancel_again.status_code == 400


def test_list_tools():
    """Test the tools listing endpoint."""
    response = client.get("/tools")
    assert response.status_code == 200
    tools = response.json()
    assert len(tools) > 0
    assert "name" in tools[0]
