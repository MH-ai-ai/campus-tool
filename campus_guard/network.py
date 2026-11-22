import threading
import time
from datetime import timedelta
from threading import Event, RLock
from typing import Callable

from .auth import campus_login
from .battery import BatteryTracker
from .bot_health import trigger_bot_health_check
from .config import get_config_dict
from .logging_setup import get_logger
from .models import ConnectivitySnapshot, ConnectivityState, NetworkMode
from .proxy_manager import launch_proxy_and_enable
from .system import (
    check_campus_gateway,
    check_internet,
    check_proxy_internet,
    get_local_ip,
    get_primary_interface_info,
    get_wifi_info,
    get_wifi_signal_percent,
    is_clash_tun_ip,
    is_wifi_link_up,
    reconnect_wifi,
)


NotifyCallback = Callable[[str], None]
log = get_logger()


def detect_is_campus_network(ssid: str, gateway_ok: bool, local_ip: str = "") -> bool:
    """智能推断当前网络环境是否属于校园网。"""
    cfg = get_config_dict()
    forced = str(cfg.get("forced_network_mode", "auto")).lower()
    if forced == NetworkMode.CAMPUS.value:
        return True
    if forced == NetworkMode.HOME.value:
        return False

    # 自动识别逻辑
    campus_ssids = [str(s).strip().lower() for s in cfg.get("campus_wifi_ssids", []) if s]
    old_ssid = str(cfg.get("campus_wifi_ssid", "")).strip().lower()
    if old_ssid:
        campus_ssids.append(old_ssid)

    home_ssids = [str(s).strip().lower() for s in cfg.get("trusted_home_ssids", []) if s]

    cleaned_ssid = ssid.strip().lower()

    # 1. 匹配已知家庭/信任网络 SSID
    if any(hs in cleaned_ssid for hs in home_ssids if hs):
        return False

    # 2. 匹配已知校园 SSID
    if any(cs in cleaned_ssid for cs in campus_ssids if cs):
        return True

    # 3. 匹配明确的校园特征关键字 (避免宽泛的 "wifi", "tea" 导致移动热点或家用 Wi-Fi 误判)
    campus_keywords = ("yadx", "yau", "-stu", "_stu", "-tea", "_tea", "campus", "eduroam", ".edu")
    if any(k in cleaned_ssid for k in campus_keywords):
        return True

    # 4. 匹配典型高校私网 IP 网段（如延安大学 10.211.、10.212. 或私网 10.x.x.x）
    ip_clean = local_ip.strip() if local_ip else ""
    if ip_clean and not ip_clean.startswith("127.") and not ip_clean.startswith("169.254."):
        if ip_clean.startswith(("10.211.", "10.212.", "10.200.")):
            return True
        if ip_clean.startswith("10.") and bool(str(cfg.get("campus_account", "")).strip()):
            return True

    # 5. 未知网络时: 网关可达才判定为校园网
    return bool(gateway_ok)



class NetworkMonitor:
    def __init__(self, notify_callback: NotifyCallback, tracker: BatteryTracker) -> None:
        self.notify = notify_callback
        self.tracker = tracker
        self.is_online: bool | None = None
        self.running = True
        self.retry_count = 0
        self.weak_signal_count = 0
        self.aggressive_mode = False
        self.aggressive_start_time: float | None = None
        self.offline_since: float | None = None
        self.last_snapshot: ConnectivitySnapshot | None = None
        self.last_event = "等待首次网络检测"
        self._lock = RLock()
        self._stop_event = Event()
        self._is_probing = False
        self._reconnecting = False
        self._last_reconnect_attempt: float = 0.0
        self._proxy_triggered_this_session: bool = False

    def record_event(self, text: str) -> None:
        """记录外部（如一键联网、手动认证等）触发的网络事件。"""
        with self._lock:
            self.last_event = text

    def effective_check_interval(self, base_interval: int) -> int:
        """自适应动态心跳计算：
        - 稳定在线时心跳拉长至 10 秒（或 max(base_interval, 10)），让后台深度节能睡眠；
        - 掉线或重连中进入高频突发冲刺模式（1~2秒），实现毫秒级快速自愈。
        """
        with self._lock:
            if self.is_online is False or self._reconnecting:
                cfg = get_config_dict()
                return max(1, int(cfg.get("reconnect_fast_retry_seconds", 2)))
            elif self.is_online is True:
                return max(int(base_interval), 10)
            return max(1, int(base_interval))

    def check(self) -> None:
        """主循环检测入口（非阻塞触发，保护主循环不被网络 IO 阻塞）。"""
        if not self.running:
            return

        with self._lock:
            if self._is_probing:
                return
            self._is_probing = True

        # 启动后台探活任务
        threading.Thread(target=self._run_probe_and_handle, daemon=True).start()

    def _run_probe_and_handle(self) -> None:
        try:
            snapshot = self.probe_connectivity()
            online = snapshot.online

            if snapshot.wifi_ok:
                signal_pct = get_wifi_signal_percent()
                if 0 <= signal_pct < 30:
                    self.weak_signal_count += 1
                    log.warning("WiFi 信号弱: %d%% (连续第 %d 次)", signal_pct, self.weak_signal_count)
                    if self.weak_signal_count >= 3:
                        self.notify(
                            f"⚠️ WiFi 信号持续偏弱！\n"
                            f"连续 {self.weak_signal_count} 次检测低于 30%\n"
                            f"当前信号: {signal_pct}%\n"
                            "建议靠近路由器或检查天线"
                        )
                        self.weak_signal_count = 0
                else:
                    self.weak_signal_count = 0

            notify_msg: str | None = None
            should_reconnect = False
            should_launch_proxy = False

            with self._lock:
                self.last_snapshot = snapshot

                if self.is_online is None:
                    self.is_online = online
                    self.last_event = f"初始网络状态: {snapshot.reason}"
                    log.info(
                        "初始网络状态: %s (网卡=%s, 校园网=%s, WiFi=%s, 网关=%s, 直连外网=%s, 代理外网=%s, TUN=%s)",
                        "在线" if online else "离线",
                        snapshot.active_interface,
                        "YES" if snapshot.is_campus_network else "NO",
                        "OK" if snapshot.wifi_ok else "断开",
                        "OK" if snapshot.gateway_ok else "不可达",
                        "OK" if snapshot.internet_direct_ok else "不通",
                        "OK" if snapshot.internet_proxy_ok else "不通",
                        "YES" if snapshot.clash_tun else "NO",
                    )
                    if not online:
                        self.offline_since = time.time()
                        notify_msg = self._format_down_message(snapshot)
                        should_reconnect = True
                    else:
                        should_launch_proxy = True
                # 状态边缘触发：首次由在线变为断开
                elif self.is_online and not online:
                    self.offline_since = time.time()
                    self._proxy_triggered_this_session = False
                    self.last_event = f"网络断开: {snapshot.reason}"
                    log.warning("检测到网络断开（%s），尝试重连...", snapshot.reason)
                    notify_msg = self._format_down_message(snapshot)
                    should_reconnect = True
                    self.is_online = online
                # 状态由离线恢复为在线
                elif not self.is_online and online:
                    self.is_online = True
                    self.retry_count = 0
                    self.last_event = f"网络恢复在线: {snapshot.reason}"
                    should_launch_proxy = True
                # 状态持续离线守护：若未连通且不在重连中，按照冷却周期自动再次触发自愈重连
                elif not online and not self._reconnecting:
                    now = time.time()
                    cooldown = min(15, max(3, 2 + min(self.retry_count * 2, 10)))
                    if now - self._last_reconnect_attempt >= cooldown:
                        log.info("网络仍处于离线状态（%s），掉线探针自动调度自愈重连...", snapshot.reason)
                        should_reconnect = True
                    self.is_online = online
                else:
                    self.is_online = online

            # 退出锁后再执行通知、重连与代理联动调度，杜绝锁内阻塞或自死锁
            if notify_msg:
                self.notify(notify_msg)
            if should_reconnect:
                self._trigger_reconnect()
            if should_launch_proxy:
                self._maybe_launch_proxy_after_online(snapshot)
        except Exception as err:
            log.error("后台网络探测异常: %s", err)
        finally:
            with self._lock:
                self._is_probing = False

    def stop(self) -> None:
        self.running = False
        self._stop_event.set()

    def probe_connectivity(self) -> ConnectivitySnapshot:
        """执行同步探测并生成当前网络连通性快照。"""
        local_ip = get_local_ip()
        if_name, _ip, _mac = get_primary_interface_info()
        wifi_ok = is_wifi_link_up()
        wifi_info = get_wifi_info()

        # 校园网关探活
        gateway_ok = check_campus_gateway() if wifi_ok else False
        internet_direct_ok = check_internet() if (gateway_ok or wifi_ok) else False
        internet_proxy_ok = check_proxy_internet()
        clash_tun = is_clash_tun_ip(local_ip)

        # 智能识别是否处于校园网环境
        is_campus = detect_is_campus_network(wifi_info, gateway_ok, local_ip)

        # 状态判定
        if not wifi_ok:
            state = ConnectivityState.WIFI_DOWN
            reason = "WiFi 链路断开"
        elif internet_direct_ok:
            # 直连外网畅通：系统必然在线，默认网关必然已成功路由外网报文
            state = ConnectivityState.ONLINE
            reason = f"网络在线 ({'校园网' if is_campus else '家庭/免认证网络'})"
            gateway_ok = True
        elif is_campus and not gateway_ok:
            state = ConnectivityState.GATEWAY_DOWN
            reason = "校园网网关不可达"
        elif is_campus and not internet_direct_ok:
            state = ConnectivityState.INTERNET_DOWN
            reason = "直连外网不通，可能需要重新认证校园网"
        elif not internet_direct_ok and not internet_proxy_ok:
            state = ConnectivityState.INTERNET_DOWN
            reason = "外网完全不通"
        else:
            state = ConnectivityState.ONLINE
            reason = "网络在线 (通过代理/TUN)"

        return ConnectivitySnapshot(
            state=state,
            wifi_ok=wifi_ok,
            gateway_ok=gateway_ok,
            internet_direct_ok=internet_direct_ok,
            internet_proxy_ok=internet_proxy_ok,
            local_ip=local_ip,
            wifi_info=wifi_info,
            clash_tun=clash_tun,
            reason=reason,
            is_campus_network=is_campus,
            active_interface=if_name,
        )

    def _get_campus_ssids(self) -> list[str]:
        """按优先级返回校园网 SSID 列表：首选单数配置排在最前，再去重追加列表项。"""
        cfg = get_config_dict()
        result: list[str] = []
        primary = str(cfg.get("campus_wifi_ssid", "")).strip()
        if primary:
            result.append(primary)
        raw_list = cfg.get("campus_wifi_ssids", [])
        if isinstance(raw_list, (list, tuple)):
            for item in raw_list:
                s = str(item).strip()
                if s and s not in result:
                    result.append(s)
        return result

    def _get_home_ssids(self) -> list[str]:
        cfg = get_config_dict()
        ssids = cfg.get("trusted_home_ssids", [])
        return [str(s) for s in ssids if str(s)]

    def _trigger_reconnect(self) -> None:
        with self._lock:
            if self._reconnecting:
                return
            self._reconnecting = True
            self._last_reconnect_attempt = time.time()
        threading.Thread(target=self._async_reconnect_job, daemon=True).start()

    def _async_reconnect_job(self) -> None:
        try:
            self._try_reconnect()
        finally:
            with self._lock:
                self._reconnecting = False

    def _try_reconnect(self) -> None:
        snapshot = self.last_snapshot or self.probe_connectivity()
        is_campus = snapshot.is_campus_network

        self.aggressive_mode = True
        self.aggressive_start_time = time.time()

        # 1. 尝试重连 WiFi：当 WiFi 断开，或网关持续不可达且已连续失败（网卡假死/ARP脱节）时强制重连
        need_force_wifi = (not snapshot.wifi_ok) or (not snapshot.gateway_ok and self.retry_count > 0)
        if not snapshot.wifi_ok or need_force_wifi:
            if is_campus:
                target_ssids = self._get_campus_ssids()
            else:
                merged_ssids: list[str] = []
                for s in self._get_home_ssids() + self._get_campus_ssids():
                    if s and s not in merged_ssids:
                        merged_ssids.append(s)
                target_ssids = merged_ssids
            if not target_ssids:
                snap_ssid = snapshot.wifi_info.split("(", 1)[0].strip() if snapshot.wifi_info else ""
                if snap_ssid and snap_ssid not in ("未连接", "未知"):
                    target_ssids = [snap_ssid]
                else:
                    target_ssids = [""]
            wifi_connected = False
            for ssid in target_ssids:
                log.info("执行 Wi-Fi 自愈连接: %s (force=%s)...", ssid, need_force_wifi)
                if reconnect_wifi(ssid, force=need_force_wifi):
                    wifi_connected = True
                    log.info("Wi-Fi 链路自愈成功: %s", ssid)
                    break
                log.warning("WiFi %s 重连失败，尝试下一个...", ssid)
            if not wifi_connected and not snapshot.wifi_ok:
                self.aggressive_mode = False
                self.notify("❌ WiFi 重连失败，所有 SSID 均不可用")
                return

        # 2. 重新探活当前连通性与网络归属判定
        if self._wait(1):
            return
        new_snap = self.probe_connectivity()
        if new_snap.online:
            with self._lock:
                self.is_online = True
                self.retry_count = 0
                self.last_snapshot = new_snap
                self.last_event = f"网络连接恢复 ({new_snap.reason})"
                self._proxy_triggered_this_session = False
            self.notify(self._format_restore_message(new_snap, 1))
            self.aggressive_mode = False
            trigger_bot_health_check()
            self._maybe_launch_proxy_after_online(new_snap)
            return

        cfg = get_config_dict()
        has_campus_account = bool(str(cfg.get("campus_account", "")).strip())
        is_home = any(hs in new_snap.wifi_info.lower() for hs in self._get_home_ssids() if hs)
        forced_mode = str(cfg.get("forced_network_mode", "auto")).lower()
        should_attempt_campus = (
            new_snap.is_campus_network
            or forced_mode == NetworkMode.CAMPUS.value
            or (forced_mode != NetworkMode.HOME.value and has_campus_account and not is_home)
        )

        if not should_attempt_campus:
            log.info("当前网络未处于校园局域网环境 (或判定为受信任家庭网络)，跳过校园网登录认证")
            self.last_snapshot = new_snap
            self.aggressive_mode = False
            return

        if not new_snap.is_campus_network:
            log.info("当前瞬时网关探活未通，但设备具备校园网配置且非家庭网络，尝试自愈认证重试...")

        # 3. 校园网 Dr.COM 登录重试（含动态嗅探与网关漂移自愈校准）
        max_retries = max(2, int(cfg.get("reconnect_max_retries", 3)))
        verify_delay = int(cfg.get("reconnect_verify_delay_seconds", 2))
        fast_retry_delay = int(cfg.get("reconnect_fast_retry_seconds", 2))

        for attempt in range(1, max_retries + 1):
            log.info("校园网重连尝试 %d/%d", attempt, max_retries)
            success, msg = campus_login()
            if success:
                if self._wait(verify_delay):
                    return
                new_snap = self.probe_connectivity()
                if new_snap.online:
                    with self._lock:
                        self.is_online = True
                        self.retry_count = 0
                        self.last_snapshot = new_snap
                        self.last_event = "网络重连成功"
                        self._proxy_triggered_this_session = False
                    self.tracker.record_reconnect()
                    self.notify(self._format_restore_message(new_snap, attempt))
                    self.aggressive_mode = False
                    trigger_bot_health_check()
                    self._maybe_launch_proxy_after_online(new_snap)
                    return
                log.warning(
                    "重连尝试 %d: 认证已发送但验证失败 (网关=%s, 直连外网=%s)",
                    attempt,
                    "OK" if new_snap.gateway_ok else "不可达",
                    "OK" if new_snap.internet_direct_ok else "不通",
                )
            else:
                # 若初次重试出现无法连接网关或超时，尝试快速嗅探更新校准参数并强力刷新链路
                if attempt == 1 and any(k in msg for k in ("无法连接", "超时", "未配置", "网关", "未获取", "10065")):
                    log.info("重连初次认证未成功 (%s)，正在自动嗅探网络网关进行二次校准...", msg)
                    try:
                        from .auth import auto_detect_portal_config
                        sniff_ok, _, detected = auto_detect_portal_config()
                        if sniff_ok and detected and detected.get("campus_auth_url"):
                            cfg_updated = get_config_dict()
                            cfg_updated["campus_auth_url"] = detected["campus_auth_url"]
                            if detected.get("wlan_ac_ip"):
                                cfg_updated["wlan_ac_ip"] = detected["wlan_ac_ip"]
                            if detected.get("campus_gateway"):
                                cfg_updated["campus_gateway"] = detected["campus_gateway"]
                            from .config import update_runtime_config
                            update_runtime_config(cfg_updated)
                            log.info("自愈重连动态校准完成: %s", detected)
                    except Exception as sniff_err:
                        log.debug("重连自愈嗅探异常: %s", sniff_err)

            if self.aggressive_mode and self.aggressive_start_time:
                elapsed = time.time() - self.aggressive_start_time
                if elapsed < 120:
                    if self._wait(fast_retry_delay):
                        return
                    continue
            self.aggressive_mode = False
            if self._wait(fast_retry_delay):
                return

        self.retry_count += 1
        self.last_event = f"重连失败: 连续失败 {self.retry_count} 次"
        self.notify(f"❌ 校园网重连失败\n已连续失败 {self.retry_count} 次")

    def get_status(self) -> str:
        status = "在线" if self.is_online else "离线"
        snapshot = self.last_snapshot
        if not snapshot:
            return f"网络: {status}\nWiFi: {get_wifi_info()}\n本机 IP: {get_local_ip()}"
        mode_str = "校园网模式" if snapshot.is_campus_network else "家庭/通用模式"
        return (
            f"网络: {status} ({mode_str})\n"
            f"原因: {snapshot.reason}\n"
            f"活动网卡: {snapshot.active_interface}\n"
            f"WiFi: {snapshot.wifi_info}\n"
            f"本机 IP: {snapshot.local_ip}\n"
            f"网关: {'OK' if snapshot.gateway_ok else '不可达'}\n"
            f"直连外网: {'OK' if snapshot.internet_direct_ok else '不通'}\n"
            f"代理外网: {'OK' if snapshot.internet_proxy_ok else '不通'}\n"
            f"Clash/TUN: {'检测到' if snapshot.clash_tun else '未检测到'}"
        )

    def _wait(self, seconds: int | float) -> bool:
        return self._stop_event.wait(seconds)

    def _maybe_launch_proxy_after_online(self, snapshot: ConnectivitySnapshot) -> None:
        """在确认网络在线且开启了代理联动配置时，异步拉起代理客户端并启用系统代理（每会话一次）。"""
        if not snapshot.online:
            return
        cfg = get_config_dict()
        if not bool(cfg.get("auto_start_proxy", False)):
            return

        with self._lock:
            if self._proxy_triggered_this_session:
                return
            self._proxy_triggered_this_session = True

        def _worker() -> None:
            try:
                ok, msg = launch_proxy_and_enable(get_config_dict())
                if ok:
                    self.record_event(f"代理联动: {msg}")
                    log.info("网络连通后代理联动完成: %s", msg)
                else:
                    log.warning("网络连通后代理联动未完成: %s", msg)
                    with self._lock:
                        self._proxy_triggered_this_session = False
            except Exception as err:
                log.warning("代理联动后台执行异常: %s", err)
                with self._lock:
                    self._proxy_triggered_this_session = False

        threading.Thread(target=_worker, daemon=True).start()

    def _format_down_message(self, snapshot: ConnectivitySnapshot) -> str:
        prefix = "⚠️ 校园网断开" if snapshot.is_campus_network else "⚠️ 网络连接断开"
        return (
            f"{prefix}：{snapshot.reason}\n"
            f"网卡: {snapshot.active_interface}\n"
            f"WiFi: {snapshot.wifi_info}\n"
            f"本机 IP: {snapshot.local_ip}\n"
            f"网关: {'OK' if snapshot.gateway_ok else '不可达'}\n"
            f"直连外网: {'OK' if snapshot.internet_direct_ok else '不通'}\n"
            f"代理外网: {'OK' if snapshot.internet_proxy_ok else '不通'}\n"
            f"Clash/TUN: {'检测到' if snapshot.clash_tun else '未检测到'}\n"
            "正在自动重连..."
        )

    def _format_restore_message(self, snapshot: ConnectivitySnapshot, attempt: int) -> str:
        downtime = "未知"
        if self.offline_since:
            downtime = str(timedelta(seconds=int(time.time() - self.offline_since)))
        title = "✅ 校园网重连成功" if snapshot.is_campus_network else "✅ 网络已恢复连接"
        return (
            f"{title}\n"
            f"耗时: {downtime}\n"
            f"尝试次数: {attempt}\n"
            f"网卡: {snapshot.active_interface}\n"
            f"WiFi: {snapshot.wifi_info}\n"
            f"本机 IP: {snapshot.local_ip}\n"
            f"网关: {'OK' if snapshot.gateway_ok else '不可达'}\n"
            f"直连外网: {'OK' if snapshot.internet_direct_ok else '不通'}\n"
            f"代理外网: {'OK' if snapshot.internet_proxy_ok else '不通'}\n"
            f"Clash/TUN: {'检测到' if snapshot.clash_tun else '未检测到'}"
        )

