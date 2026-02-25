# Python Dev Kit Architecture

## Overview

Python Dev Kit is a specialized AI agent framework for Python tool development and multi-language code understanding. It extends the Antigravity Kit architecture with Python-focused agents, skills, and workflows.

## Structure

```
.python-dev-kit/
├── agents/                    # Specialist AI personas
│   ├── python-architect.md
│   ├── code-analyzer.md
│   ├── tool-builder.md
│   ├── java-bridge.md
│   ├── cpp-bridge.md
│   ├── performance-tuner.md
│   ├── test-engineer.md
│   ├── debugger.md
│   ├── documentation-writer.md
│   ├── security-auditor.md
│   ├── multi-language-analyst.md
│   ├── orchestrator.md
│   ├── project-planner.md
│   ├── code-archaeologist.md
│   └── explorer-agent.md
├── skills/                    # Domain-specific knowledge modules
│   ├── python-patterns/
│   ├── code-comprehension/
│   ├── cross-language-bridge/
│   ├── tool-development/
│   ├── performance-optimization/
│   ├── testing-strategies/
│   ├── automation-scripts/
│   ├── debugging-methodology/
│   ├── security-patterns/
│   └── documentation-patterns/
├── workflows/                 # Slash command procedures
│   ├── analyze-code.md
│   ├── build-tool.md
│   ├── debug-python.md
│   ├── optimize.md
│   ├── cross-lang.md
│   ├── test.md
│   ├── review.md
│   ├── document.md
│   ├── profile.md
│   ├── refactor.md
│   ├── integrate.md
│   └── explain.md
├── rules/                     # Workspace rules
│   ├── python-standards.md
│   ├── code-review.md
│   └── memory-bank.md
└── ARCHITECTURE.md
```

## Components

### Agents

Agents are specialist AI personas configured with domain-specific expertise. Each agent is defined by a markdown file with YAML frontmatter specifying:
- `name`: Agent identifier
- `description`: Agent's purpose
- `tools`: Available tools (Read, Edit, Write, Bash, etc.)
- `skills`: Accessible skill modules

### Skills

Skills are modular knowledge packages containing principles, patterns, and decision-making frameworks. Each skill includes:
- `SKILL.md`: Main documentation
- `sections/`: Detailed guides
- `examples/`: Reference implementations
- `scripts/`: Helper utilities (optional)

### Workflows

Workflows are step-by-step procedures invoked via slash commands. Each workflow contains:
- YAML frontmatter with description
- Structured steps
- Decision points
- Best practices

### Rules

Rules are automatically applied workspace standards:
- `python-standards.md`: PEP 8, type hints, docstrings
- `code-review.md`: Review checklist
- `memory-bank.md`: Project context storage

## Usage

### Using Agents

Mention an agent by name to invoke specialized expertise:
```
Use the code-analyzer agent to review this Python module
Use the java-bridge agent to understand this Java code
```

### Using Skills

Skills are loaded automatically based on task context. No manual configuration needed.

### Using Workflows

Invoke workflows with slash commands:
```
/analyze-code path/to/module.py
/build-tool log analyzer
/debug-python function X failing
```

## Key Features

1. **Python-Focused**: Optimized for Python development
2. **Cross-Language**: Supports Java, C++, Python understanding
3. **Tool Development**: Specialized for building CLI tools
4. **Code Comprehension**: Deep analysis capabilities
5. **Modular**: Reusable skills and agents
6. **Extensible**: Easy to add new agents and skills

## Design Principles

### Skill Design
- Principle-based, not pattern-based
- Context-aware loading
- Modular and reusable
- Examples-driven

### Agent Design
- Specialized domain expertise
- Composable via orchestrator
- Configurable via YAML
- Tool-aware

### Workflow Design
- Step-by-step procedures
- Clear decision points
- Embedded best practices
- Easy slash command invocation

## Integration with Cline

This kit integrates seamlessly with Cline's:
- **Rules**: Workspace rules in `.python-dev-kit/rules/`
- **Workflows**: Slash commands in `.python-dev-kit/workflows/`
- **Memory Bank**: Context storage in `.python-dev-kit/rules/memory-bank.md`

## License

MIT © Python Dev Kit Contributors
