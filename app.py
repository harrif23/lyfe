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


@app.get("/")
def index():
    return {"message": "Hello, World!"}


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



