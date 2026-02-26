#!/bin/bash
# launch-claudes.sh - Launch 4 tmux windows with claude

SESSION="claude"
PROJECT_DIR="$HOME/avaris-ai"

tmux new-session -d -s "$SESSION" -c "$PROJECT_DIR" 2>/dev/null || tmux kill-session -t "$SESSION" && tmux new-session -d -s "$SESSION" -c "$PROJECT_DIR"
tmux send-keys -t "$SESSION" "claude" Enter

for i in 2 3 4; do
  tmux new-window -t "$SESSION" -c "$PROJECT_DIR"
  tmux send-keys -t "$SESSION" "claude" Enter
done

tmux attach -t "$SESSION"
