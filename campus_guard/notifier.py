from __future__ import annotations

import base64
import hashlib
import hmac
import threading
import time
import urllib.parse
from typing import Any

import requests

from .config import get_config_dict
from .logging_setup import get_logger


log = get_logger()


class UnifiedNotifier:
    """统一多平台通知分发中心。
    支持 Telegram Bot、飞书自定义机器人富文本卡片、钉钉加签 Markdown 消息。
    """

    def __init__(self, tg_bot=None) -> None:
        self.tg_bot = tg_bot

    def notify(self, text: str, title: str = "Campus Guard 状态提醒", level: str = "info") -> None:
        """多通道并行异步发送通知。"""
        # 1. 投递 Telegram Bot
        if self.tg_bot:
            try:
                self.tg_bot.send_notification(text)
            except Exception as err:
                log.debug("Telegram 投递异常: %s", err)

        # 2. 后台异步投递国内通道
        threading.Thread(
            target=self._dispatch_domestic,
            args=(text, title, level),
            daemon=True,
        ).start()

    def _dispatch_domestic(self, text: str, title: str, level: str) -> None:
        cfg = get_config_dict()
        feishu_url = str(cfg.get("feishu_webhook_url", "")).strip()
        dingtalk_url = str(cfg.get("dingtalk_webhook_url", "")).strip()
        dingtalk_secret = str(cfg.get("dingtalk_secret", "")).strip()

        if feishu_url:
            self._send_feishu_card(feishu_url, text, title, level)

        if dingtalk_url:
            self._send_dingtalk(dingtalk_url, dingtalk_secret, text, title)

    @staticmethod
    def _send_feishu_card(webhook_url: str, text: str, title: str, level: str) -> bool:
        """向飞书机器人发送高颜值交互式卡片。"""
        template_map = {
            "error": "red",
            "warning": "orange",
            "success": "green",
            "info": "blue",
        }
        # 根据文本特征自适应色彩
        if "⚠️" in text or "断开" in text or "危险" in text:
            color = "red"
        elif "✅" in text or "成功" in text or "恢复" in text:
            color = "green"
        elif "提醒" in text or "弱" in text:
            color = "orange"
        else:
            color = template_map.get(level, "blue")

        # 转换为飞书卡片 Markdown
        lines = text.splitlines()
        content_md = "\n".join(f"- {line}" if line and not line.startswith("─") else line for line in lines)

        card_payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": title},
                    "template": color,
                },
                "elements": [
                    {
                        "tag": "markdown",
                        "content": content_md,
                    },
                    {
                        "tag": "note",
                        "elements": [
                            {
                                "tag": "plain_text",
                                "content": f"Campus Guard 守护中 · {time.strftime('%H:%M:%S')}",
                            }
                        ],
                    },
                ],
            },
        }

        try:
            resp = requests.post(webhook_url, json=card_payload, timeout=6)
            res_json = resp.json()
            if res_json.get("code") == 0:
                log.info("飞书卡片通知发送成功")
                return True
            log.warning("飞书卡片通知返回异常: %s", res_json)
            return False
        except Exception as err:
            log.debug("飞书卡片通知发送失败: %s", err)
            return False

    @staticmethod
    def _send_dingtalk(webhook_url: str, secret: str, text: str, title: str) -> bool:
        """向钉钉机器人发送加签 Markdown 消息。"""
        target_url = webhook_url
        if secret:
            timestamp = str(round(time.time() * 1000))
            secret_enc = secret.encode("utf-8")
            string_to_sign = f"{timestamp}\n{secret}"
            string_to_sign_enc = string_to_sign.encode("utf-8")
            hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
            sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
            sep = "&" if "?" in target_url else "?"
            target_url = f"{target_url}{sep}timestamp={timestamp}&sign={sign}"

        md_payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": f"### {title}\n\n{text}\n\n> Campus Guard · {time.strftime('%H:%M:%S')}",
            },
        }

        try:
            resp = requests.post(target_url, json=md_payload, timeout=6)
            res_json = resp.json()
            if res_json.get("errcode") == 0:
                log.info("钉钉通知发送成功")
                return True
            log.warning("钉钉通知返回异常: %s", res_json)
            return False
        except Exception as err:
            log.debug("钉钉通知发送失败: %s", err)
            return False
