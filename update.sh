#!/bin/bash
# 简化版自动 Git 提交脚本

# 获取当前日期
current_date=$(date +"%Y-%m-%d")

# 提交消息
commit_message="${current_date} update"

# 检查是否为 Git 仓库
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "错误：当前目录不是 Git 仓库"
    exit 1
fi

# 执行 Git 操作
echo "执行 git add..."
git add . || { echo "git add 失败"; exit 1; }

echo "执行 git commit..."
git commit -m "$commit_message" || { echo "git commit 失败"; exit 1; }

echo "执行 git push..."
git push || { echo "git push 失败"; exit 1; }

echo "完成！"
