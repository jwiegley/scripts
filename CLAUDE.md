# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a personal collection of ~200 utility scripts and automation tools, primarily written in Bash, Python, and other scripting languages. The scripts handle various system administration, development workflow, and automation tasks on macOS/Darwin systems with NixOS integration.

## Script Categories

### AI/ML Tools
- `ai` - Main Claude interface wrapper with model selection and proxy support
- `claude-sandbox` - Runs Claude in a firejail sandboxed environment
- `claude-auth` - Authentication helper for Claude
- `ask`, `ask-litellm` - LLM query interfaces
- `hf`, `hf.sh` - Hugging Face utilities
- `mlx-*` - Apple MLX framework tools
- `ollama-update` - Ollama model management

### Backup & Synchronization
- `backup` - Main backup orchestration script
- `backup-machines` - Machine-specific backup operations
- `push` - Multi-host synchronization using pushme
- `syncup`, `syncall`, `syncit` - Various sync utilities
- `gasync` - Git annex synchronization
- `update` - Update local repositories

### Git & Version Control
- `git-purge-from-annex`, `git-unlfs` - Git LFS/annex utilities
- `ga*` scripts (`gaadd`, `gacopy`, `gadrop`, `gaget`, `gamove`) - Git annex operations
- `changes` - Track repository changes

### Email Management
- `imapdedup`, `imapdedup.py` - IMAP deduplication
- `move-mail`, `rename-mailbox.sh` - Mailbox management
- `startmail`, `stopmail` - Mail service control
- `learn_ham` - Spam filter training
- `delete_message.py`, `list_message_ids.py` - Message operations

### File & System Management
- `checksum` - File checksumming utility
- `clean`, `cleanold`, `clearempty.py` - Cleanup utilities
- `trash` - Safe file deletion
- `zfs-*` scripts - ZFS filesystem management
- `b2-restic` - Backblaze B2 backup with restic

### Development Tools
- `mktags` - Generate tags files
- `start-hackage` - Hackage server management
- `hackage-upload` - Package upload to Hackage
- `epylint` - Python linting wrapper
- `run-python-with-requirements` - Python environment management

## Common Commands

### Running AI Tools
```bash
# Use Claude with default Sonnet model
./ai

# Use Claude Opus model
./ai opus

# Run Claude in sandbox
./claude-sandbox

# Enable MITM proxy for debugging
./ai --mitm
```

### Backup Operations
```bash
# Run full backup
./backup

# Quick backup without source updates
./backup --quick

# Backup with system upgrades
./backup --upgrade

# Push to specific hosts
./push all
./push clio
./push tank
```

### Git Annex Operations
```bash
# Add files to annex
./gaadd <files>

# Sync annex repositories
./gasync

# Move files between repositories
./gamove <source> <dest>
```

## Architecture Notes

### Script Patterns
- Most scripts use `#!/usr/bin/env bash` or `#!/bin/bash` shebang
- Error handling typically uses `set -euo pipefail` for strict mode
- Scripts often check for command availability before execution
- Environment-specific behavior based on hostname (hera, clio, tank, vulcan)

### Host Configuration
The scripts are designed for a multi-host setup:
- **hera**: Primary development machine
- **clio**: Secondary system
- **tank**: Storage/backup system
- **vulcan**: NixOS system

### Dependencies
- NixOS/Nix package manager for many tools
- `pass` for password management
- `firejail` for sandboxing
- Git, Git Annex, Git LFS
- Python for utility scripts
- Various command-line tools (rsync, ssh, etc.)

### Security Considerations
- Scripts use `pass` for credential management
- Claude sandbox uses firejail for filesystem isolation
- MITM proxy support includes certificate validation bypass (development only)
- Sensitive operations require authentication via getpass

## Working Directory Context
Many scripts assume operation from specific directories:
- AI tools default to `/etc/nixos`
- Backup scripts reference `~/doc`, `~/src`, `~/Models`, `~/Databases`
- Git operations may assume repository context