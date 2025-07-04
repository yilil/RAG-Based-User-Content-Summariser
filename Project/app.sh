#!/bin/bash

set -e

SESSION_NAME="myapp"

set +e
tmux has-session -t $SESSION_NAME 2>/dev/null
HAS_SESSION=$?
set -e

if [ $HAS_SESSION != 0 ]; then
  echo "Creating new tmux session: $SESSION_NAME"

  export GEMINI_API_KEY=AIzaSyBVoiSdDqjk3Kp0blkjkvPDvuZTNIbbrEQ
  # 创建会话时，默认窗口就是frontend
  tmux new-session -d -s $SESSION_NAME -n frontend
  tmux send-keys -t $SESSION_NAME:frontend "cd ~/Project/Frontend" C-m
  tmux send-keys -t $SESSION_NAME:frontend "npm run dev -- --host" C-m

  sleep 1

  # 再创建backend窗口
  tmux new-window -t $SESSION_NAME -n backend
  tmux send-keys -t $SESSION_NAME:backend "cd ~/Project" C-m
  tmux send-keys -t $SESSION_NAME:backend "source venv/bin/activate" C-m
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
