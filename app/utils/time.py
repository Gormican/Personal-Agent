from datetime import datetime, time, timedelta

def blocks_from_events(events):
    # events: list of tuples (start,end,title) in local time strings "HH:MM"
    parsed = []
    for s,e,t in events:
        sh, sm = map(int, s.split(":")); eh, em = map(int, e.split(":"))
        parsed.append((time(sh,sm), time(eh,em), t))
    parsed.sort(key=lambda x: x[0])
    # compute free gaps > 30 min between 07:00-22:00
    day_start, day_end = time(7,0), time(22,0)
    free = []
    current = day_start
    for s,e,_ in parsed:
        if (datetime.combine(datetime.today(), s) - datetime.combine(datetime.today(), current)).seconds >= 30*60:
            free.append((current, s))
        current = max(current, e)
    if (datetime.combine(datetime.today(), day_end) - datetime.combine(datetime.today(), current)).seconds >= 30*60:
        free.append((current, day_end))
    def fmt(t): return f"{t.hour:02d}:{t.minute:02d}"
    return [f"{fmt(a)}–{fmt(b)}" for a,b in free]
