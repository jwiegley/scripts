# Personal Scripts

A personal collection of ~200 utility scripts and automation tools, primarily written in Bash and Python, designed for system administration, development workflows, and personal automation on macOS/Darwin systems with NixOS integration.

## Statistics

- **Total Scripts:** 200
- **Language Distribution:** 
  - Bash: 195 scripts (97.5%)
  - Python: 5 scripts (2.5%)
- **Script Types:** Executable scripts, shell scripts (.sh), Python scripts (.py), Awk scripts (.awk)

---

## Categories

### 1. AI/LLM Tools (14 scripts)

Tools for interacting with AI models and language learning platforms.

| Script | Purpose |
|--------|---------|
| `ai` | Main Claude interface wrapper with model selection (sonnet/opus) and MITM proxy support |
| `ask` | LLM query interface supporting multiple providers (OpenAI, Anthropic, OpenRouter, Perplexity) with customizable endpoints |
| `ask-litellm` | LiteLLM proxy interface for accessing local/remote models |
| `claude-auth` | Authentication helper for Claude via pass password manager |
| `claude-sandbox` | Runs Claude in a sandboxed firejail environment with filesystem isolation |
| `hf` | Hugging Face model utilities wrapper |
| `hf.sh` | Hugging Face configuration and model management |
| `mlx` | Apple MLX framework interface |
| `mlx-lm` | MLX language model tools |
| `mlx-vlm` | MLX vision-language model tools |
| `mlx-whisper` | MLX Whisper speech-to-text interface |
| `ollama-update` | Ollama model update and management |
| `openrouter-credits` | Check OpenRouter API credits |
| `ragflow-cli` | RAGFlow (document understanding) CLI interface |

**Key Dependencies:** pass (password manager), nix/nix-shell, claude CLI, Hugging Face Hub

---

### 2. Backup & Synchronization (11 scripts)

Backup orchestration and multi-host synchronization tools.

| Script | Purpose |
|--------|---------|
| `backup` | Main backup orchestration with monitoring and logging |
| `backup-machines` | Machine-specific backup operations (rsync-based) |
| `backup-tank` | Tank storage backup using Backblaze B2 |
| `b2` | Backblaze B2 API authentication setup |
| `b2-restic` | Restic backup to Backblaze B2 storage |
| `push` | Multi-host synchronization wrapper (hera, clio, tank) using pushme |
| `syncup` | Synchronize key directories (doc, src, emacs.d) across hosts |
| `syncall` | Full synchronization across multiple repositories |
| `syncit` | Git-based synchronization helper |
| `gasync` | Git Annex synchronization across remotes |
| `running-backup` | Monitor and report backup status |

**Key Dependencies:** pushme, restic, git annex, b2 CLI, pass (credentials)

**Host Configuration:**
- hera: Primary development machine
- clio: Secondary system
- tank: Storage/backup system
- vulcan: NixOS system

---

### 3. Git & Version Control (11 scripts)

Git and Git Annex management utilities.

| Script | Purpose |
|--------|---------|
| `changes` | Stage all changes, handle deleted files, auto-commit, and sync to remotes |
| `create-repo` | Initialize repository and create GitHub remote |
| `conflicts` | Find merge conflict markers in C/C++ files |
| `gaadd` | Add files to Git Annex with auto-sync (wrapper) |
| `gacopy` | Copy Annex files to remote locations with numcopies enforcement |
| `gadrop` | Drop local Annex file copies with auto-sync |
| `gaget` | Get Annex files from remotes with auto-sync |
| `gamove` | Move Annex files between repositories |
| `gasync` | Full Git Annex synchronization across all configured remotes |
| `git-purge-from-annex` | Convert Git-tracked files to Git Annex |
| `git-unlfs` | Convert Git LFS pointers back to actual files |

**Key Dependencies:** git, git-annex, ssh

---

### 4. Email Management (10 scripts)

Email inbox management, deduplication, and mailbox operations.

| Script | Purpose |
|--------|---------|
| `imapdedup` | IMAP mailbox deduplication wrapper (Dovecot IMAP) |
| `imapdedup.py` | Python implementation of IMAP deduplication |
| `startmail` | Start mail service/server |
| `stopmail` | Stop mail service/server |
| `learn_ham` | Train spam filter with ham (good email) samples |
| `move-mail` | Move emails between mailboxes |
| `rename-mailbox.sh` | Rename IMAP mailbox |
| `convert-mail` | Convert mail format between mdbox and maildir |
| `delete_message.py` | Delete messages by UID from IMAP mailbox |
| `list_message_ids.py` | List message IDs from IMAP mailbox |

**Key Dependencies:** dovecot, imaplib (Python), pass (credentials)

---

### 5. File & Storage Management (12 scripts)

File operations, checksums, cleanup, and compression.

| Script | Purpose |
|--------|---------|
| `checksum` | Comprehensive checksum management tool (SHA256, Blake3, etc.) with parallel processing |
| `clean` | Remove build artifacts (Cabal, Cargo, Python, etc.) with dry-run option |
| `cleanold` | Remove old ZFS snapshots keeping only latest 2 |
| `clearempty.py` | Remove empty ZFS snapshots based on 'used' property |
| `trash` | Safe file deletion to trash directory with duplicate handling |
| `remove-dups` | Remove duplicate files based on hash |
| `find_duplicates.py` | Find duplicates with directory priority preferences |
| `compact` | Compact macOS disk images |
| `compact-sparse` | Compact sparse disk images with battery optimization |
| `breaklinks` | Break hardlinks and create independent copies |
| `dropunused` | Drop unused Git Annex data |
| `bundleit` | Bundle directories into compressed tarballs |

**Key Dependencies:** OpenSSL, blake3/b3sum, hdiutil, tar/xz

---

### 6. System Administration (13 scripts)

System-level operations, monitoring, and configuration.

| Script | Purpose |
|--------|---------|
| `zfs-cleanup` | Clean up empty ZFS snapshots |
| `zfs-local` | Manage local ZFS snapshots |
| `zfs-overridden` | Find ZFS properties that have been overridden |
| `zfs-transfer` | Transfer ZFS snapshots between systems |
| `mkzfs` | Create ZFS pool with optimized settings |
| `mkramdisk` | Create RAM disk for temporary storage |
| `clear-semaphores` | Clear all IPC semaphores |
| `cleardns` | Clear pdnsd DNS cache |
| `cpu-temperature` | Report CPU temperature via powermetrics |
| `fix-vmware-vpn` | Fix VMware VPN NAT rules |
| `setdockerdns` | Configure Docker DNS settings |
| `throttle` | System throttling control |
| `idletime` | Report system idle time in seconds |

**Key Dependencies:** zfs, hdiutil, sudo, pdnsd, powermetrics

---

### 7. Network Utilities (7 scripts)

Network operations and cloud service interactions.

| Script | Purpose |
|--------|---------|
| `ipaddr` | Display system IP addresses |
| `routerip` | Display router IP address |
| `gateway` | Display gateway IP (from netstat) |
| `ports` | Display listening network ports |
| `quickping` | Quick ping test to check connectivity |
| `runningping` | Continuous ping monitoring |
| `cloudflare-dns-record-id` | Query Cloudflare DNS record IDs |
| `cloudflare-gettoken` | Retrieve Cloudflare tunnel token |

**Key Dependencies:** netstat, ping, curl, Cloudflare API

---

### 8. Development Tools (7 scripts)

Development workflow and code analysis tools.

| Script | Purpose |
|--------|---------|
| `mktags` | Generate GNU Global tags files for C/C++/Haskell code |
| `epylint` | Python linting wrapper using pylint |
| `start-hackage` | Start local Hackage server |
| `hackage-upload` | Upload Haskell packages to Hackage |
| `run-python-with-requirements` | Run Python scripts with automatic dependency management |
| `simplify-imports` | Simplify Python import statements |
| `ygrep` | Ruby-based grep with enhanced pattern matching |

**Key Dependencies:** GNU Global, pylint, Cabal (Haskell), Python

---

### 9. Media & Photos (10 scripts)

Audio/video processing and photo management.

| Script | Purpose |
|--------|---------|
| `photoname` | Rename photos based on EXIF metadata |
| `extract-audio` | Extract audio from video files to M4A |
| `images` | Find image files (JPEG, PNG, RAW, HEIC, etc.) |
| `videos` | Find video files |
| `clip` | Cut video/audio clips using FFmpeg |
| `combine` | Combine separate video and audio streams |
| `combine-all` | Batch combine DASH format videos |
| `double-image` | Double the size of a disk image |
| `getphotos` | Download and organize photos from cameras/cards |
| `import-photos` | Import photos with renaming |

**Key Dependencies:** FFmpeg, ffprobe, exifdata

---

### 10. Data Processing (3 scripts)

Text and data manipulation utilities.

| Script | Purpose |
|--------|---------|
| `field` | Extract specific field from text using awk |
| `uniqify` | Remove duplicate entries while preserving order |
| `only-in-second-by-key.sh` | Find records in second file not in first (by key) |

**Key Dependencies:** awk, sort, uniq

---

### 11. Text & File Utilities (8 scripts)

Download, search, and file transfer tools.

| Script | Purpose |
|--------|---------|
| `ack` | High-performance code search using ripgrep (rg) |
| `grab` | Download videos/media using youtube-dl |
| `download` | Download files with version selection (Firefox, etc.) |
| `mirror` | Mirror remote directories/websites |
| `upload` | Upload files to remote servers |
| `attach` | Create tmux session with macOS native tabs |
| `notify` | Send system notifications |
| `resolve` | Resolve domain names |

**Key Dependencies:** ripgrep, youtube-dl, rsync, curl

---

### 12. Cloud Integration & Cryptocurrency (6 scripts)

Cloud services and financial data tools.

| Script | Purpose |
|--------|---------|
| `ada` | Interact with Cardano (ADA) blockchain via Quill |
| `ic` | Interact with Internet Computer (ICP) blockchain via Quill |
| `dfn` | DeFi/finance operations using Quill |
| `getquote` | Get financial quotes via Finance::Quote (Perl) |
| `weight` | Track weight measurements |
| `uv-index` | Get UV index data |

**Key Dependencies:** quill (blockchain CLI), Perl Finance::Quote module

---

### 13. Emacs & Editor Integration (7 scripts)

Emacs and editor configuration tools.

| Script | Purpose |
|--------|---------|
| `configure-emacs` | Configure Emacs build with imagemagick and tree-sitter |
| `org-lint-emacs` | Lint Emacs Org files |
| `marked` | Open file in Marked.app (macOS) |
| `tidify` | Tidy up Org mode files |
| `texinfo-update` | Update Texinfo documentation |
| `hpc-report` | Generate Haskell code coverage reports |
| `coq-unused` | Find unused definitions in Coq code |

**Key Dependencies:** Emacs, Org mode, Haskell/Cabal, Coq

---

### 14. Work/Productivity (12 scripts)

Session management, issue tracking, and productivity tools.

| Script | Purpose |
|--------|---------|
| `spawn` | Create git worktree and tmux session with Claude |
| `start` | Boot sequence (push, brew update/upgrade, start apps) |
| `start-apps` | Start macOS applications |
| `start-ghcid` | Start Haskell ghcid development tool |
| `new-session` | Create new tmux session |
| `sessions` | List active tmux sessions |
| `ready` | Check system readiness |
| `small-issues` | Find and work on small GitHub issues |
| `missing-meetings` | Find meetings not in calendar |
| `topic` | Display/manage topic information |
| `redflags` | Find red flag issues/problems |
| `prepare-checks` | Prepare system for testing |

**Key Dependencies:** git, tmux, Claude CLI, gh (GitHub CLI)

---

### 15. System Status & Monitoring (8 scripts)

System information and monitoring utilities.

| Script | Purpose |
|--------|---------|
| `status` | Display ZFS pool status |
| `l` | Git log wrapper |
| `w` | Show disk/filesystem usage |
| `dh` | Display ZFS filesystem space usage and stats |
| `ncpu` | Show number of CPUs |
| `now` | Display current time/date |
| `ss` | Show network/socket statistics |
| `report` | Generate system status report |

**Key Dependencies:** zfs, git, df/du

---

### 16. System Configuration & NixOS (8 scripts)

NixOS and system configuration management.

| Script | Purpose |
|--------|---------|
| `nixos` | Update NixOS configuration from vulcan |
| `update` | Fetch all git repositories with tags |
| `update-and-pull` | Update and pull from git repositories |
| `update.locate` | Update mlocate database |
| `workspace-update` | Update workspace configuration |
| `aider.sh` | Aider AI coding assistant CLI |
| `huggingface-cli` | Hugging Face CLI with model management |
| `da` | Run direnv allow |

**Key Dependencies:** NixOS, git, direnv, uvx

---

### 17. SSH & Remote Access (5 scripts)

SSH and remote connection utilities.

| Script | Purpose |
|--------|---------|
| `sshpw` | SSH with password input |
| `gohome` | SSH tunnel to home network |
| `k` | Kubernetes CLI shortcut |
| `n` | Node.js version/environment wrapper |
| `getpass` | Retrieve password from pass manager with retry logic |

**Key Dependencies:** ssh, pass (password manager), kubectl, nvm

---

### 18. Database & Query Tools (6 scripts)

Database operations and query interfaces.

| Script | Purpose |
|--------|---------|
| `sqlite` | SQLite database interface |
| `mssql-attach-srp` | Attach SQL Server database with SRP |
| `mssql-kick` | Remove SQL Server locks |
| `rmbox` | Remove mailbox from database |
| `mailboxes` | List available mailboxes |
| `hazel` | Hazel automation rules manager |

**Key Dependencies:** sqlite3, SQL Server tools

---

### 19. File Format Conversion (6 scripts)

Convert and process various file formats.

| Script | Purpose |
|--------|---------|
| `clean-csv` | Clean and deduplicate CSV files |
| `bzdmg` | Convert disk images to bzip2 compression |
| `dmgdir` | Convert directory to compressed disk image |
| `tardir` | Convert directory to compressed tar.xz archive |
| `mac-bundle-exe.sh` | Bundle executable into macOS .app bundle |
| `hp2csv.awk` | Convert HP profiling data to CSV |

**Key Dependencies:** hdiutil, tar, xz, awk

---

### 20. Git Operations & Repository Tools (4 scripts)

Advanced git repository management.

| Script | Purpose |
|--------|---------|
| `b` | Simple git branch shortcut |
| `repoize` | Convert directory to git repository |
| `create-iso.sh` | Create macOS installation ISO |
| `create-login.sh` | Create login entry using 1Password |

**Key Dependencies:** git, gh (GitHub CLI), jq

---

### 21. Testing & Validation (4 scripts)

Code testing and validation tools.

| Script | Purpose |
|--------|---------|
| `ct` | Cabal test runner for Haskell projects |
| `hnix-test` | Test Haskell Nix implementation |
| `fsck` | Git Annex filesystem check (non-fatal errors) |
| `snaplog` | Snapshot logging |

**Key Dependencies:** Cabal, git annex, Haskell

---

### 22. Learning & Development (4 scripts)

Learning tools and development utilities.

| Script | Purpose |
|--------|---------|
| `rustdocs` | Open Rust documentation |
| `outofdate` | Find outdated dependencies |
| `already-exists` | Check for existing checksums |
| `average` | Calculate averages from input |

**Key Dependencies:** Rust toolchain

---

### 23. Miscellaneous Utilities (12 scripts)

Various one-off utilities and special-purpose scripts.

| Script | Purpose |
|--------|---------|
| `abspath` | Print absolute path of file |
| `genpass` | Generate random password (32 chars, no ambiguous) |
| `sign` | Sign files/documents |
| `quit` | Quit application (if exists) |
| `tab` | Create new terminal tab |
| `iterm` | Control iTerm2 |
| `whenidle` | Run command when system is idle |
| `wipe-history` | Wipe shell history |
| `wipe-old-history` | Wipe old history entries |
| `tube` | Tube utility (unclear purpose) |
| `perf` | Performance profiling |
| `retire` | Retire/decommission system |

**Key Dependencies:** iTerm2, terminal utilities

---

### 24. System Operations & Utilities (5+ scripts)

Additional system operation scripts.

| Script | Purpose |
|--------|---------|
| `check-devonthink-urls` | Verify DevonThink item UUIDs |
| `github-org-dl.sh` | Clone all repos from GitHub organization |
| `hive` | Claude Hive Mind spawn interface |
| `mitm` | MITM proxy setup for debugging |
| `vlc-sync` | Synchronize VLC playlists |
| `volcopy` | Volume copy utility |
| `protected-rsync` | rsync with protection flags |
| `kill-safari` | Kill Safari processes |
| `browsers` | List available web browsers |

**Key Dependencies:** DevonThink, GitHub CLI, VLC, rsync

---

## Architecture & Design Patterns

### Shebang Patterns
- Most scripts: `#!/usr/bin/env bash`
- Python scripts: `#!/usr/bin/env python3` or `#!/usr/bin/env python`
- Special scripts: 
  - Zsh: `cleanold`
  - Ruby: `ygrep`
  - Awk: `hp2csv.awk`
  - Nix: `ragflow-cli`

### Error Handling
- Common pattern: `set -euo pipefail` for strict mode
- Variable checks before use
- Exit code checking in critical operations

### Credential Management
- Primary method: `pass` password manager integration
- Used by: AI tools, Git Annex, Email, Backup (B2), Hackage
- Example: `export CLAUDE_CODE_OAUTH_TOKEN=$(pass claude-pro.ai | head -1)`

### Remote Host Support
- Multi-host aware: hera, clio, tank, vulcan
- Host detection: `$(myhost)` or hostname checks
- SSH integration: Remote execution via ssh tunnels
- Path translation: Automatic path conversion between hosts

### Environment Integration
- NixOS/Nix package manager dependencies
- Emacs integration (`.emacs.d` synchronization)
- Org mode workflows
- Git Annex for large file management

---

## Common Dependencies Summary

### Core Tools
- git, git-annex, git-lfs
- bash, zsh, Python 3, Perl, Ruby, Awk
- rsync, ssh, curl, wget
- GNU/BSD utilities (find, grep, awk, sed, etc.)

### File Operations
- tar, xz, gzip, bzip2
- hdiutil (macOS disk images)
- zfs (storage management)

### Development
- Cabal (Haskell)
- Cargo (Rust)
- npm/node
- Python tools (pylint, etc.)
- GNU Global (ctags/etags)

### AI/ML
- Claude CLI
- Hugging Face tools
- MLX (Apple Silicon ML)
- Ollama
- OpenRouter

### System
- ZFS filesystem tools
- NixOS package manager
- tmux
- direnv
- Emacs

### Cloud/Services
- Backblaze B2 CLI
- Cloudflare API
- IMAP (Dovecot)
- SQL Server tools
- Blockchain: quill

### Password & Secrets
- `pass` password manager
- 1Password

---

## Usage Patterns

### Single-Purpose Wrappers
Many scripts are thin wrappers around system commands:
```bash
#!/usr/bin/env bash
exec git l "$@"              # l → git log
exec zpool status -L        # status → zfs pool status
```

### Configuration Helpers
Scripts that set up environment variables and pass credentials:
```bash
export B2_APPLICATION_KEY=$(pass show Passwords/backblaze-secret-key)
```

### Pipeline Builders
Scripts that orchestrate multiple tools:
```bash
git add -A
git ls-files --deleted -z | while read -r file
git commit
```

### Conditional Host Detection
```bash
if [[ $MYHOST == hera ]]; then
    # hera-specific operations
fi
```

---

## Installation & Setup

### Prerequisites
```bash
# Password manager
brew install pass

# Package manager
brew install nix direnv

# Version control
brew install git git-annex

# Development tools
brew install bash zsh python3 perl ruby

# System tools
brew install tmux ffmpeg ripgrep youtube-dl
```

### NixOS Integration
Most scripts are designed to work with NixOS:
- Scripts call `nix-shell` for tool availability
- Tools referenced via `/nix/store/...` paths
- `direnv` integration for automatic environment setup

### Path Setup
Add script directory to PATH:
```bash
export PATH="$HOME/src/scripts:$PATH"
```

---

## Notable Features

### Parallel Processing
- `checksum`: Multi-threaded hash computation
- `gacopy`: Parallel file copies to Git Annex

### Multi-Host Awareness
- Automatic host detection
- SSH tunneling support
- Path translation between hosts
- Conditional logic based on hostname

### Extensive Error Handling
- Pre-flight checks for required tools
- Graceful degradation
- Informative error messages
- Dry-run modes (e.g., `clean -n`)

### Credential Security
- Integration with `pass` password manager
- No hardcoded secrets
- Automatic credential refresh

### Logging & Monitoring
- Backup operations logged to `~/Library/Logs/`
- Status monitoring and health checks
- Performance tracking

---

## Development Notes

### Script Maintenance
- Total lines of code: ~15,000+ (estimated)
- Average script: ~40-100 lines
- Largest scripts: checksum (~300 lines), various wrappers

### Language Migration
- Majority Bash for system integration
- Python for complex data processing
- Perl for specialized text processing

### Testing
- Many scripts have `--help` or `-n` (dry-run) options
- Manual testing typical for system-level operations

---

## Security Considerations

1. **Credential Management**: All scripts use `pass` for secrets, no hardcoded credentials
2. **Sandbox Isolation**: `claude-sandbox` uses firejail for runtime isolation
3. **File Permissions**: Scripts carefully manage file permissions during copy/move operations
4. **SSH Keys**: Uses SSH keys rather than password authentication
5. **MITM Proxy**: Development mode includes optional MITM proxy bypass (careful!)

---

## Performance Optimizations

- **Parallel processing**: ThreadPoolExecutor in checksum script
- **Batch operations**: Git Annex uses batch processing
- **Caching**: ZFS snapshot caching
- **Direct execution**: Many scripts use `exec` to avoid subprocess overhead

---

This repository represents a mature, production-used collection of personal automation tools with strong emphasis on reliability, credential security, and multi-host deployment.
