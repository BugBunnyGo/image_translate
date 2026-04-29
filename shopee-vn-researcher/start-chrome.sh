#!/bin/bash
# 启动 Chrome 带远程调试端口（用于 Playwright CDP 连接）
# 先关闭现有 Chrome 进程，再以调试模式重新启动

echo "正在关闭 Chrome..."
pkill -x "Google Chrome" 2>/dev/null
sleep 2

echo "以调试模式启动 Chrome (端口 9222)..."
open -a "Google Chrome" --args --remote-debugging-port=9222 --no-first-run --no-default-browser-check

echo ""
echo "Chrome 已启动，调试端口: 9222"
echo "请在 Chrome 中："
echo "  1. 访问 shopee.vn 并登录"
echo "  2. 访问 1688.com 并登录"
echo "  3. 访问 mobile.yangkeduo.com（如需采集拼多多）"
echo ""
echo "完成后运行: python3 run.py"
