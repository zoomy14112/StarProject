#!/bin/bash

# 获取当前日期
current_date=$(date +"%Y-%m-%d")

# 提交消息
commit_message="${current_date} update"

# 检查是否为 Git 仓库
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "error:git respository not found."
    exit 1
fi

# 执行 Git 操作
echo "execute git add..."
git add . || { echo "git add failed"; exit 1; }

echo "execute git commit..."
git commit -m "$commit_message" || { echo "git commit failed"; exit 1; }

echo "execute git push..."
git push || { echo "git push failed"; exit 1; }

echo "Finished pushing StarProject."

# ──────────────────────────────────────────────
# 进入 blog 子目录，整理 Markdown 并推送
# ──────────────────────────────────────────────
BLOG_DIR="$(dirname "$0")/blog"

echo ""
echo ">>> Entering blog directory: $BLOG_DIR"
cd "$BLOG_DIR" || { echo "error: blog directory not found."; exit 1; }

echo ">>> Running transform.py..."
python3 transform.py || { echo "transform.py failed"; exit 1; }

echo ">>> git add..."
git add . || { echo "git add failed in blog/"; exit 1; }

echo ">>> git commit..."
git commit -m "$commit_message" || echo "(nothing to commit or commit skipped)"

echo ">>> git push..."
git push || { echo "git push failed in blog/"; exit 1; }

echo ""
echo "All done."
