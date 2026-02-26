#!/bin/bash
# launch-vscode.sh - Always triggers folderOpen tasks

PROJECT_DIR="${1:-$(pwd)}"

# Open in new window - guarantees folderOpen triggers
code -n "$PROJECT_DIR"
