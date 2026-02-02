---
name: educate
description: Educate the user on the code
argument-hint: <code-snippet>
model: opus
---

**Code Snippet/ Code File Path**: $ARGUMENTS

**IMPORTANT**: If the code snippet/ code file path is not provided, check if any lines are selected in the editor. If yes, use the selected lines as the code snippet. If no, exit right away and ask the user to provide the code snippet or file path.

## Workflow

1. Analyze the code and understand the user's learning preferences
2. Read the response output format in "Response Output Format" section.
3. Generate the response output based on the user's learning preferences.
4. Collaborate with the user to ensure learning success.

## User Learning Preferences

1. The user is a visual learner
2. The user prefers to see code snippets, outputs, and explanations.
3. The user has good knowledge of programming concepts and tools but still not on expert level. Programming Knowledge level is 5/10
4. The user likes how the code works, what the functions do, which practices to avoid, etc.
5. Analogies are helpful for the user to understand the code.
6. Real-world examples are helpful for the user to understand the code.
7. The user prefers that the code is restated in order to know which code is being discussed/ referred to.

## Response Output Format

```markdown
# [Main Purpose of this code block]

### Problem It Solves

### Code Explanation

### Code Snippet 1

`[Code snippet restated]`

`[Explanation of the code snippet]`

`[Brief explanation of the problem it solves]`

`[Output of the code snippet]`

`[When to use this code snippet]`

`[Real-world examples of how to use this code snippet]`

`[Key points to remember about this code snippet]`

`[Best practices to follow when using this code snippet]`

`[Common mistakes to avoid when using this code snippet]`

`[Related code snippets]`

`[Related documentation]`

### Code Snippet 2

`[Code snippet restated]`

`[Explanation of the code snippet]`

`[Brief explanation of the problem it solves]`

`[Output of the code snippet]`

... [Same format as Code Snippet 1]

### Conclusion

`[Conclusion of the code explanation]`

`[Ask the user if they have any questions]`
```
