from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from typing import Any
from urllib.parse import urlparse

import requests

from .adapters import guess_adapter_by_url
from .logging_setup import get_logger
from .paths import UNIVERSITIES_CACHE_PATH

log = get_logger()

# 远程高校规则库热更新地址 (GitHub / Gitee 镜像)
_REMOTE_RULE_URL = "https://raw.githubusercontent.com/MH-ai-ai/campus-tool/main/data/universities.json"


@dataclass
class UniversityProfile:
    id: str
    name: str
    pinyin: str
    protocol: str
    auth_url: str
    gateway: str = ""
    ac_ip: str = ""
    wifi_ssids: list[str] = field(default_factory=list)
    domain_keywords: list[str] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UniversityProfile":
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            pinyin=str(data.get("pinyin", "")),
            protocol=str(data.get("protocol", "drcom")),
            auth_url=str(data.get("auth_url", "")),
            gateway=str(data.get("gateway", "")),
            ac_ip=str(data.get("ac_ip", "")),
            wifi_ssids=list(data.get("wifi_ssids", [])),
            domain_keywords=list(data.get("domain_keywords", [])),
            description=str(data.get("description", "")),
        )


# 内置离线高校与协议规则库（延安大学默认置顶，保证完全向后兼容）
_DEFAULT_PROFILES: list[dict[str, Any]] = [
    {
        "id": "yau",
        "name": "延安大学 (默认 · Dr.COM)",
        "pinyin": "yanandaxue yau ydy yadx",
        "protocol": "drcom",
        "auth_url": "http://10.200.84.3:801/eportal/portal/login",
        "gateway": "10.211.0.1",
        "ac_ip": "10.255.250.74",
        "wifi_ssids": ["YADX-STU", "YADX-TEA", "YAU", "YAU_5G", "i-YAU"],
        "domain_keywords": ["10.200.84.3", "10.211.", "10.212.", "yadx", "yau.edu.cn"],
        "description": "延安大学新校区/杨家岭校区/萃园 Dr.COM ePortal 校园网 (YADX-STU / YADX-TEA)",
    },
    {
        "id": "generic_drcom",
        "name": "城市热点通用模板 (Dr.COM Web)",
        "pinyin": "chengshiretian drcom generic",
        "protocol": "drcom",
        "auth_url": "http://10.0.0.1/eportal/index.jsp",
        "gateway": "10.0.0.1",
        "ac_ip": "",
        "wifi_ssids": [],
        "domain_keywords": ["drcom", "dr1003", "dr1002"],
        "description": "国内数百所高校通用的 Dr.COM Web / ePortal 认证",
    },
    {
        "id": "generic_srun",
        "name": "深澜软件通用模板 (Srun 4000 / Portal)",
        "pinyin": "shenlan srun generic",
        "protocol": "srun",
        "auth_url": "http://10.0.0.1/cgi-bin/srun_portal",
        "gateway": "10.0.0.1",
        "ac_ip": "1",
        "wifi_ssids": [],
        "domain_keywords": ["srun", "srun_portal", "get_challenge"],
        "description": "清北浙大等近半数主流高校采用的深澜 Srun 认证系统",
    },
    {
        "id": "generic_ruijie",
        "name": "锐捷网络通用模板 (Ruijie ePortal / SAM)",
        "pinyin": "ruijie sam generic",
        "protocol": "ruijie",
        "auth_url": "http://192.168.1.1/eportal/InterFace.do?method=login",
        "gateway": "192.168.1.1",
        "ac_ip": "",
        "wifi_ssids": ["Ruijie", "RG-"],
        "domain_keywords": ["ruijie", "interface.do", "sam"],
        "description": "国内工科和多类综合院校采用的锐捷认证网关",
    },
    {
        "id": "generic_portal",
        "name": "通用 Web Portal 表单认证 (其他高校)",
        "pinyin": "tongyong portal web form",
        "protocol": "portal",
        "auth_url": "http://10.0.0.1/login",
        "gateway": "10.0.0.1",
        "ac_ip": "",
        "wifi_ssids": [],
        "domain_keywords": ["login", "portal"],
        "description": "基于标准 HTTP POST 表单提交的通用高校网页认证",
    },
    {
        "id": "tsinghua",
        "name": "清华大学 (深澜 Srun)",
        "pinyin": "qinghuadaxue thu th",
        "protocol": "srun",
        "auth_url": "https://auth.tsinghua.edu.cn/cgi-bin/srun_portal",
        "gateway": "166.111.4.1",
        "ac_ip": "1",
        "wifi_ssids": ["Tsinghua", "Tsinghua-Secure"],
        "domain_keywords": ["tsinghua.edu.cn", "auth.tsinghua"],
        "description": "清华大学深澜 Srun Web 认证",
    },
    {
        "id": "zju",
        "name": "浙江大学 (深澜 Srun)",
        "pinyin": "zhejiangdaxue zju zd",
        "protocol": "srun",
        "auth_url": "http://10.10.0.1/cgi-bin/srun_portal",
        "gateway": "10.10.0.1",
        "ac_ip": "1",
        "wifi_ssids": ["ZJUWLAN", "ZJUWLAN-Secure"],
        "domain_keywords": ["zju.edu.cn", "10.10.0.1"],
        "description": "浙江大学深澜校园网 Portal 认证",
    },
    {
        "id": "bupt",
        "name": "北京邮电大学 (深澜 Srun)",
        "pinyin": "beijingyoudiandaxue bupt byd",
        "protocol": "srun",
        "auth_url": "http://10.3.8.211/cgi-bin/srun_portal",
        "gateway": "10.3.8.211",
        "ac_ip": "1",
        "wifi_ssids": ["BUPT-portal", "BUPT-mobile"],
        "domain_keywords": ["bupt.edu.cn", "10.3.8.211"],
        "description": "北京邮电大学深澜 Web Portal 认证",
    },
    {
        "id": "jlu",
        "name": "吉林大学 (城市热点 Dr.COM)",
        "pinyin": "jilindaxue jlu jd",
        "protocol": "drcom",
        "auth_url": "http://10.100.61.3/eportal/index.jsp",
        "gateway": "10.100.61.1",
        "ac_ip": "",
        "wifi_ssids": ["JLU.NET"],
        "domain_keywords": ["jlu.edu.cn", "10.100.61."],
        "description": "吉林大学 Dr.COM 认证体系",
    },
    {
        "id": "szu",
        "name": "深圳大学 (深澜 Srun)",
        "pinyin": "shenzhendaxue szu sd",
        "protocol": "srun",
        "auth_url": "https://auth.szu.edu.cn/cgi-bin/srun_portal",
        "gateway": "172.30.255.42",
        "ac_ip": "1",
        "wifi_ssids": ["SZU-WLAN"],
        "domain_keywords": ["szu.edu.cn"],
        "description": "深圳大学校园网深澜认证",
    },
    {
        "id": "uestc",
        "name": "电子科技大学 (深澜 Srun)",
        "pinyin": "dianzikedaxue uestc cdkj",
        "protocol": "srun",
        "auth_url": "http://10.254.1.2/cgi-bin/srun_portal",
        "gateway": "10.254.1.2",
        "ac_ip": "1",
        "wifi_ssids": ["UESTC-WiFi"],
        "domain_keywords": ["uestc.edu.cn", "10.254.1.2"],
        "description": "电子科技大学校园网 Portal",
    },
]


class UniversityManager:
    """高校校园网模板规则库管理器，支持离线全量加载、模糊搜索与云端静默热更新。"""

    def __init__(self) -> None:
        self._profiles: dict[str, UniversityProfile] = {}
        self.reload()

    def reload(self) -> None:
        """从内置默认数据与本地持久化缓存加载高校名录。"""
        self._profiles.clear()
        
        # 1. 先载入内置全量数据
        for item in _DEFAULT_PROFILES:
            prof = UniversityProfile.from_dict(item)
            self._profiles[prof.id] = prof

        # 2. 如果存在本地热更新文件，合并覆盖
        if UNIVERSITIES_CACHE_PATH.exists():
            try:
                content = UNIVERSITIES_CACHE_PATH.read_text(encoding="utf-8")
                remote_data = json.loads(content)
                if isinstance(remote_data, list):
                    for item in remote_data:
                        prof = UniversityProfile.from_dict(item)
                        self._profiles[prof.id] = prof
                log.info("已成功加载本地高校热更新规则库: %d 所高校", len(self._profiles))
            except Exception as err:
                log.warning("解析本地高校规则库缓存失败，降级使用内置规则: %s", err)

    def get_all_profiles(self) -> list[UniversityProfile]:
        """获取所有已收录高校模板（延安大学默认置顶）。"""
        profiles = list(self._profiles.values())
        # 保证延安大学排在首位
        yau = self._profiles.get("yau")
        if yau and yau in profiles:
            profiles.remove(yau)
            profiles.insert(0, yau)
        return profiles

    def get_profile(self, uni_id: str) -> UniversityProfile | None:
        return self._profiles.get(uni_id)

    def search(self, keyword: str) -> list[UniversityProfile]:
        """按中文名称、拼音首字母缩写或关键字模糊搜索高校。"""
        kw = keyword.strip().lower()
        if not kw:
            return self.get_all_profiles()

        results: list[UniversityProfile] = []
        for prof in self.get_all_profiles():
            if (
                kw in prof.name.lower()
                or kw in prof.pinyin.lower()
                or kw in prof.id.lower()
                or kw in prof.protocol.lower()
            ):
                results.append(prof)
        return results

    def infer_by_url_and_html(
        self,
        url: str,
        html: str = "",
    ) -> tuple[UniversityProfile | None, str]:
        """根据 Captive 探针捕获到的重定向 URL 和 HTML 内容，智能反推归属高校及协议。
        返回 (匹配到的高校模板或 None, 推荐协议名称)。
        """
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        url_lower = url.lower()

        # 1. 尝试从域名/IP关键字精确匹配具体高校（排除通用兜底模板）
        for prof in self.get_all_profiles():
            if prof.id.startswith("generic_"):
                continue
            for kw in prof.domain_keywords:
                if kw and (kw.lower() in host or kw.lower() in url_lower):
                    log.info("特征命中高校: %s (协议: %s)", prof.name, prof.protocol)
                    return prof, prof.protocol

        # 2. 如果未命中具体高校，使用适配器指纹引擎判定通用协议
        adapter = guess_adapter_by_url(url, html)
        protocol = adapter.name

        # 匹配对应的通用模板
        generic_map = {
            "drcom": "generic_drcom",
            "srun": "generic_srun",
            "ruijie": "generic_ruijie",
            "portal": "generic_portal",
        }
        gen_id = generic_map.get(protocol, "generic_portal")
        return self._profiles.get(gen_id), protocol

    def sync_from_remote(self, timeout: int = 5) -> tuple[bool, str]:
        """从远程仓库同步更新高校规则库并持久化。"""
        try:
            session = requests.Session()
            session.trust_env = False
            resp = session.get(_REMOTE_RULE_URL, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    UNIVERSITIES_CACHE_PATH.write_text(
                        json.dumps(data, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                    self.reload()
                    return True, f"规则库已更新，共加载 {len(self._profiles)} 所高校"
                return False, "远程规则库数据格式不合法"
            return False, f"远程响应异常 (HTTP {resp.status_code})"
        except Exception as err:
            return False, f"同步失败: {err}"


# 全局单例
_uni_manager = UniversityManager()


def get_university_manager() -> UniversityManager:
    return _uni_manager
