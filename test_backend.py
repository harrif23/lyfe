import pytest
from unittest.mock import patch, MagicMock
import json
from backend import process_text, TextInput


@pytest.fixture
def mock_supabase():
    with patch("main.supabase") as mock:
        yield mock


@pytest.fixture
def mock_gemini_model():
    with patch("main.model") as mock:
        yield mock


@pytest.mark.asyncio
async def test_process_text_success():
    # # Mock Gemini API response
    # mock_gemini_response = MagicMock()
    # mock_gemini_response.text = json.dumps({
    #     "project_name": "WIP: Health Trend Tracker",
    #     "description": "WIP is a web application that allows users to upload medical data.",
    #     "category": "health",
    #     "product_type": "app",
    #     "timeline": "4 weeks",
    #     "weeks": [
    #         {
    #             "week": 1,
    #             "tasks": [
    #                 {"task_num": 1, "task": "Define user personas and key features for the app."},
    #                 {"task_num": 2, "task": "Research existing health tracking apps."}
    #             ]
    #         }
    #     ]
    # })
    # mock_gemini_model.generate_content.return_value = mock_gemini_response
    #
    # # Mock Supabase responses
    # mock_supabase.table().insert().execute.side_effect = [
    #     MagicMock(data=[{"id": 1}]),  # Project insertion
    #     MagicMock(),  # Task insertion
    #     MagicMock()  # Task insertion
    # ]

    # Call the function directly
    result = await process_text(TextInput(text="Create a health app", user_id=1))
    print(result)

    # Assertions
    # assert result.project_name == "WIP: Health Trend Tracker"
    # assert result.category == "health"
    # assert len(result.weeks) == 1
    # assert len(result.weeks[0].tasks) == 2


@pytest.mark.asyncio
async def test_process_text_gemini_error(mock_gemini_model):
    # Mock Gemini API error
    mock_gemini_model.generate_content.side_effect = Exception("Gemini API Error")

    # Call the function and expect an exception
    with pytest.raises(Exception) as exc_info:
        await process_text(TextInput(text="Create a health app", user_id=1))

    assert str(exc_info.value) == "Gemini API Error"


@pytest.mark.asyncio
async def test_process_text_supabase_error(mock_supabase, mock_gemini_model):
    # Mock Gemini API response
    mock_gemini_response = MagicMock()
    mock_gemini_response.text = json.dumps({"project_name": "Test Project"})
    mock_gemini_model.generate_content.return_value = mock_gemini_response

    # Mock Supabase error
    mock_supabase.table().insert().execute.side_effect = Exception("Supabase Error")

    # Call the function and expect an exception
    with pytest.raises(Exception) as exc_info:
        await process_text(TextInput(text="Create a project", user_id=1))

    assert str(exc_info.value) == "Supabase Error"

# Add more test cases as needed

