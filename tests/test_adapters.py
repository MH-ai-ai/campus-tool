from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock, patch

from campus_guard.adapters import (
    DrcomAdapter,
    GenericPortalAdapter,
    RuijieAdapter,
    SrunAdapter,
    get_adapter,
    guess_adapter_by_url,
)
from campus_guard.adapters.srun_crypto import (
    build_srun_chksum,
    build_srun_info,
    get_hmac_md5,
    get_sha1,
    srun_base64,
    srun_xencode,
)
from campus_guard.models import Config
from campus_guard.universities import UniversityManager, get_university_manager


class TestSrunCrypto(unittest.TestCase):
    def test_sha1_and_hmac(self) -> None:
        self.assertEqual(get_sha1("test"), "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3")
        # hmac-md5(token="123456", key="password")
        res = get_hmac_md5("123456", "password")
        self.assertTrue(len(res) == 32)

    def test_srun_base64_custom_alpha(self) -> None:
        raw = "hello world"
        b64 = srun_base64(raw)
        self.assertTrue(len(b64) > 0)
        # 验证只包含自定义码表字符或等号填充
        for ch in b64:
            self.assertTrue(ch in "LVoJPiCN2R8G90yg+hmFHuacZ1OWMnrsSTXkYpUq/3dlbfKwv6xztjI7DeBE45QA=")

    def test_srun_xencode(self) -> None:
        msg = '{"username":"20230001","password":"pwd"}'
        key = "1479203648"
        encoded = srun_xencode(msg, key)
        self.assertTrue(len(encoded) > 0)

        info_enc = build_srun_info({"username": "test", "password": "123"}, key)
        self.assertTrue(info_enc.startswith("{SRUNBX1}"))

    def test_build_srun_chksum(self) -> None:
        chksum = build_srun_chksum(
            token="token123",
            username="user01",
            hmd5="0123456789abcdef0123456789abcdef",
            ac_id="1",
            ip="10.0.0.2",
            n=200,
            auth_type=1,
            info_encrypted="{SRUNBX1}xxxx",
        )
        self.assertEqual(len(chksum), 40)


class TestAdapters(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = Config.from_mapping({
            "campus_account": "20240001",
            "campus_password": "mypassword",
            "campus_auth_url": "http://10.212.0.1:801/eportal/index.jsp",
            "wlan_ac_ip": "10.212.0.254",
        })

    def test_adapter_registry(self) -> None:
        drcom = get_adapter("drcom")
        self.assertIsInstance(drcom, DrcomAdapter)
        srun = get_adapter("srun")
        self.assertIsInstance(srun, SrunAdapter)
        ruijie = get_adapter("ruijie")
        self.assertIsInstance(ruijie, RuijieAdapter)
        portal = get_adapter("portal")
        self.assertIsInstance(portal, GenericPortalAdapter)
        # 缺省 fallback
        self.assertIsInstance(get_adapter("unknown_proto"), DrcomAdapter)

    def test_drcom_adapter(self) -> None:
        adapter = DrcomAdapter()
        params = adapter.build_auth_params(self.cfg, "10.212.1.2", "aa:bb:cc:dd:ee:ff")
        self.assertEqual(params["user_account"], ",0,20240001")
        self.assertEqual(params["callback"], "dr1003")

        # 指纹评分
        score = adapter.inspect_fingerprint("http://10.212.0.1/eportal/index.jsp?wlanuserip=10.212.1.2")
        self.assertGreater(score, 0.5)

    def test_srun_fingerprint_and_mock(self) -> None:
        adapter = SrunAdapter()
        score = adapter.inspect_fingerprint("http://10.10.0.1/cgi-bin/srun_portal?ac_id=1")
        self.assertGreater(score, 0.8)

        # Mock srun 登录流
        with patch("requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session

            # 1. 模拟 challenge 返回
            challenge_resp = MagicMock()
            challenge_resp.text = '{"challenge": "mock_token_12345"}'
            # 2. 模拟 portal 返回
            portal_resp = MagicMock()
            portal_resp.text = '{"res": "ok"}'

            mock_session.get.return_value = challenge_resp
            mock_session.post.return_value = portal_resp

            ok, msg = adapter.login(self.cfg, "10.10.1.2", "11:22:33:44:55:66")
            self.assertTrue(ok)
            self.assertEqual(msg, "认证成功")

    def test_ruijie_fingerprint(self) -> None:
        adapter = RuijieAdapter()
        score = adapter.inspect_fingerprint("http://192.168.1.1/eportal/InterFace.do?method=login")
        self.assertGreater(score, 0.5)


class TestUniversityManager(unittest.TestCase):
    def setUp(self) -> None:
        self.mgr = UniversityManager()

    def test_yau_is_first(self) -> None:
        profiles = self.mgr.get_all_profiles()
        self.assertTrue(len(profiles) >= 5)
        # 延安大学默认置顶
        self.assertEqual(profiles[0].id, "yau")
        self.assertIn("延安大学", profiles[0].name)
        self.assertEqual(profiles[0].protocol, "drcom")

    def test_fuzzy_search(self) -> None:
        # 中文搜索
        yau_list = self.mgr.search("延安")
        self.assertTrue(any(p.id == "yau" for p in yau_list))

        # 拼音搜索
        thu_list = self.mgr.search("thu")
        self.assertTrue(any(p.id == "tsinghua" for p in thu_list))

        zju_list = self.mgr.search("zhejiang")
        self.assertTrue(any(p.id == "zju" for p in zju_list))

    def test_infer_by_url(self) -> None:
        # 命中清华
        prof, proto = self.mgr.infer_by_url_and_html("https://auth.tsinghua.edu.cn/login", "")
        self.assertIsNotNone(prof)
        self.assertEqual(prof.id, "tsinghua")
        self.assertEqual(proto, "srun")

        # 命中延大
        prof, proto = self.mgr.infer_by_url_and_html("http://10.212.0.1:801/eportal/index.jsp", "")
        self.assertIsNotNone(prof)
        self.assertEqual(prof.id, "yau")
        self.assertEqual(proto, "drcom")

        # 未命中具体高校，但识别为深澜协议通用模板
        prof, proto = self.mgr.infer_by_url_and_html("http://172.16.0.1/cgi-bin/srun_portal", "")
        self.assertEqual(proto, "srun")
        self.assertEqual(prof.id, "generic_srun")


if __name__ == "__main__":
    unittest.main()
