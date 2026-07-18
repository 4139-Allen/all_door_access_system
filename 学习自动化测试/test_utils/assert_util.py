"""统一断言工具"""

import json


def _format_error(response, message):
    """断言失败时构建详细的错误信息"""
    body = response.json()
    details = [
        f"\n{'=' * 50}",
        f"❌  {message}",
        f"🔷 {response.request.method} {response.request.url}", #response.request.method：获取本次接口请求方式：GET / POST / PUT / DELETE 大写字符串。response.request.url：获取完整请求地址（域名 + 路径 + 拼接参数）。
        f"📥 状态码: {response.status_code}",
        f"📥 完整响应: {json.dumps(body, ensure_ascii=False, indent=2)}",
        f"{'=' * 50}",
    ]
    return "\n".join(details)

def assert_success(response, expected_code=200, expected_msg=None):
    """断言接口返回成功"""
    body = response.json()

    assert body["code"] == 200, _format_error(
        response,f"预期 code={expected_code}, 实际 code={body["code"]}"
    )

    if expected_msg:
        assert expected_msg in body["msg"], _format_error(
            response,
            f" 预期 msg 包含 '{expected_msg}'，实际 msg='{body["msg"]}'"
        )

    return body.get("data")

def assert_failure(response, expected_code=400, expected_msg=None):
    """断言接口返回失败"""
    body =response.json()

    assert body["code"] == expected_code, _format_error(
        response,
        f"预期 code={expected_code}, 实际 code={body["code"]}"
        )

    if expected_msg:
        assert expected_msg in body["msg"], _format_error(
            response,
            f"预期 msg 包含 '{expected_msg}'，实际 msg='{body["msg"]}'"
        )


def print_response(response):
  """打印请求和响应的详细信息，方便调试观察"""
  import json

  print("\n" + "=" * 50)
  print(f"🔷 {response.request.method} {response.request.url}")

  # 请求体
  if response.request.body:
      try:
          body = json.loads(response.request.body)
          print(f"📤 请求: {json.dumps(body, ensure_ascii=False, indent=2)}")
      except:
          print(f"📤 请求: {response.request.body}")

  # 响应
  print(f"📥 状态码: {response.status_code}")
  try:
      body = response.json()
      print(f"📥 响应: {json.dumps(body, ensure_ascii=False, indent=2)}")
  except:
      print(f"📥 响应: {response.text}")

  print("=" * 50)






