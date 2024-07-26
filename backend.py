import os
import json
import logging
from datetime import datetime

from typing import List, Any, Optional
from zoneinfo import ZoneInfo, available_timezones
from collections import defaultdict
from dotenv import load_dotenv

import asyncio
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi import Request as FARequest
from pydantic import BaseModel, field_validator
from supabase import create_client, Client
import google.generativeai as genai

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.http import HttpRequest


load_dotenv()
app = FastAPI(port=8080)
# Configure the logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# Create a logger
logger = logging.getLogger(__name__)

# Initialize Supabase client
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# Initialize Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
generation_config = {
  "temperature": 1,
  "top_p": 0.95,
  "top_k": 64,
  "max_output_tokens": 8192,
  "response_mime_type": "application/json",
}
model = genai.GenerativeModel(
    model_name='gemini-1.5-flash',
    generation_config=generation_config,
)


class TextInput(BaseModel):
    text: str
    user_id: int


class Task(BaseModel):
    week_no: int
    task_no: int
    weekly_goal: str
    task: str


class ProjectResponse(BaseModel):
    project_id: int
    project_name: str
    description: str
    category: str
    product_type: str
    timeline: str
    tasks: List[Task]


class ProjectDB(BaseModel):
    project_id: int
    user_id: int
    project_name: str
    description: str
    category: str
    product_type: str
    timeline: str


class TaskDB(BaseModel):
    task: str
    task_id: int
    task_no: int


class WeekDB(BaseModel):
    week_no: int
    tasks: List[TaskDB]


class TasksDB(BaseModel):
    project_id: int
    project_name: str
    description: str
    category: str
    weeks: List[WeekDB]


class WeeklyGoal(BaseModel):
    project_id: int
    week_no: int
    weekly_goal: str


class WeeklyGoalDB(BaseModel):
    project_id: int
    project_name: str
    description: str
    category: str
    weekly_goal: List[WeeklyGoal]


class WeeklyTasks(BaseModel):
    task_id: int
    week_no: int
    task_no: int
    task: str


class WeeklyTasksDB(BaseModel):
    project_id: int
    week_no: int
    weekly_goal: str
    tasks: List[WeeklyTasks]


class EventRequest(BaseModel):
    summary: str
    start_time: datetime
    end_time: datetime
    timezone: str

    @field_validator('timezone')
    def validate_timezone(cls, v):
        if v not in available_timezones():
            raise ValueError(f"Invalid timezone: {v}")
        return v

    @field_validator('end_time')
    def validate_end_time(cls, v, info) -> datetime:
        values = info.data
        start_time = values.get('start_time')
        if start_time and v <= start_time:
            raise ValueError("end_time must be after start_time")
        return v


class EventResponse(BaseModel):
    id: str
    html_link: str
    summary: str
    start: datetime
    end: datetime

class AuthRequest(BaseModel):
    provider: str

class CallbackRequest(BaseModel):
    callback_url: str


@app.get("/")
def index():
    return {"message": "Hello, World!"}


@app.post("/auth/signin")
async def sign_in_with_provider(auth_request: AuthRequest):
    """
    Initiate the sign-in process with a social provider.
    """
    try:
        logger.info(f"Attempting to sign in with provider: {auth_request.provider}")
        response = supabase.auth.sign_in_with_oauth({
            "provider": auth_request.provider,
            # "options": {
            #     "redirect_to": "http://localhost:8000/auth-callback"  # Local callback URL
            # }
        })
        logger.info(f"Successfully initiated sign-in. Auth URL: {response.url}")

        # Log the full auth URL for debugging
        logger.info(f"Full auth URL: {response.url}")

        return {"auth_url": response.url}
    except Exception as e:
        logger.error(f"Error initiating {auth_request.provider} sign-in: {str(e)}")
        if "Unsupported provider" in str(e):
            logger.error(f"Provider '{auth_request.provider}' may not be enabled in Supabase settings.")
            raise HTTPException(status_code=400,
                                detail=f"Provider '{auth_request.provider}' is not enabled. Please check your Supabase configuration.")
        raise HTTPException(status_code=400, detail=f"Error initiating {auth_request.provider} sign-in: {str(e)}")



@app.get("/auth-callback")
async def auth_callback(request: FARequest):
    """
    Handle the callback after social authentication.
    """
    # Get all query parameters
    logger.info(f"Request received: {request}")
    logger.info(f"Request headers: {request.headers}")
    logger.info(f"Raw URL: {request.url.query}")
    logger.info(f"Query parameters: {request.query_params}")
    params = dict(request.query_params)
    logger.info(f"Received callback request with params: {params}")

    # Check for error
    if 'error' in params:
        logger.error(f"Error in OAuth callback: {params['error']}")
        raise HTTPException(status_code=400, detail=f"OAuth error: {params['error']}")

    # If we have an access_token and refresh_token, we can use them directly
    if 'access_token' in params and 'refresh_token' in params:
        try:
            logger.info("Attempting to get user with access token")
            response = supabase.auth.get_user(params['access_token'])
            user = response.user
            if user:
                logger.info(f"Successfully authenticated user: {user.email}")
                return {
                    "user_id": user.id,
                    "email": user.email,
                    "provider": user.app_metadata.get("provider")
                }
            else:
                logger.error("Failed to get user information")
                raise HTTPException(status_code=400, detail="Failed to get user information")
        except Exception as e:
            logger.error(f"Error getting user information: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Error getting user information: {str(e)}")
    else:
        logger.error("No access_token found in callback parameters")
        raise HTTPException(status_code=400, detail="Invalid callback parameters")


@app.post("/auth/callback")
async def handle_auth_callback(callback_request: CallbackRequest):
    """
    Handle the callback after social authentication.
    """
    try:
        response = supabase.auth.exchange_code_for_session(callback_request.callback_url)
        session = response.session
        if session and session.user:
            return {
                "user_id": session.user.id,
                "email": session.user.email,
                "provider": session.user.app_metadata.get("provider")
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to get user information")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error handling auth callback: {str(e)}")


@app.get("/user")
async def get_user(access_token: str):
    """
    Retrieve user information using the access token.
    """
    try:
        response = supabase.auth.get_user(access_token)
        user = response.user
        if user:
            return {
                "user_id": user.id,
                "email": user.email,
                "provider": user.app_metadata.get("provider")
            }
        else:
            raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error retrieving user information: {str(e)}")


@app.post("/gen-tasks", response_model=ProjectResponse)
async def generate_tasks(input_data: TextInput):
    try:
        # Call Gemini API
        response = model.generate_content([
            "You're an expert in generating tasks for project ideas. You'll be given a project idea, this could be a project in tech space like AI, software, application development or music or film making, or any kind of artistic project. You are responsible for generating step by step tasks for how to execute that idea. Keep the tasks as simple as possible. The tasks you generate must be able to be completed within the timeline provided to you. Keep it simple when generating tasks, I want the tasks to be high level and easily achieving rather than an overwhelming list that is not very motivating to begin the work. Don't generate more than three tasks per week. Make sure the tasks for each week are scoped in a way that they can be completed within specified weeks. It is very important that you scope the tasks within the limits of the project idea. Do not include anything that is not in the scope of the project idea. Include project name, description of the project, category, product_type, timeline, weeks the tasks for each week.",
            "input: wip - Track Your Health Trends. Upload your medical data and lab reports. Get insights and see how diet and supplement protocols affect you over time. I want to finish this project in 4 weeks",
            "output: {\"project_name\":\"WIP: Health Trend Tracker\",\"description\":\"WIP is a web application that allows users to upload medical data (lab reports, etc.) and track health trends over time. It provides insights on how diet, supplements, and lifestyle choices affect various health parameters.\",\"category\":\"health\",\"product_type\":\"app\",\"timeline\":\"4 weeks\",\"tasks\":[{\"week_no\":1,\"weekly_goal\":\"Project Setup and User Interface Design\",\"task_no\":1,\"task\":\"Define user personas and key features for the app.\"},{\"week_no\":1,\"weekly_goal\":\"Project Setup and User Interface Design\",\"task_no\":2,\"task\":\"Research existing health tracking apps and data visualization tools.\"},{\"week_no\":1,\"weekly_goal\":\"Project Setup and User Interface Design\",\"task_no\":3,\"task\":\"Create a basic wireframe for the app's UI and data input/output methods.\"},{\"week_no\":1,\"weekly_goal\":\"Project Setup and User Interface Design\",\"task_no\":4,\"task\":\"Choose the technology stack for frontend and backend development.\"},{\"week_no\":2,\"weekly_goal\":\"Data Input and Storage\",\"task_no\":1,\"task\":\"Develop the user authentication and profile creation system.\"},{\"week_no\":2,\"weekly_goal\":\"Data Input and Storage\",\"task_no\":2,\"task\":\"Build the interface for uploading and storing medical data.\"},{\"week_no\":2,\"weekly_goal\":\"Data Input and Storage\",\"task_no\":3,\"task\":\"Implement basic data visualization capabilities (charts, graphs).\"},{\"week_no\":2,\"weekly_goal\":\"Data Input and Storage\",\"task_no\":4,\"task\":\"Start building the trend analysis and insight generation algorithms.\"},{\"week_no\":3,\"weekly_goal\":\"Trend Analysis and Visualization\",\"task_no\":1,\"task\":\"Enhance data visualization with interactive features and filtering options.\"},{\"week_no\":3,\"weekly_goal\":\"Trend Analysis and Visualization\",\"task_no\":2,\"task\":\"Integrate AI-powered insights based on user data and research trends.\"},{\"week_no\":3,\"weekly_goal\":\"Trend Analysis and Visualization\",\"task_no\":3,\"task\":\"Develop a personalized dashboard for users to track their health trends over time.\"},{\"week_no\":3,\"weekly_goal\":\"Trend Analysis and Visualization\",\"task_no\":4,\"task\":\"Conduct user testing and gather feedback for improvement.\"},{\"week_no\":4,\"weekly_goal\":\"Testing and Deployment\",\"task_no\":1,\"task\":\"Implement secure data storage and privacy features.\"},{\"week_no\":4,\"weekly_goal\":\"Testing and Deployment\",\"task_no\":2,\"task\":\"Integrate with wearable devices and other health data sources.\"},{\"week_no\":4,\"weekly_goal\":\"Testing and Deployment\",\"task_no\":3,\"task\":\"Develop a marketing strategy and plan for launch.\"},{\"week_no\":4,\"weekly_goal\":\"Testing and Deployment\",\"task_no\":4,\"task\":\"Finalize the application and deploy it on a chosen platform.\"}]}",
            f"input: {input_data.text}",
            "output: ",
        ])
        # response = model.generate_content(input_data.text)
        gemini_data = json.loads(response.text)
        logger.info(f"Response from LLM -> {gemini_data}")

        # Insert project data
        project_data = {
            "user_id": input_data.user_id,
            "project_name": gemini_data["project_name"],
            "description": gemini_data["description"],
            "category": gemini_data["category"],
            "product_type": gemini_data["product_type"],
            "timeline": gemini_data["timeline"]
        }
        project_result = supabase.table("projects").insert(project_data).execute()
        project_id = project_result.data[0]['project_id']
        logger.info(f"Response from DB after inserting projects. Project ID -> {project_id}")

        tasks = gemini_data["tasks"]
        tasks[:] = [{**task, 'project_id': project_id} for task in tasks]
        response = supabase.table("tasks").insert(tasks).execute()
        logger.info(f"Response from DB after inserting tasks -> {response}")

        gemini_data['project_id'] = project_id
        return ProjectResponse(**gemini_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/get-project/{project_id}", response_model=ProjectDB)
async def get_project(project_id: int):
    try:
        projects_result = supabase.table("projects").select(
            "project_id, project_name, description, category, product_type, timeline, user_id"
        ).eq("project_id", project_id).execute()
        print(projects_result.data)
        if not projects_result.data:
            raise HTTPException(status_code=404, detail="Project not found")
        return ProjectDB(**projects_result.data[0])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/get-tasks/{project_id}", response_model=TasksDB)
async def get_tasks(project_id: int):
    try:
        logger.info(f"Retrieving tasks for project {project_id}")
        result = (supabase.table("projects")
                  .select("project_id, project_name, description, category, tasks(task_id, week_no, task_no, task)")
                  .eq("project_id", project_id)
                  .execute())
        project = result.data[0]
        weeks_dict = defaultdict(list)
        for task in project['tasks']:
            week_no = task.pop('week_no')
            weeks_dict[week_no].append(task)
        weeks = [{'week_no': week_no, 'tasks': tasks} for week_no, tasks in weeks_dict.items()]
        transformed_project = {
            'project_id': project['project_id'],
            'project_name': project['project_name'],
            'description': project['description'],
            'category': project['category'],
            'weeks': weeks
        }
        logger.info(f"Sending response -> {transformed_project}")
        return TasksDB(**transformed_project)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/get-weekly-goal/{project_id}", response_model=WeeklyGoalDB)
async def get_weekly_goal(project_id: int):
    try:
        logger.info(f"Retrieving weekly goals for project {project_id}")
        project_details_res = (supabase.table("projects")
                               .select("project_id, project_name, description, category)")
                               .eq("project_id", project_id)
                               .execute())
        weekly_goals_res = (supabase.table("weekly_goal")
                            .select("project_id, week_no, weekly_goal)")
                            .eq("project_id", project_id)
                            .execute())
        project_details_res = project_details_res.data[0]
        weekly_goals_res = weekly_goals_res.data
        constructed_result = {
            'project_id': project_details_res['project_id'],
            'project_name': project_details_res['project_name'],
            'description': project_details_res['description'],
            'category': project_details_res['category'],
            'weekly_goal': weekly_goals_res
        }
        logger.info(f"Sending response -> {constructed_result}")
        return WeeklyGoalDB(**constructed_result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/get-weekly-tasks/{project_id}/{week_no}", response_model=WeeklyTasksDB)
async def get_weekly_tasks(project_id: int, week_no: int):
    try:
        logger.info(f"Retrieving weekly goals for project {project_id}")
        weekly_tasks_res = (supabase.table("tasks")
                            .select("project_id, week_no, weekly_goal, task_id, task_no, task")
                            .filter('project_id', 'eq', str(project_id))
                            .filter('week_no', 'eq', str(week_no))
                            .execute())
        weekly_goal_details = weekly_tasks_res.data[0]
        constructed_result = {
            'project_id': weekly_goal_details['project_id'],
            'week_no': weekly_goal_details['week_no'],
            'weekly_goal': weekly_goal_details['weekly_goal'],
            'tasks': weekly_tasks_res.data
        }
        logger.info(f"Sending response -> {constructed_result}")
        return WeeklyTasksDB(**constructed_result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def get_calendar_service():
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    creds = None
    # The file token.json stores the user's access and refresh tokens
    if os.path.exists('calendars/creds/token.json'):
        creds = Credentials.from_authorized_user_file('calendars/creds/token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            asyncio.to_thread(creds.refresh, Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                '/Users/hp/Documents/projects/lyfe/calendars/creds/gcal_creds.json', SCOPES)
            creds = await asyncio.to_thread(flow.run_local_server, port=0)
        # Save the credentials for the next run
        with open('calendars/creds/token.json', 'w') as token:
            token.write(creds.to_json())

    async def wrapped_request(request):
        return await asyncio.to_thread(request.execute)

    return build('calendar', 'v3', credentials=creds, requestBuilder=HttpRequest)


@app.post("/schedule-task", response_model=EventResponse)
async def schedule_event(event_request: EventRequest):
    try:
        service = await get_calendar_service()

        event = {
            'summary': event_request.summary,
            'start': {
                'dateTime': event_request.start_time.isoformat(),
                'timeZone': event_request.timezone,
            },
            'end': {
                'dateTime': event_request.end_time.isoformat(),
                'timeZone': event_request.timezone,
            },
        }

        created_event = await asyncio.to_thread(
            lambda: service.events().insert(calendarId='primary', body=event).execute()
        )

        return EventResponse(
            id=created_event['id'],
            html_link=created_event['htmlLink'],
            summary=created_event['summary'],
            start=datetime.fromisoformat(created_event['start']['dateTime']),
            end=datetime.fromisoformat(created_event['end']['dateTime'])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



