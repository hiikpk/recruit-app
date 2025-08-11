from datetime import datetime
from uuid import uuid4

def build_ics(uid_domain, title, start, end, location="", description=""):
    uid = f"{uuid4()}@{uid_domain}"
    def to_dt(dt):
        if dt.tzinfo:
            dt = dt.astimezone(tz=None).replace(tzinfo=None)
        return dt.strftime('%Y%m%dT%H%M%SZ')
    ics = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//RecruitMVP//Interview//JP
BEGIN:VEVENT
UID:{uid}
DTSTAMP:{to_dt(datetime.utcnow())}
DTSTART:{to_dt(start)}
DTEND:{to_dt(end)}
SUMMARY:{title}
LOCATION:{location}
DESCRIPTION:{description}
END:VEVENT
END:VCALENDAR"""
    return ics