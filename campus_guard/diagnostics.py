from __future__ import annotations

import json
import platform
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import SENSITIVE_FIELDS, get_config_dict
from .logging_setup import SensitiveDataFilter
from .paths import APP_DIR, LOG_PATH
from .proxy_manager import detect_clash_client
from .system import check_campus_gateway, check_internet, get_local_ip, get_wifi_info
from .version import APP_VERSION


_SENSITIVE_KEY_TOKENS = ("password", "token", "secret", "webhook", "key")


def _is_sensitive_key(key: str) -> bool:
    if key in SENSITIVE_FIELDS:
        return True
    lowered = key.lower()
    return any(tok in lowered for tok in _SENSITIVE_KEY_TOKENS)


def sanitize_config_for_diagnostics(cfg: dict[str, Any]) -> dict[str, Any]:
    """返回脱敏后的配置副本，所有敏感字段仅保留是否已配置标记。"""
    sanitized: dict[str, Any] = {}
    for key, value in cfg.items():
        if _is_sensitive_key(key):
            has_value = bool(str(value).strip()) if value is not None else False
            sanitized[key] = "***已配置***" if has_value else ""
        elif isinstance(value, dict):
            sanitized[key] = sanitize_config_for_diagnostics(value)
        else:
            sanitized[key] = value
    return sanitized


def _safe_call(fn, default: Any):
    try:
        return fn()
    except Exception as err:
        return f"探测异常: {err}"


def collect_diagnostics() -> dict[str, Any]:
    """采集当前本机网络、代理、网关、Wi-Fi 与脱敏配置诊断快照（只读）。"""
    cfg = get_config_dict()
    return {
        "app_version": APP_VERSION,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "platform": platform.platform(),
        "python_version": sys.version.split()[0],
        "wifi": _safe_call(lambda: get_wifi_info(force=True), "未知"),
        "local_ip": _safe_call(get_local_ip, "未知"),
        "gateway_ok": _safe_call(check_campus_gateway, False),
        "internet_ok": _safe_call(check_internet, False),
        "proxy_client": _safe_call(detect_clash_client, {"found": False}),
        "config_summary": sanitize_config_for_diagnostics(cfg),
    }


def format_diagnostics_text(report: dict[str, Any]) -> str:
    """将诊断快照字典格式化为清晰易读的中文纯文本报告。"""
    proxy_info = report.get("proxy_client")
    if isinstance(proxy_info, dict):
        if proxy_info.get("found"):
            proxy_str = (
                f"已发现 ({proxy_info.get('client_name') or 'Clash'}, "
                f"运行中={proxy_info.get('running')}, 端口={proxy_info.get('port')})"
            )
        else:
            proxy_str = "未探测到 Clash 客户端"
    else:
        proxy_str = str(proxy_info)

    cfg = report.get("config_summary") if isinstance(report.get("config_summary"), dict) else {}
    lines = [
        f"=== 安澜 (AnLan) v{report.get('app_version', APP_VERSION)} 网络诊断报告 ===",
        f"生成时间   : {report.get('generated_at', '')}",
        f"运行环境   : {report.get('platform', '')} (Python {report.get('python_version', '')})",
        f"当前 Wi-Fi : {report.get('wifi', '未知')}",
        f"本机 IP    : {report.get('local_ip', '未知')}",
        f"校园网关   : {'可达' if report.get('gateway_ok') is True else report.get('gateway_ok')}",
        f"外网连通   : {'在线' if report.get('internet_ok') is True else report.get('internet_ok')}",
        f"代理客户端 : {proxy_str}",
        "--- 核心配置摘要（已脱敏）---",
        f"网络模式   : {cfg.get('network_mode', '')} | 高校预设={cfg.get('university_id', '')} | 协议={cfg.get('auth_protocol', '')}",
        f"认证地址   : {cfg.get('campus_auth_url', '')} | 网关={cfg.get('campus_gateway', '')}",
        f"自动代理   : auto_start_proxy={cfg.get('auto_start_proxy', False)} | proxy_port={cfg.get('proxy_port', 7897)}",
        f"开机/关闭  : autostart={cfg.get('autostart', True)} | minimized={cfg.get('start_minimized_on_boot', True)} | close_action={cfg.get('close_action', 'ask')}",
        f"消息通道   : telegram_token={cfg.get('telegram_bot_token') or '未配置'} | feishu={cfg.get('feishu_webhook') or '未配置'} | dingtalk={cfg.get('dingtalk_webhook') or '未配置'}",
    ]
    return "\n".join(lines)


def export_diagnostic_bundle(output_dir: Path | None = None) -> Path:
    """生成脱敏后的诊断压缩包 (diagnostics.json + diagnostics.txt + 脱敏日志)，严禁包含 config.json 与密钥文件。"""
    target_dir = Path(output_dir) if output_dir is not None else Path(APP_DIR)
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bundle_path = target_dir / f"anlan_diagnostic_{timestamp}.zip"

    report = collect_diagnostics()
    text_summary = format_diagnostics_text(report)

    if LOG_PATH.exists():
        raw_log = LOG_PATH.read_text(encoding="utf-8", errors="replace")
        sanitized_log = "\n".join(
            SensitiveDataFilter.sanitize(line) for line in raw_log.splitlines()
        )
    else:
        sanitized_log = "暂无运行日志文件 (campus_guard.log)。"

    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("diagnostics.json", json.dumps(report, ensure_ascii=False, indent=2))
        zf.writestr("diagnostics.txt", text_summary)
        zf.writestr("campus_guard.log", sanitized_log)

    return bundle_path
