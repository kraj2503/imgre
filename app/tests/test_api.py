from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_read_root():
    """Verify the root health endpoint runs successfully."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["project"] == "Imgre Multi-Agent Automation"

def test_generation_router_registered():
    """Verify that generation endpoint paths are correctly registered in the FastAPI app."""
    # We test with an invalid payload type to trigger a 422 Unprocessable Entity,
    # which confirms the route exists, is registered, and executes validation correctly.
    response = client.post("/api/v1/generation/generate-art", json={"user_idea": ["invalid", "type"]})
    assert response.status_code == 422
