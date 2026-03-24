---
name: skill-creator
description: Create, modify, and improve Claude Code skills. Use when the user asks to create a new skill, build a custom skill, write a SKILL.md, or package agent capabilities.
metadata:
  author: anthropic
  version: "1.0.0"
---

# Skill Creator

Help users create, modify, and improve Claude Code skills.

## What is a Skill?

A skill is a packaged set of instructions that teaches Claude how to perform a specific task. Skills are defined by a `SKILL.md` file and optional supporting resources.

## Skill Structure

```
my-skill/
├── SKILL.md              # Required: Core skill definition
├── scripts/              # Optional: Executable scripts
│   └── run.sh
├── references/           # Optional: Reference documentation
│   └── patterns.md
└── assets/               # Optional: Templates and static files
    └── template.html
```

## SKILL.md Format

```markdown
---
name: my-skill-name
description: Clear description of when this skill should activate. Include trigger phrases like "deploy", "review code", "create component".
metadata:
  author: your-name
  version: "1.0.0"
  argument-hint: <optional-argument-description>
---

# Skill Title

Brief overview of what this skill does.

## When to Use

Describe the situations and trigger phrases that should activate this skill.

## Instructions

Step-by-step instructions for Claude to follow when this skill is invoked.

## Examples

Show example inputs and expected behavior.

## Guidelines

List important rules, constraints, and best practices.
```

## Key Principles

### 1. Clear Trigger Description
The `description` field in frontmatter is the primary signal for when the skill activates. Make it specific:
- Good: `"Deploy applications to AWS using CDK. Use when asked to 'deploy to AWS', 'create infrastructure', or 'set up cloud resources'."`
- Bad: `"Helps with AWS stuff"`

### 2. Actionable Instructions
Write instructions as if teaching a skilled developer who has never done this specific task:
- Be explicit about commands to run
- Include error handling guidance
- Specify the expected output format

### 3. Minimal and Focused
Each skill should do one thing well. If a skill is trying to do too many things, split it into multiple skills.

### 4. Include Context
Reference documentation, API specs, or patterns that Claude needs to follow. Put large reference material in the `references/` directory.

## Installation Paths

Skills can be installed in two locations:

### Project-level (recommended)
```
.agents/skills/my-skill/SKILL.md
```
With a symlink for Claude Code:
```
.claude/skills/my-skill -> ../../.agents/skills/my-skill
```

### User-level
```
~/.claude/skills/my-skill/SKILL.md
```

## Creating a New Skill

1. **Define the purpose** — What specific task does this skill handle?
2. **Write the SKILL.md** — Follow the format above with clear frontmatter and instructions
3. **Add supporting files** — Scripts, references, or assets as needed
4. **Test the skill** — Invoke it in Claude Code and verify the behavior
5. **Iterate** — Refine instructions based on how Claude performs

## Testing Skills

To test a skill locally:
1. Place it in `.agents/skills/your-skill/`
2. Create symlink: `ln -s ../../.agents/skills/your-skill .claude/skills/your-skill`
3. Start a new Claude Code session
4. Use the trigger phrases from your skill description
5. Verify Claude follows the instructions correctly

## Common Mistakes

- **Too vague description** — Claude won't know when to activate the skill
- **Too many instructions** — Keep it focused; Claude works better with clear, concise guidance
- **Missing error handling** — Always include what to do when things go wrong
- **Hardcoded paths** — Use relative paths and environment variables
- **No examples** — Examples help Claude understand expected behavior
