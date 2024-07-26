from datetime import datetime, time, timedelta
import pytz
import asyncio
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from dateutil import parser
import json

from calendars.gcal_access import get_calendar_service


async def get_calendar_blocks(start_date, end_date, timezone='UTC'):
    service = await get_calendar_service()
    # Call the Calendar API to get user's preferred timezone
    calendar_list_entry = await asyncio.to_thread(
        lambda: service.calendarList().get(calendarId='primary').execute()
    )
    timezone = calendar_list_entry['timeZone']
    tz = pytz.timezone(timezone)
    start_date = tz.localize(start_date)
    end_date = tz.localize(end_date)

    events_result = await asyncio.to_thread(
        lambda: service.events().list(
            calendarId='primary',
            timeMin=start_date.isoformat(),
            timeMax=end_date.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
    )
    events = events_result.get('items', [])

    calendar_blocks = {}
    current_date = start_date.date()
    while current_date <= end_date.date():
        day_start = tz.localize(datetime.combine(current_date, time(0, 0)))
        day_end = day_start + timedelta(days=1)

        day_events = [
            {
                'start': parser.parse(event['start'].get('dateTime', event['start'].get('date'))).astimezone(tz),
                'end': parser.parse(event['end'].get('dateTime', event['end'].get('date'))).astimezone(tz),
                'summary': event.get('summary', 'Busy'),
                'event_type': event.get('eventType', 'default')
            }
            for event in events
            if parser.parse(event['start'].get('dateTime', event['start'].get('date'))).astimezone(
                tz).date() == current_date
        ]

        day_blocks = []
        last_time = day_start

        for event in sorted(day_events, key=lambda x: x['start']):
            if last_time < event['start']:
                day_blocks.append({
                    'start': last_time.strftime('%H:%M'),
                    'end': event['start'].strftime('%H:%M'),
                    'is_available': True
                })

            day_blocks.append({
                'start': event['start'].strftime('%H:%M'),
                'end': event['end'].strftime('%H:%M'),
                'is_available': False,
                'event_name': event['summary'],
                'event_type': event['event_type']
            })

            last_time = event['end']

        if last_time < day_end:
            day_blocks.append({
                'start': last_time.strftime('%H:%M'),
                'end': '00:00',
                'is_available': True
            })

        if not day_blocks:
            day_blocks.append({
                'start': '00:00',
                'end': '00:00',
                'is_available': True
            })

        calendar_blocks[current_date.isoformat()] = day_blocks
        current_date += timedelta(days=1)

    result = {
        'timezone': timezone,
        'time_format': '24hr',
        'available_blocks': calendar_blocks
    }

    return json.dumps(result, indent=2)


async def main():
    start_date = datetime(2024, 7, 16)
    end_date = datetime(2024, 7, 21)
    timezone = 'America/Los_Angeles'

    available_slots = await get_calendar_blocks(start_date, end_date, timezone)
    print(available_slots)


if __name__ == '__main__':
    asyncio.run(main())

