"""Test configuration and fixtures for HR Onboarding Orchestrator."""

import pytest


@pytest.fixture
def sample_onboarding_context():
    """Sample context for onboarding workflow."""
    return {
        "candidate_name": "Jane Smith",
        "candidate_email": "jane.smith@example.com",
        "position": "Senior Software Engineer",
        "department": "Engineering",
        "start_date": "2024-03-15",
        "envelope_id": "test-envelope-12345",
    }


@pytest.fixture
def sample_signed_context():
    """Sample context with signed envelope status."""
    return {
        "candidate_name": "John Doe",
        "candidate_email": "john.doe@example.com",
        "position": "Product Manager",
        "department": "Product",
        "start_date": "2024-03-01",
        "envelope_id": "test-envelope-67890",
        "envelope_status": "signed",
    }


@pytest.fixture
def sample_escalation_context():
    """Sample context for escalation scenario."""
    return {
        "candidate_name": "Alice Johnson",
        "candidate_email": "alice.j@example.com",
        "position": "Data Analyst",
        "department": "Analytics",
        "start_date": "2024-03-20",
        "envelope_id": "test-envelope-11111",
        "envelope_status": "pending",
        "elapsed_hours": "50",
    }
