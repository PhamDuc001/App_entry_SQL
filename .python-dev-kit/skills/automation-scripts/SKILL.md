# Automation Scripts Skill

## Overview
This skill teaches how to write automation scripts for file operations, system integration, and scheduling.

## Principles
- **Idempotency**: Scripts should be safe to run multiple times
- **Error Recovery**: Handle failures gracefully
- **Logging**: Log all actions for debugging
- **Configuration**: Make scripts configurable
- **Validation**: Validate inputs before processing

## Key Capabilities

### 1. File Operations
- Batch processing
- File watching
- Pattern matching
- Directory traversal

### 2. System Integration
- Subprocess execution
- Shell commands
- System monitoring
- Service management

### 3. Scheduling
- cron jobs
- APScheduler
- Task queues (Celery, RQ)

## When to Use This Skill
Load this skill when:
- Writing automation scripts
- Batch processing files
- System integration
- Task scheduling
- Error recovery logic

## Sections
- `file-operations.md`: Batch processing, file watching
- `system-integration.md`: Subprocess, shell commands
- `scheduling.md`: cron, APScheduler
- `error-recovery.md`: Retry logic, idempotency
