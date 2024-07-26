# test_main.py
from fastapi.testclient import TestClient
from main import app
import pytest
from unittest.mock import patch, MagicMock

client = TestClient(app)

@pytest.fixture
def mock_supabase():
    with patch("main.supabase") as mock:
        yield mock

@pytest.fixture
def mock_gemini_model():
    with patch("main.model") as mock:
        yield mock


def test_process_text(mock_supabase, mock_gemini_model):
    # Mock Gemini API response
    mock_gemini_response = MagicMock()
    mock_gemini_response.text = '''
    {
        "project_name":"WIP: Health Trend Tracker",
        "description":"WIP is a web application that allows users to upload medical data (lab reports, etc.) and track health trends over time.",
        "category":"health",
        "product_type":"app",
        "timeline":"4 weeks",
        "weeks":[
            {
                "week":1,
                "tasks":[
                    {"task_num":1,"task":"Define user personas and key features for the app."},
                    {"task_num":2,"task":"Research existing health tracking apps and data visualization tools."}
                ]
            }
        ]
    }
    '''
    mock_gemini_model.generate_content.return_value = mock_gemini_response

    # Mock Supabase responses
    mock_supabase.table().insert().execute.side_effect = [
        MagicMock(data=[{"id": 1}]),  # Project insertion
        MagicMock(),  # Task insertion
        MagicMock()   # Task insertion
    ]

    response = client.post("/process-text", json={"text": "Create a health app", "user_id": 1})
    assert response.status_code == 200
    assert response.json()["project_name"] == "WIP: Health Trend Tracker"
    assert response.json()["category"] == "health"
    assert len(response.json()["weeks"]) == 1
    assert len(response.json()["weeks"][0]["tasks"]) == 2


def test_get_project(mock_supabase):
    # Mock Supabase response
    mock_supabase.table().select().eq().execute.return_value.data = [{
        "id": 1,
        "user_id": 1,
        "project_name": "WIP: Health Trend Tracker",
        "description": "WIP is a web application that allows users to upload medical data.",
        "category": "health",
        "product_type": "app",
        "timeline": "4 weeks"
    }]

    response = client.get("/get-project/1")
    assert response.status_code == 200
    assert response.json()["project_name"] == "WIP: Health Trend Tracker"
    assert response.json()["category"] == "health"


def test_get_tasks(mock_supabase):
    # Mock Supabase response
    mock_supabase.table().select().eq().execute.return_value.data = [
        {
            "id": 1,
            "project_id": 1,
            "user_id": 1,
            "week_no": 1,
            "task_no": 1,
            "task": "Define user personas and key features for the app."
        },
        {
            "id": 2,
            "project_id": 1,
            "user_id": 1,
            "week_no": 1,
            "task_no": 2,
            "task": "Research existing health tracking apps and data visualization tools."
        }
    ]

    response = client.get("/get-tasks/1")
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["task"] == "Define user personas and key features for the app."


def test_get_project_not_found(mock_supabase):
    # Mock Supabase response for not found
    mock_supabase.table().select().eq().execute.return_value.data = []

    response = client.get("/get-project/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


def test_process_text_error(mock_gemini_model):
    # Mock Gemini API error
    mock_gemini_model.generate_content.side_effect = Exception("API Error")

    response = client.post("/process-text", json={"text": "Create a health app", "user_id": 1})
    assert response.status_code == 500
    assert "API Error" in response.json()["detail"]

# Add more test cases as needed

