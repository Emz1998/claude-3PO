# Security Hooks

PreToolUse hooks for security validation and blocking dangerous operations.

## Files

**security.py** - Main security validation hook
- Blocks critical system-damaging commands and paths
- Uses exit code 2 for blocking (hard block)

## Blocked Patterns

**Critical Paths**
- `/etc/passwd`, `/etc/shadow`, `/boot/`, `/sys/`
- SSH keys: `id_rsa`, `id_dsa`, `id_ecdsa`, `id_ed25519`

**Critical Commands**
- `rm -rf /` and variants
- `dd if=/dev/zero of=/dev/` (disk wipe)
- `mkfs.*` (filesystem format)
- Fork bombs
- `chmod 777 /`

## Safe Directories

Operations in these directories are always allowed:
- `/.claude/`
- `/src/`
- `/tests/`

## Usage

The hook reads from stdin and validates:
- `Write`, `Edit`, `MultiEdit` - checks file_path against critical paths
- `Bash` - checks command against dangerous patterns

## Exit Codes

- `0` - Operation allowed
- `2` - Operation blocked (critical security violation)
