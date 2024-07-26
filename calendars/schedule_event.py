import asyncio
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from calendars.gcal_access import get_calendar_service


async def schedule_event(summary, start_time, end_time, tz):
    pst = ZoneInfo(tz)
    service = await get_calendar_service()
    event = {
        'summary': summary,
        'start': {
            'dateTime': start_time.astimezone(pst).isoformat(),
            'timeZone': tz,
        },
        'end': {
            'dateTime': end_time.astimezone(pst).isoformat(),
            'timeZone': tz,
        },
    }
    event = await asyncio.to_thread(
        lambda: service.events().insert(calendarId='primary', body=event).execute()
    )
    return event


async def main():
    time_zone = "America/Los_Angeles"
    start = datetime(2024, 7, 20, 15, 0)
    end = datetime(2024, 7, 20, 15, 25)
    new_event = await schedule_event("Test Event 4", start, end, time_zone)
    print(f"\nNew event scheduled: {new_event['summary']} at {new_event['start']['dateTime']}")


if __name__ == '__main__':
    asyncio.run(main())
