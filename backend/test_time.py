import requests

s = requests.Session()
login = s.post("http://127.0.0.1:8000/api/auth/login",
    json={"username": "admin", "password": "123456"})
token = login.headers.get("authorization", "").replace("Bearer ", "")
print("Token:", token[:20] if token else "无")
if not token:
    exit(1)

headers = {"Authorization": "Bearer " + token}

# 开始时间大于结束时间（UTC+8：2026-07-25 00:00:00 到 2026-07-24 00:00:00）
r = s.get(
    "http://127.0.0.1:8000/api/door-logs"
    "?start_time=2026-07-25+00:00:00"
    "&end_time=2026-07-24+00:00:00"
    "&page=1&size=10",
    headers=headers
)
print("状态码:", r.status_code)
body = r.json()
print("code:", body.get("code"))
print("msg:", body.get("msg"))
