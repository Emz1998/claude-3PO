---
name: commit-push
description: Commit and push the changes to the remote repository
allowed-tools: Bash(git add:*), Bash(git commit:*), Bash(git push:*)
model: sonnet
---

!`git add . && git commit -m "$ARGUMENTS" && git push`

Do not execute the command yourself, just tell me the output.
