"""
验证码服务
生成、存储、验证短信/邮箱验证码
"""
import uuid
import random
import re
import string
import json
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from database.redis import redis_client
from utils.logger import AppLogger
from core.config import (
    ALIYUN_ACCESS_KEY_ID, ALIYUN_ACCESS_KEY_SECRET, ALIYUN_SMS_SIGN, ALIYUN_SMS_TEMPLATE,
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM
)

logger = AppLogger.get_logger()

# 验证码 Redis key 前缀
CODE_PREFIX = "verify_code:"
# 验证码有效期（秒）
CODE_TTL = 300  # 5 分钟
# 发送频率限制 key 前缀
RATE_PREFIX = "verify_rate:"
# 发送频率限制（秒）
RATE_TTL = 60  # 60 秒内只能发送一次


def generate_code(length: int = 6) -> str:
    """生成数字验证码"""
    return ''.join(random.choices(string.digits, k=length))


def save_code(key: str, code: str):
    """保存验证码到 Redis"""
    if redis_client:
        redis_client.setex(f"{CODE_PREFIX}{key}", CODE_TTL, code)


def verify_code(key: str, code: str) -> bool:
    """验证验证码"""
    if not redis_client:
        return False
    stored = redis_client.get(f"{CODE_PREFIX}{key}")
    if stored and stored == code:
        redis_client.delete(f"{CODE_PREFIX}{key}")
        return True
    return False


def check_rate_limit(key: str) -> bool:
    """检查发送频率限制，返回 True 表示可以发送"""
    import os
    if os.getenv("DISABLE_RATE_LIMIT", "").lower() in ("true", "1", "yes"):
        return True
    if not redis_client:
        return True
    return not redis_client.exists(f"{RATE_PREFIX}{key}")


def set_rate_limit(key: str):
    """设置发送频率限制"""
    if redis_client:
        redis_client.setex(f"{RATE_PREFIX}{key}", RATE_TTL, "1")


def _aliyun_api_request(action: str, params: dict, endpoint: str = "dysmsapi.aliyuncs.com", version: str = "2017-05-25") -> dict:
    """调用阿里云 API（通用签名方法）"""
    import hmac
    import hashlib
    import base64
    import urllib.parse
    import requests as req

    common_params = {
        "AccessKeyId": ALIYUN_ACCESS_KEY_ID,
        "Format": "JSON",
        "RegionId": "cn-hangzhou",
        "SignatureMethod": "HMAC-SHA1",
        "SignatureNonce": str(uuid.uuid4()),
        "SignatureVersion": "1.0",
        "Timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "Action": action,
        "Version": version,
    }
    all_params = {**common_params, **params}

    # 排序 + URL 编码
    sorted_params = sorted(all_params.items())
    query_string = urllib.parse.urlencode(sorted_params)
    string_to_sign = f"GET&{urllib.parse.quote_plus('/')}&{urllib.parse.quote_plus(query_string)}"

    # HMAC-SHA1 签名
    sign = base64.b64encode(
        hmac.new((ALIYUN_ACCESS_KEY_SECRET + "&").encode(), string_to_sign.encode(), hashlib.sha1).digest()
    ).decode()
    all_params["Signature"] = sign

    resp = req.get(f"https://{endpoint}/", params=all_params, timeout=10)
    return resp.json()


def send_sms_code(phone: str) -> tuple[bool, str]:
    """发送短信验证码（调用 SendSmsVerifyCode API）"""
    if not ALIYUN_ACCESS_KEY_ID or not ALIYUN_ACCESS_KEY_SECRET:
        logger.warning("阿里云短信未配置")
        return False, "短信服务未配置"

    if not check_rate_limit(phone):
        return False, "发送过于频繁，请稍后再试"

    try:
        result = _aliyun_api_request("SendSmsVerifyCode", {
            "PhoneNumber": phone,
            "CountryCode": "86",
            "SignName": ALIYUN_SMS_SIGN,
            "TemplateCode": ALIYUN_SMS_TEMPLATE,
            "TemplateParam": '{"code":"##code##","min":"5"}',
            "CodeType": "1",
            "ReturnVerifyCode": "true",
        }, endpoint="dypnsapi.aliyuncs.com", version="2017-05-25")

        if result.get("Code") == "OK":
            set_rate_limit(phone)
            logger.info(f"短信验证码已发送: {phone}")
            return True, "验证码已发送"
        else:
            logger.warning(f"短信发送失败: {result}")
            return False, result.get("Message", "发送失败")

    except Exception as e:
        logger.error(f"短信发送异常: {e}")
        return False, "短信发送失败，请稍后重试"


def check_sms_code(phone: str, code: str) -> bool:
    """核验短信验证码（调用 CheckSmsVerifyCode API）"""
    if not ALIYUN_ACCESS_KEY_ID or not ALIYUN_ACCESS_KEY_SECRET:
        return False

    try:
        result = _aliyun_api_request("CheckSmsVerifyCode", {
            "PhoneNumber": phone,
            "CountryCode": "86",
            "VerifyCode": code,
        }, endpoint="dypnsapi.aliyuncs.com", version="2017-05-25")

        logger.info(f"验证码核验响应: {result}")
        # 尝试从不同位置获取结果
        verify_result = result.get("VerifyResult", "")
        if not verify_result and "Model" in result:
            verify_result = result["Model"].get("VerifyResult", "")
        logger.info(f"验证码核验: phone={phone}, result={verify_result}")
        return verify_result == "PASS"

    except Exception as e:
        logger.error(f"验证码核验异常: {e}")
        return False


def send_email_code(email: str) -> tuple[bool, str]:
    """发送邮箱验证码"""
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("SMTP 邮件未配置")
        return False, "邮件服务未配置"

    if not check_rate_limit(email):
        return False, "发送过于频繁，请稍后再试"

    code = generate_code()

    try:
        msg = MIMEMultipart()
        msg["From"] = SMTP_FROM or SMTP_USER
        msg["To"] = email
        msg["Subject"] = "智能门禁系统 - 验证码"

        body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 400px; margin: 0 auto;">
            <h2 style="color: #409eff;">智能门禁管理系统</h2>
            <p>您的登录验证码是：</p>
            <div style="background: #f5f7fa; padding: 16px; text-align: center; border-radius: 8px; margin: 16px 0;">
                <span style="font-size: 32px; font-weight: bold; color: #303133; letter-spacing: 8px;">{code}</span>
            </div>
            <p style="color: #909399; font-size: 13px;">验证码 5 分钟内有效，请勿泄露给他人。</p>
        </div>
        """
        msg.attach(MIMEText(body, "html", "utf-8"))

        if SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)
        else:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
            server.starttls()

        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_FROM or SMTP_USER, email, msg.as_string())
        server.quit()

        save_code(email, code)
        set_rate_limit(email)
        logger.info(f"邮箱验证码已发送: {email}")
        return True, "验证码已发送"

    except Exception as e:
        logger.error(f"邮件发送异常: {e}")
        return False, "邮件发送失败，请稍后重试"


def send_verify_code_service(target: str) -> tuple[bool, str]:
    """
    发送验证码（自动判断手机号或邮箱）

    参数:
        target: 手机号或邮箱地址

    返回:
        (bool, str): 是否成功、提示信息

    异常:
        ValueError: 手机号格式不正确
    """
    target = target.strip()
    if not target:
        raise ValueError("请输入手机号或邮箱")

    if "@" in target:
        return send_email_code(target)

    if not re.match(r'^1[3-9]\d{9}$', target):
        raise ValueError("请输入正确的手机号")

    return send_sms_code(target)
