"""统一断言工具"""

def assert_success(response, expected_msg=None):

    body = response.json()

    assert body["code"] == 200, (
        f"\n ❌ 预期 code=200, 实际 code={body["code"]}"
        f"\n msg: {body.get('msg', '')}"
    )


