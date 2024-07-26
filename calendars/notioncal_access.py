# https://www.notion.so/c216f2e6dd6e4beabc83bbe5b1a7de36?v=50d8a5d9981a4f559e861746904cba1e&pvs=4
# https://www.notion.so/4224be63c6504eadb8c66ab241fcfd46?v=11f52afc2a1a419bb89d6a44a1562370&pvs=4

import os
from typing import List, Dict, Any
import asyncio
from notion_client import Client, AsyncClient
from datetime import datetime
import json
from dotenv import load_dotenv
load_dotenv()


# def get_calendar_events(database_id, notion_token):
#     # Initialize the Notion client
#     notion = Client(auth=notion_token)
#
#     # Query the database
#     response = notion.databases.query(
#         database_id=database_id,
#         sorts=[
#             {
#                 "property": "Date",
#                 "direction": "ascending"
#             }
#         ]
#     )
#
#     # Process and format the results
#     events = []
#     for page in response['results']:
#         properties = page['properties']
#
#         # Extract start and end timestamps
#         date_property = properties.get('Date', {}).get('date', {})
#         start = date_property.get('start')
#         end = date_property.get('end')
#
#         # Convert timestamps to datetime objects
#         start_dt = datetime.fromisoformat(start) if start else None
#         end_dt = datetime.fromisoformat(end) if end else None
#
#         # Extract other properties
#         name = properties.get('Name', {}).get('title', [{}])[0].get('plain_text', '')
#         is_complete = properties.get('Complete', {}).get('checkbox', '')
#         hours_spent = properties.get('Hours spent', {}).get('formula', '').get('number', '')
#         day_of_week = properties.get('Day of Week', {}).get('formula', '').get('string', '')
#         projects = properties.get('Projects', {}).get('select', {}).get('name', '')
#         hours_spent = properties.get('Hours spent', {}).get('number', 0)
#
#         # Calculate day of week and week number
#         day_of_week = start_dt.strftime('%A') if start_dt else None
#         week_number = start_dt.isocalendar()[1] if start_dt else None
#
#         event = {
#             'name': name,
#             'start': start,
#             'end': end,
#             'projects': projects,
#             'day_of_week': day_of_week,
#             'week_number': week_number,
#             'hours_spent': hours_spent
#         }
#
#         events.append(event)
#
#     # Convert to JSON
#     events_json = json.dumps(events, indent=2)
#     return events_json
#
#
# # Example usage
# database_id = '4224be63c6504eadb8c66ab241fcfd46'
# notion_token = os.getenv("NOTION_API_KEY")
#
# calendar_events = get_calendar_events(database_id, notion_token)
# print(calendar_events)


async def get_calendar_events(database_id: str, notion_token: str) -> str:
    async def fetch_project_title(project_id: str) -> str:
        try:
            project_page = await notion.pages.retrieve(page_id=project_id)
            return project_page['properties']['Name']['title'][0]['plain_text']
        except Exception as e:
            print(f"Error fetching project title for ID {project_id}: {str(e)}")
            return "Unknown Project"

    async def process_page(page: Dict[str, Any]) -> Dict[str, Any]:
        properties = page['properties']

        date_property = properties.get('Date', {}).get('date', {})
        start = date_property.get('start')
        end = date_property.get('end')

        start_dt = datetime.fromisoformat(start) if start else None
        end_dt = datetime.fromisoformat(end) if end else None

        name = properties.get('Name', {}).get('title', [{}])[0].get('plain_text', '')
        is_complete = properties.get('Complete', {}).get('checkbox', '')
        hours_spent = properties.get('Hours spent', {}).get('formula', '').get('number', '')
        day_of_week = properties.get('Day of Week', {}).get('formula', '').get('string', '')

        project_relation = properties.get('Projects', {}).get('relation', [])
        project_id = project_relation[0]['id'] if project_relation else None
        project_title = await fetch_project_title(project_id) if project_id else "No Project"

        # day_of_week = start_dt.strftime('%A') if start_dt else None
        week_number = start_dt.isocalendar()[1] if start_dt else None

        return {
            'name': name,
            'start': start,
            'end': end,
            'day_of_week': day_of_week,
            'is_complete': is_complete,
            'project': project_title,
            'week_number': week_number,
            'hours_spent': hours_spent
        }

    try:
        notion = AsyncClient(auth=notion_token)

        events: List[Dict[str, Any]] = []
        has_more = True
        next_cursor = None

        while has_more:
            response = await notion.databases.query(
                database_id=database_id,
                start_cursor=next_cursor,
                sorts=[
                    {
                        "property": "Date",
                        "direction": "ascending"
                    }
                ]
            )

            pages = response['results']
            events.extend(await asyncio.gather(*[process_page(page) for page in pages]))

            has_more = response['has_more']
            next_cursor = response['next_cursor']

        events_json = json.dumps(events, indent=2)
        return events_json

    except Exception as e:
        error_message = f"An error occurred while fetching calendar events: {str(e)}"
        print(error_message)
        return json.dumps({"error": error_message})

    finally:
        await notion.aclose()


# Example usage
async def main():
    database_id = '4224be63c6504eadb8c66ab241fcfd46'
    notion_token = os.getenv("NOTION_API_KEY")

    calendar_events = await get_calendar_events(database_id, notion_token)
    print(calendar_events)


# Run the async function
if __name__ == "__main__":
    asyncio.run(main())
