# 贡献指南 (Contributing to 安澜 · AnLan)

感谢你关注并考虑为 **安澜 (AnLan)** 贡献代码、高校校园网预设或问题反馈！

---

## 1. 提交高校校园网适配器预设

如果你所在高校尚未收录在内置预设库中，欢迎通过 Pull Request 补充 `data/universities.json`：

1. 在本地使用「安澜」的 **Portal 自动嗅探** 或浏览器抓包确认学校的认证协议（如 `drcom`、`srun`、`ruijie`、`generic` 等）、网关 IP 与认证页 URL；
2. 在 `data/universities.json` 中新增一条脱敏后的预设条目（**切勿包含任何个人学号或密码**）：
   ```json
   {
     "id": "university_code",
     "name": "大学名称 (认证体系说明)",
     "pinyin": "daxuemingcheng dxmc",
     "protocol": "drcom",
     "auth_url": "http://10.0.0.1/eportal/index.jsp",
     "gateway": "10.0.0.1",
     "wifi_ssids": ["Campus-WiFi"],
     "domain_keywords": ["example.edu.cn"]
   }
   ```
3. 提交 PR 并简述你的校园网认证特征，方便其他校友快速开箱即用。

---

## 2. 本地开发环境搭建

```powershell
# 1. 创建并激活虚拟环境，安装 Python 依赖
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. 构建前端静态界面
Push-Location frontend
npm install
npm run build
Pop-Location

# 3. 运行全量自动化单元测试
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

---

## 3. 代码与隐私脱敏规范

- 提交前请确保所有新增逻辑均配有对应的单元测试，且全量测试全部通过；
- **严禁提交**个人配置文件与运行产物（`config.json`、`campus_guard.key`、`campus_guard.log`、`anlan_diagnostic_*.zip` 等）；
- 文档与测试样例中的学号、密码、Token、Webhook、IP、MAC 等请统一使用占位符或示例值；
- 面向用户的提示信息、日志和代码注释保持清晰简洁的简体中文。

---

## 4. 提交 Issue 建议

反馈断网自愈、认证失败或界面异常时，建议在界面「运行日志」页点击 **「诊断包」**（或在终端执行 `AnLan.exe --export-diagnostics`）生成已自动脱敏的 `anlan_diagnostic_*.zip`，连同复现步骤一并附在 GitHub Issue 中。
