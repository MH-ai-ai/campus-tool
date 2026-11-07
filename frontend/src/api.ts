export interface BatteryInfo {
  has_battery: boolean;
  percent: number;
  plugged: boolean;
  charging?: boolean;
  status_text: string;
}

export interface SystemInfo {
  uptime_seconds: number;
  memory: string;
  disk_free_gb: number;
}

export interface TelegramState {
  configured: boolean;
  user_id: string;
  is_running: boolean;
}

export interface StateData {
  online: boolean | null;
  is_campus: boolean;
  wifi: string;
  ip: string;
  mac: string;
  gateway: string;
  gateway_ok: boolean;
  clash_tun: boolean;
  active_interface: string;
  battery: BatteryInfo;
  system: SystemInfo;
  last_event: string;
  university_name: string;
  auth_protocol: string;
  campus_account: string;
  telegram?: TelegramState;
}

export interface UniversityItem {
  id: string;
  name: string;
  protocol: string;
  auth_url: string;
  gateway: string;
  wifi_ssids: string[];
}

export interface ApiResponse<T = any> {
  success: boolean;
  message: string;
  detected?: Record<string, any>;
  data?: T;
}

declare global {
  interface Window {
    pywebview?: {
      api: Record<string, (...args: any[]) => Promise<any>>;
    };
  }
}

// 模拟回退数据（用于独立浏览器预览或开发调试）
const MOCK_STATE: StateData = {
  online: true,
  is_campus: true,
  wifi: "YADX-STU (92%)",
  ip: "10.200.84.15",
  mac: "3c7c3f8899aa",
  gateway: "10.200.84.3",
  gateway_ok: true,
  clash_tun: false,
  active_interface: "Intel Wi-Fi 6E AX211",
  battery: {
    has_battery: true,
    percent: 94,
    plugged: true,
    status_text: "交流供电中 (已充满)",
  },
  system: {
    uptime_seconds: 3720,
    memory: "18.4 MB (常驻轻量)",
    disk_free_gb: 128.5,
  },
  last_event: "校园网认证成功，网络持续连通",
  university_name: "延安大学 (默认 · Dr.COM)",
  auth_protocol: "DRCOM",
  campus_account: "20240901001",
};

function withTimeout<T>(promise: Promise<T>, ms: number, errorMsg: string): Promise<T> {
  let timer: any;
  const timeoutPromise = new Promise<T>((_, reject) => {
    timer = setTimeout(() => {
      reject(new Error(errorMsg));
    }, ms);
  });
  return Promise.race([promise, timeoutPromise]).finally(() => {
    clearTimeout(timer);
  });
}

export const api = {
  async getState(): Promise<StateData> {
    if (window.pywebview?.api?.get_state) {
      return await withTimeout(window.pywebview.api.get_state(), 4000, "获取系统状态超时");
    }
    return MOCK_STATE;
  },

  async getConfig(): Promise<Record<string, any>> {
    if (window.pywebview?.api?.get_config) {
      return await withTimeout(window.pywebview.api.get_config(), 4000, "读取配置超时");
    }
    return {
      university_name: "延安大学 (默认 · Dr.COM)",
      auth_protocol: "drcom",
      campus_account: "20240901001",
      campus_password: "••••••••",
      campus_auth_url: "http://10.200.84.3:801/eportal/index.jsp",
      campus_gateway: "10.200.84.3",
      campus_wifi_ssids: ["YADX-STU", "YAU-WiFi"],
      trusted_home_ssids: ["Home_5G"],
      forced_network_mode: "auto",
      network_check_interval_seconds: 2,
      check_interval_seconds: 5,
      autostart: true,
      battery_warning_thresholds: [50, 30, 20],
      auto_shutdown_threshold: 20,
      auto_shutdown_delay: 60,
      feishu_webhook_url: "",
      dingtalk_webhook_url: "",
    };
  },

  async saveConfig(cfg: Record<string, any>): Promise<ApiResponse> {
    if (window.pywebview?.api?.save_config) {
      return await withTimeout(window.pywebview.api.save_config(cfg), 4000, "保存配置超时");
    }
    return { success: true, message: "模拟保存配置成功" };
  },

  async reconnectWifi(): Promise<ApiResponse> {
    if (window.pywebview?.api?.reconnect_wifi) {
      return await withTimeout(
        window.pywebview.api.reconnect_wifi(),
        6000,
        "重连 Wi-Fi 请求超时，请检查网卡开关"
      );
    }
    return { success: true, message: "已向 Windows 发送重新连接 Wi-Fi 指令" };
  },

  async authCampus(): Promise<ApiResponse> {
    if (window.pywebview?.api?.auth_campus) {
      return await withTimeout(
        window.pywebview.api.auth_campus(),
        7000,
        "认证网关响应超时，请确认 Wi-Fi 信号良好"
      );
    }
    return { success: true, message: "认证成功：账号已上线" };
  },

  async logoutCampus(): Promise<ApiResponse> {
    if (window.pywebview?.api?.logout_campus) {
      return await withTimeout(
        window.pywebview.api.logout_campus(),
        5000,
        "注销下线请求超时"
      );
    }
    return { success: true, message: "注销成功：已安全下线" };
  },

  async autoSniff(): Promise<ApiResponse> {
    if (window.pywebview?.api?.auto_sniff) {
      return await withTimeout(
        window.pywebview.api.auto_sniff(),
        6000,
        "嗅探网关超时：未捕获到重定向，请确认已连入校园 Wi-Fi"
      );
    }
    return {
      success: true,
      message: "成功捕获 Captive Portal 302 重定向",
      detected: {
        campus_auth_url: "http://10.200.84.3:801/eportal/index.jsp",
        campus_gateway: "10.200.84.3",
        campus_wifi_ssid: "YADX-STU",
        auth_protocol: "drcom",
        university_name: "延安大学",
      },
    };
  },

  async quickSetup(payload: Record<string, any>): Promise<ApiResponse> {
    if (window.pywebview?.api?.quick_setup) {
      return await withTimeout(
        window.pywebview.api.quick_setup(payload),
        8000,
        "向导设置提交超时"
      );
    }
    return { success: true, message: "一键极速打通成功！网络已正常连通" };
  },

  async quickConnect(account: string = "", password: string = ""): Promise<ApiResponse> {
    if (window.pywebview?.api?.quick_connect) {
      return await withTimeout(
        window.pywebview.api.quick_connect(account, password),
        8000,
        "一键极速联网超时：认证网关无响应，请检查校园 Wi-Fi 连接"
      );
    }
    return {
      success: true,
      message: "认证成功：校园网已连通并开启后台自愈守护",
      detected: {
        university_name: "延安大学",
        auth_protocol: "drcom",
        campus_auth_url: "http://10.200.84.3:801/eportal/index.jsp",
      },
    };
  },

  async searchUniversities(keyword: string): Promise<UniversityItem[]> {
    if (window.pywebview?.api?.search_universities) {
      return await withTimeout(window.pywebview.api.search_universities(keyword), 3000, "检索高校库超时");
    }
    return [
      {
        id: "yanan_university",
        name: "延安大学 (默认 · Dr.COM 认证)",
        protocol: "drcom",
        auth_url: "http://10.200.84.3:801/eportal/index.jsp",
        gateway: "10.200.84.3",
        wifi_ssids: ["YADX-STU", "YAU-WIFI"],
      },
      {
        id: "tsinghua",
        name: "清华大学 (深澜 Srun 4000)",
        protocol: "srun",
        auth_url: "http://10.10.0.1/cgi-bin/srun_portal",
        gateway: "10.10.0.1",
        wifi_ssids: ["Tsinghua-Secure"],
      },
      {
        id: "zju",
        name: "浙江大学 (Web Portal)",
        protocol: "portal",
        auth_url: "http://10.5.1.1/portal",
        gateway: "10.5.1.1",
        wifi_ssids: ["ZJU-WiFi"],
      },
    ];
  },

  async getLogs(): Promise<string[]> {
    if (window.pywebview?.api?.get_logs) {
      return await window.pywebview.api.get_logs();
    }
    return [
      "[INFO] 监控循环启动: 电池检查=5s, 网络检查=2s",
      "[INFO] Wi-Fi 链路已就绪: YADX-STU, 信号强度 92%",
      "[INFO] 校园网网关 10.200.84.3 探测畅通",
      "[INFO] 延安大学 Dr.COM 登录认证成功: 20240901001",
      "[INFO] 内存工作集优化完成，当前物理内存常驻 18.4MB",
    ];
  },

  async clearLogs(): Promise<ApiResponse> {
    if (window.pywebview?.api?.clear_logs) {
      return await window.pywebview.api.clear_logs();
    }
    return { success: true, message: "日志已清空" };
  },

  async exportLogs(): Promise<ApiResponse<{ content?: string; path?: string }>> {
    if (window.pywebview?.api?.export_logs) {
      return await window.pywebview.api.export_logs();
    }
    return {
      success: true,
      message: "日志文件就绪",
      data: {
        content: "[INFO] 模拟日志导出测试\n[INFO] 运行状态良好",
        path: "C:\\Users\\User\\AppData\\Roaming\\CampusGuard\\campus_guard.log",
      },
    };
  },

  async openLogFolder(): Promise<ApiResponse> {
    if (window.pywebview?.api?.open_log_folder) {
      return await window.pywebview.api.open_log_folder();
    }
    return { success: true, message: "已在资源管理器中打开日志目录" };
  },

  async lockScreen(): Promise<ApiResponse> {
    if (window.pywebview?.api?.lock_screen) {
      return await window.pywebview.api.lock_screen();
    }
    return { success: true, message: "已触发系统锁屏" };
  },

  async takeScreenshot(): Promise<ApiResponse> {
    if (window.pywebview?.api?.take_screenshot) {
      return await window.pywebview.api.take_screenshot();
    }
    return { success: true, message: "桌面截图已成功捕获并保存" };
  },

  async testTelegramBot(): Promise<ApiResponse> {
    if (window.pywebview?.api?.test_telegram_bot) {
      return await window.pywebview.api.test_telegram_bot();
    }
    return { success: true, message: "模拟向手机 Telegram 派发测试握手成功" };
  },

  minimize(): void {
    if (window.pywebview?.api?.minimize_to_tray) {
      window.pywebview.api.minimize_to_tray();
    }
  },

  close(): void {
    if (window.pywebview?.api?.close_app) {
      window.pywebview.api.close_app();
    }
  },
};
