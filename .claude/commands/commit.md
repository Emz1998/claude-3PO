---
name: commit
description: Commit the changes to the remote repository
allowed-tools: Bash(git add:*), Bash(git commit:*)
model: sonnet
---

!`git add . && git commit -m "$ARGUMENTS"`

Do not execute the command yourself, just tell me the output.
