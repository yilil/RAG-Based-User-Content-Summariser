#!/bin/bash

set -e

SESSION_NAME="AI_RAG"

set +e
tmux has-session -t $SESSION_NAME 2>/dev/null
HAS_SESSION=$?
set -e

if [ $HAS_SESSION != 0 ]; then
  echo "Creating new tmux session: $SESSION_NAME"

  # 创建 frontend 窗口并进入对应目录
  tmux new-session -d -s $SESSION_NAME -n frontend
  tmux send-keys -t $SESSION_NAME:frontend "export GEMINI_API_KEY=AIzaSyBVoiSdDqjk3Kp0blkjkvPDvuZTNIbbrEQ" C-m
  tmux send-keys -t $SESSION_NAME:frontend "export DEEPSEEK_API_KEY="sk-8c146e867fc64d5fb5972f06066b3aa2" C-m
  tmux send-keys -t $SESSION_NAME:frontend "cd ~/NextGen-AI/Project/Frontend" C-m
  tmux send-keys -t $SESSION_NAME:frontend "npm run dev -- --host" C-m

  sleep 1

  # 创建 backend 窗口并进入对应目录
  tmux new-window -t $SESSION_NAME -n backend
  tmux send-keys -t $SESSION_NAME:backend "cd ~/NextGen-AI/Project" C-m
  tmux send-keys -t $SESSION_NAME:backend "if [ -d venv ]; then source venv/bin/activate; else echo '虚拟环境不存在！'; fi" C-m
  tmux send-keys -t $SESSION_NAME:backend "python manage.py runserver 0.0.0.0:8000" C-m

  echo "tmux session '$SESSION_NAME' created with frontend and backend."

else
  echo "tmux session '$SESSION_NAME' already exists."
fi

if [ -z "$TMUX" ]; then
  tmux attach -t $SESSION_NAME
else
  echo "Already inside a tmux session, skipping attach."
fi
