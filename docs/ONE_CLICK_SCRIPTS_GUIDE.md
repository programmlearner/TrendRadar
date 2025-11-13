# TrendRadar 一键启动脚本使用指南

本文档介绍如何使用 TrendRadar 的一键启动和关闭脚本。

## 📋 前置要求

- **Python 3.10+** 已安装（macOS/Linux 使用 `python3`，Windows 使用 `python`）
- 网络连接正常（首次运行时需要安装依赖）

> **注意**: 脚本会自动检测 Python 环境并安装所需依赖，无需手动配置虚拟环境。

---

## 🚀 快速开始

### Windows 用户

#### 启动服务
```bash
# 双击运行或在命令提示符中执行
start.bat

# 指定运行模式（可选）
start.bat daily         # 当日汇总模式（默认）
start.bat current       # 当前榜单模式
start.bat incremental   # 增量监控模式
```

#### 停止服务
```bash
# 优雅关闭
stop.bat

# 强制终止
stop.bat --force
```

#### 查看状态
```bash
status.bat
```

---

### macOS/Linux 用户

#### 启动服务
```bash
# 在终端中执行
./start.sh

# 指定运行模式（可选）
./start.sh daily         # 当日汇总模式（默认）
./start.sh current       # 当前榜单模式
./start.sh incremental   # 增量监控模式
```

#### 停止服务
```bash
# 优雅关闭
./stop.sh

# 强制终止
./stop.sh --force
```

#### 查看状态
```bash
./status.sh
```

---

## 📖 详细说明

### 运行模式

TrendRadar 支持三种运行模式:

1. **daily (当日汇总)** - 默认模式
   - 汇总当天所有匹配的新闻
   - 定时推送当日新闻 + 新增区域

2. **current (当前榜单)**
   - 只推送当前批次的新闻
   - 定时推送当前榜单匹配新闻 + 新增区域

3. **incremental (增量监控)**
   - 仅推送新增内容
   - 有新增才推送（节省通知频率）

### 脚本功能说明

#### start 脚本 (启动)

执行流程:
1. ✅ 检查 Python 环境（版本、可用性）
2. ✅ 自动安装项目依赖（首次运行或依赖缺失时）
3. ✅ 检查配置文件（`config/config.yaml`）
4. ✅ 后台启动 TrendRadar 服务
5. ✅ 记录进程 PID 到 `trendradar.pid`

输出信息:
- Python 版本
- 依赖安装状态
- 配置文件状态
- 进程 PID 和日志文件位置

#### stop 脚本 (停止)

执行流程:
1. ✅ 读取 PID 文件
2. ✅ 检查进程是否存在
3. ✅ 发送优雅关闭信号（默认）
4. ✅ 等待进程退出（超时 10 秒）
5. ✅ 强制终止（如果优雅关闭失败或使用 `--force` 参数）
6. ✅ 清理 PID 文件

参数:
- `--force` 或 `-f`: 跳过优雅关闭，直接强制终止

#### status 脚本 (状态查看)

显示信息:
- ✅ 服务运行状态（运行中/未运行）
- ✅ 进程 PID
- ✅ 启动时间
- ✅ CPU 和内存占用
- ✅ 命令行参数
- ✅ 日志文件路径和大小

---

## 🔧 高级用法

### 使用 Python 进程管理工具

如果你需要更多控制，可以直接使用 Python 进程管理工具:

```bash
# Windows
python scripts\process_manager.py [action] [options]

# macOS/Linux
python3 scripts/process_manager.py [action] [options]
```

**可用操作**:

1. **启动服务**
   ```bash
   python3 scripts/process_manager.py start --mode daily
   python3 scripts/process_manager.py start --mode current
   python3 scripts/process_manager.py start --mode incremental
   ```

2. **停止服务**
   ```bash
   python3 scripts/process_manager.py stop           # 优雅关闭
   python3 scripts/process_manager.py stop --force   # 强制终止
   ```

3. **重启服务**
   ```bash
   python3 scripts/process_manager.py restart --mode daily
   ```

4. **查看状态**
   ```bash
   python3 scripts/process_manager.py status
   ```

5. **查看日志**
   ```bash
   python3 scripts/process_manager.py log              # 最近 20 行
   python3 scripts/process_manager.py log --lines 50   # 最近 50 行
   ```

---

## 📝 日志管理

### 日志文件位置

- **默认路径**: `output/trendradar.log`
- **编码**: UTF-8
- **追加模式**: 每次启动会追加到现有日志文件

### 查看日志

#### 实时查看（推荐）

**Windows (PowerShell)**:
```powershell
Get-Content output\trendradar.log -Wait -Tail 20
```

**macOS/Linux**:
```bash
tail -f output/trendradar.log
```

#### 查看最近日志

使用进程管理工具:
```bash
python3 scripts/process_manager.py log --lines 50
```

#### 清空日志

```bash
# Windows
del output\trendradar.log

# macOS/Linux
rm output/trendradar.log
```

---

## 🛠️ 故障排查

### 1. 启动失败

**症状**: 运行 `start` 脚本后提示启动失败

**排查步骤**:
1. 检查 Python 版本是否 >= 3.10
   ```bash
   python --version    # Windows
   python3 --version   # macOS/Linux
   ```

2. 检查配置文件是否存在
   ```bash
   # 确保 config/config.yaml 存在
   ls config/config.yaml   # macOS/Linux
   dir config\config.yaml  # Windows
   ```

3. 查看详细日志
   ```bash
   python3 scripts/process_manager.py log --lines 100
   ```

4. 手动运行测试
   ```bash
   python main.py --mode daily
   ```

### 2. 依赖安装失败

**症状**: 提示 "依赖安装失败"

**解决方案**:
1. 升级 pip
   ```bash
   python3 -m pip install --upgrade pip
   ```

2. 手动安装依赖
   ```bash
   python3 -m pip install -r requirements.txt
   ```

3. 使用国内镜像（网络问题）
   ```bash
   python3 -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
   ```

### 3. 进程无法停止

**症状**: 运行 `stop` 脚本后进程仍在运行

**解决方案**:
1. 使用强制停止
   ```bash
   ./stop.sh --force      # macOS/Linux
   stop.bat --force       # Windows
   ```

2. 手动查找并终止进程
   ```bash
   # macOS/Linux
   ps aux | grep main.py
   kill -9 <PID>

   # Windows (PowerShell)
   Get-Process python | Where-Object {$_.CommandLine -like "*main.py*"} | Stop-Process -Force
   ```

### 4. PID 文件冲突

**症状**: 提示 "TrendRadar 已在运行" 但实际未运行

**解决方案**:
删除 PID 文件
```bash
# macOS/Linux
rm trendradar.pid

# Windows
del trendradar.pid
```

### 5. 权限问题（macOS/Linux）

**症状**: `Permission denied` 错误

**解决方案**:
```bash
chmod +x start.sh stop.sh status.sh
```

---

## 🔐 安全注意事项

1. **配置文件安全**
   - ⚠️ 不要将 webhook URLs 提交到 Git
   - ✅ 使用环境变量或 GitHub Secrets 管理敏感信息

2. **日志文件**
   - ⚠️ 日志可能包含敏感信息
   - ✅ 定期清理或轮转日志文件

3. **进程权限**
   - ⚠️ 不建议使用 root/管理员权限运行
   - ✅ 使用普通用户权限即可

---

## 💡 最佳实践

### 开发环境

1. **测试新配置**
   ```bash
   # 先停止后台服务
   ./stop.sh

   # 前台运行测试（查看实时输出）
   python3 main.py --mode daily

   # 确认无误后再后台启动
   ./start.sh daily
   ```

2. **查看实时日志**
   ```bash
   tail -f output/trendradar.log
   ```

### 生产环境

1. **使用定时任务**（如果需要周期性运行）
   - GitHub Actions（推荐，已配置）
   - Docker + cron（推荐，已配置）
   - 系统 cron/计划任务

2. **监控服务状态**
   ```bash
   # 添加到 crontab 定期检查
   */30 * * * * /path/to/TrendRadar/status.sh >> /tmp/trendradar-health.log
   ```

3. **日志轮转**
   ```bash
   # 每天清理旧日志（保留最近 100 行）
   0 0 * * * tail -n 100 /path/to/TrendRadar/output/trendradar.log > /tmp/temp.log && mv /tmp/temp.log /path/to/TrendRadar/output/trendradar.log
   ```

---

## 📚 相关文档

- [README.md](../README.md) - 项目总体介绍
- [README_REFACTORED.md](../README_REFACTORED.md) - 重构版使用说明
- [config/config.yaml](../config/config.yaml) - 配置文件说明

---

## ❓ 常见问题

**Q: 脚本需要 root 权限吗？**
A: 不需要。普通用户权限即可运行。

**Q: 可以同时运行多个实例吗？**
A: 不建议。脚本使用单一 PID 文件管理，同时运行多个实例会导致冲突。

**Q: 如何修改运行模式？**
A: 停止当前服务，然后使用新模式重新启动：
```bash
./stop.sh
./start.sh incremental
```

**Q: 日志文件会无限增长吗？**
A: 是的。建议定期清理或使用日志轮转工具（如 `logrotate`）。

**Q: Windows 上双击 .bat 文件窗口闪退怎么办？**
A: 在命令提示符中运行，或右键 → 编辑，检查是否有错误提示。

---

## 🆘 获取帮助

如果遇到问题，请提供以下信息:

1. 操作系统和版本
2. Python 版本 (`python --version`)
3. 错误信息截图
4. 最近的日志内容（`python3 scripts/process_manager.py log`）

GitHub Issues: https://github.com/yourusername/TrendRadar/issues

---

**文档版本**: 1.0
**最后更新**: 2025-11-13
