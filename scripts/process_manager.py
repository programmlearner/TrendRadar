#!/usr/bin/env python
# coding=utf-8
"""TrendRadar 进程管理工具

跨平台的进程启动、停止和状态检查工具
"""

import os
import sys
import time
import signal
import subprocess
import psutil
from pathlib import Path
from typing import Optional, Tuple


class ProcessManager:
    """进程管理器"""

    def __init__(self, project_root: Optional[Path] = None, service_type: str = "api"):
        """初始化进程管理器

        Args:
            project_root: 项目根目录,默认为脚本所在目录的父目录
            service_type: 服务类型 ('api' 或 'crawler')
        """
        if project_root is None:
            self.project_root = Path(__file__).parent.parent.resolve()
        else:
            self.project_root = Path(project_root).resolve()

        self.service_type = service_type

        # 根据服务类型设置不同的文件名
        if service_type == "api":
            self.pid_file = self.project_root / "trendradar_api.pid"
            self.log_file = self.project_root / "output" / "trendradar_api.log"
        else:
            self.pid_file = self.project_root / "trendradar.pid"
            self.log_file = self.project_root / "output" / "trendradar.log"

        # 确保输出目录存在
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def is_running(self) -> Tuple[bool, Optional[int]]:
        """检查进程是否正在运行

        Returns:
            (是否运行, 进程ID) 如果没有运行则返回 (False, None)
        """
        if not self.pid_file.exists():
            return False, None

        try:
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())

            # 检查进程是否存在
            if psutil.pid_exists(pid):
                # 进一步检查进程名称是否匹配
                try:
                    proc = psutil.Process(pid)
                    cmdline = ' '.join(proc.cmdline())
                    # 根据服务类型检查不同的进程特征
                    if self.service_type == "api":
                        if 'uvicorn' in cmdline or 'src.api.server' in cmdline:
                            return True, pid
                    else:
                        if 'main.py' in cmdline or 'python' in proc.name().lower():
                            return True, pid
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            # PID 文件存在但进程不存在,清理 PID 文件
            self.pid_file.unlink(missing_ok=True)
            return False, None

        except (ValueError, IOError):
            return False, None

    def start(self, host: str = "0.0.0.0", port: int = 8000, mode: str = "daily") -> bool:
        """启动 TrendRadar 服务

        Args:
            host: API 服务器监听地址（仅 API 模式）
            port: API 服务器端口（仅 API 模式）
            mode: 爬虫运行模式 (daily/current/incremental)（仅爬虫模式）

        Returns:
            是否启动成功
        """
        # 检查是否已经在运行
        running, pid = self.is_running()
        if running:
            service_name = "API 服务器" if self.service_type == "api" else "爬虫"
            print(f"❌ TrendRadar {service_name}已在运行 (PID: {pid})")
            return False

        # 准备启动命令
        if self.service_type == "api":
            # API 服务器启动命令
            print(f"🚀 启动 TrendRadar API 服务器 (监听: {host}:{port})...")
            # 检查 uvicorn 是否可用
            try:
                subprocess.run(
                    [sys.executable, "-m", "uvicorn", "--version"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True
                )
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("❌ uvicorn 未安装，请先安装依赖: pip install uvicorn")
                return False

            cmd = [
                sys.executable, "-m", "uvicorn",
                "src.api.server:app",
                "--host", host,
                "--port", str(port)
            ]
        else:
            # 爬虫启动命令
            print(f"🚀 启动 TrendRadar 爬虫 (模式: {mode})...")
            main_py = self.project_root / "main.py"
            if not main_py.exists():
                print(f"❌ 找不到主程序: {main_py}")
                return False
            cmd = [sys.executable, str(main_py), "--mode", mode]

        try:
            # 打开日志文件
            log_file = open(self.log_file, 'a', encoding='utf-8')

            # 启动进程
            if os.name == 'nt':  # Windows
                # Windows 使用 CREATE_NO_WINDOW 标志
                process = subprocess.Popen(
                    cmd,
                    cwd=str(self.project_root),
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:  # macOS/Linux
                # Unix 使用 nohup
                process = subprocess.Popen(
                    cmd,
                    cwd=str(self.project_root),
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    start_new_session=True
                )

            # 写入 PID 文件
            with open(self.pid_file, 'w') as f:
                f.write(str(process.pid))

            # 等待一小段时间确保进程正常启动
            time.sleep(2)

            # 验证进程是否还在运行
            if psutil.pid_exists(process.pid):
                service_name = "API 服务器" if self.service_type == "api" else "爬虫"
                print(f"✅ TrendRadar {service_name}启动成功 (PID: {process.pid})")
                print(f"📝 日志文件: {self.log_file}")
                if self.service_type == "api":
                    print(f"🌐 访问地址: http://{host}:{port}")
                    print(f"📚 API 文档: http://{host}:{port}/docs")
                return True
            else:
                print("❌ 进程启动后立即退出,请检查日志")
                self.pid_file.unlink(missing_ok=True)
                return False

        except Exception as e:
            print(f"❌ 启动失败: {e}")
            self.pid_file.unlink(missing_ok=True)
            return False

    def stop(self, force: bool = False) -> bool:
        """停止 TrendRadar 服务

        Args:
            force: 是否强制终止

        Returns:
            是否停止成功
        """
        running, pid = self.is_running()

        if not running:
            service_name = "API 服务器" if self.service_type == "api" else "爬虫"
            print(f"ℹ️  TrendRadar {service_name}未在运行")
            return True

        service_name = "API 服务器" if self.service_type == "api" else "爬虫"
        print(f"🛑 正在停止 TrendRadar {service_name} (PID: {pid})...")

        try:
            process = psutil.Process(pid)

            if force:
                # 强制终止
                process.kill()
                print("✅ 已强制终止进程")
            else:
                # 优雅关闭
                if os.name == 'nt':
                    # Windows 使用 CTRL_BREAK_EVENT
                    process.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    # Unix 使用 SIGTERM
                    process.terminate()

                # 等待进程退出
                try:
                    process.wait(timeout=10)
                    print("✅ 进程已优雅退出")
                except psutil.TimeoutExpired:
                    print("⚠️  进程未在超时时间内退出,强制终止...")
                    process.kill()
                    print("✅ 已强制终止进程")

            # 清理 PID 文件
            self.pid_file.unlink(missing_ok=True)
            return True

        except psutil.NoSuchProcess:
            print("ℹ️  进程已不存在")
            self.pid_file.unlink(missing_ok=True)
            return True
        except Exception as e:
            print(f"❌ 停止失败: {e}")
            return False

    def status(self) -> None:
        """显示进程状态"""
        running, pid = self.is_running()

        service_name = "API 服务器" if self.service_type == "api" else "爬虫"

        print("=" * 50)
        print(f"TrendRadar {service_name}状态")
        print("=" * 50)

        if running:
            try:
                process = psutil.Process(pid)
                print(f"状态: ✅ 运行中")
                print(f"PID: {pid}")
                print(f"启动时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(process.create_time()))}")
                print(f"CPU 占用: {process.cpu_percent(interval=1):.1f}%")
                print(f"内存占用: {process.memory_info().rss / 1024 / 1024:.1f} MB")
                print(f"命令行: {' '.join(process.cmdline())}")
            except Exception as e:
                print(f"状态: ⚠️  运行异常 - {e}")
        else:
            print("状态: ⭕ 未运行")

        print(f"\n项目目录: {self.project_root}")
        print(f"日志文件: {self.log_file}")

        if self.log_file.exists():
            print(f"日志大小: {self.log_file.stat().st_size / 1024:.1f} KB")

        print("=" * 50)

    def tail_log(self, lines: int = 20) -> None:
        """显示日志尾部内容

        Args:
            lines: 显示的行数
        """
        if not self.log_file.exists():
            print("ℹ️  日志文件不存在")
            return

        print(f"\n📝 最近 {lines} 行日志:")
        print("-" * 50)

        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                for line in all_lines[-lines:]:
                    print(line.rstrip())
        except Exception as e:
            print(f"❌ 读取日志失败: {e}")


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="TrendRadar 进程管理工具")
    parser.add_argument(
        "action",
        choices=["start", "stop", "restart", "status", "log"],
        help="操作: start(启动) stop(停止) restart(重启) status(状态) log(日志)"
    )
    parser.add_argument(
        "--service",
        choices=["api", "crawler"],
        default="api",
        help="服务类型: api(API服务器) crawler(爬虫) (默认: api)"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="API 服务器监听地址 (仅用于 api 服务)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="API 服务器端口 (仅用于 api 服务)"
    )
    parser.add_argument(
        "--mode",
        choices=["daily", "current", "incremental"],
        default="daily",
        help="爬虫启动模式 (仅用于 crawler 服务)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制停止进程 (仅用于 stop)"
    )
    parser.add_argument(
        "--lines",
        type=int,
        default=20,
        help="日志显示行数 (仅用于 log)"
    )

    args = parser.parse_args()

    # 创建进程管理器
    manager = ProcessManager(service_type=args.service)

    # 执行操作
    if args.action == "start":
        if args.service == "api":
            success = manager.start(host=args.host, port=args.port)
        else:
            success = manager.start(mode=args.mode)
        sys.exit(0 if success else 1)

    elif args.action == "stop":
        success = manager.stop(force=args.force)
        sys.exit(0 if success else 1)

    elif args.action == "restart":
        print("🔄 重启 TrendRadar...")
        manager.stop(force=False)
        time.sleep(1)
        if args.service == "api":
            success = manager.start(host=args.host, port=args.port)
        else:
            success = manager.start(mode=args.mode)
        sys.exit(0 if success else 1)

    elif args.action == "status":
        manager.status()
        sys.exit(0)

    elif args.action == "log":
        manager.tail_log(lines=args.lines)
        sys.exit(0)


if __name__ == "__main__":
    main()
