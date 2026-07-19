from datetime import datetime


def get_current_context() -> dict:
    now = datetime.now().astimezone()
    seasons = {12: "winter", 1: "winter", 2: "winter", 3: "spring", 4: "spring", 5: "spring", 6: "summer", 7: "summer", 8: "summer", 9: "autumn", 10: "autumn", 11: "autumn"}
    return {"local_datetime": now.isoformat(timespec="minutes"), "timezone": now.tzname() or "local", "season": seasons[now.month]}
