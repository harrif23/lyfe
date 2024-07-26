from app import (
    TextInput,
    EventRequest,
    generate_tasks,
    get_weekly_goal,
    get_weekly_tasks,
    get_tasks,
    get_project,
    schedule_event
)
from datetime import datetime

import asyncio

event_data = {
        "summary": "Team Meeting",
        "start_time": datetime.fromisoformat("2024-07-20T19:00:00"),
        "end_time": datetime.fromisoformat("2024-07-20T19:30:00"),
        "timezone": "America/Los_Angeles"
    }

if __name__ == "__main__":
    # result = asyncio.run(generate_tasks(TextInput(text="Create a health app", user_id=1)))
    # result = asyncio.run(get_project(114))
    # result = asyncio.run(get_tasks(114))
    # result = asyncio.run(get_weekly_goal(114))
    # result = asyncio.run(get_weekly_tasks(114, 2))
    result = asyncio.run(schedule_event(EventRequest(**event_data)))

    print(result)


