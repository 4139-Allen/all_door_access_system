import requests, urllib.parse

s = requests.Session()
login = s.post("http://127.0.0.1:8000/api/auth/login", json={"username": "admin", "password": "123456"})
# token 在响应头的 Authorization 字段
token = login.headers.get("authorization", "").replace("Bearer ", "")
print("Token OK:", token[:30])
if not token:
    print("No token found!")
    print("Response:", login.text)
    print("Headers:", dict(login.headers))
    exit(1)

headers = {"Authorization": f"Bearer {token}"}

# 不带筛选
r1 = s.get("http://127.0.0.1:8000/api/door-logs?page=1&size=10", headers=headers)
d1 = r1.json()
print("无筛选: total=%s, list长度=%s" % (d1["data"]["total"], len(d1["data"]["list"])))

# 筛选状态=成功
st = urllib.parse.quote("成功")
r2 = s.get("http://127.0.0.1:8000/api/door-logs?page=1&size=10&status=" + st, headers=headers)
d2 = r2.json()
print("筛选status=成功: total=%s, list长度=%s" % (d2["data"]["total"], len(d2["data"]["list"])))

# 筛选状态=失败
st2 = urllib.parse.quote("失败")
r3 = s.get("http://127.0.0.1:8000/api/door-logs?page=1&size=10&status=" + st2, headers=headers)
d3 = r3.json()
print("筛选status=失败: total=%s, list长度=%s" % (d3["data"]["total"], len(d3["data"]["list"])))
