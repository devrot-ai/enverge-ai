# Security

ForgeLab executes untrusted, agent-generated code. Security is not optional — it is the foundation of the system.

## Core Principle: Fail-Closed

If Docker is unavailable, ForgeLab displays a clear setup error. **It never falls back to executing generated code on the host.** This is non-negotiable.

## Docker Sandbox Security

### Container Policies

| Policy | Setting | Rationale |
|--------|---------|-----------|
| User | Non-root user (UID 1000) | Prevents privilege escalation |
| Network | Disabled (`--network none`) | Prevents data exfiltration and external calls |
| Memory | Configurable limit (default: 512MB) | Prevents resource exhaustion |
| CPU | Configurable limit (default: 1.0) | Prevents resource exhaustion |
| Timeouts | Configurable per-run (default: 300s) | Prevents infinite loops |
| Filesystem | Read-only base, writable workspace only | Limits write access |
| Capabilities | Dropped all, added minimal set | Principle of least privilege |
| Privilege escalation | Prevented (`--security-opt no-new-privileges`) | Blocks setuid/setgid |
| Docker socket | Never mounted | Prevents container escape |

### Container Configuration

```python
# forge/sandbox/policies.py
SandboxPolicy(
    memory_limit="512m",
    cpu_limit=1.0,
    network_mode="none",
    user="1000:1000",
    read_only_root=True,
    no_new_privileges=True,
    cap_drop=["ALL"],
    cap_add=[],
    tmpfs=["/tmp"],
)
```

### Workspace Isolation

- Each run gets a fresh, isolated workspace directory.
- Only the assigned repository is mounted into the container.
- Hidden tests are mounted into a **separate** verification container.
- The agent container **never** has access to hidden test files.
- Reference solutions run in their own isolated workspace.

## Agent Tool Security

### Path Traversal Prevention

All filesystem operations validate that paths remain within the assigned workspace:

```python
def validate_path(workspace: Path, requested_path: str) -> Path:
    resolved = (workspace / requested_path).resolve()
    if not str(resolved).startswith(str(workspace.resolve())):
        raise PathTraversalError(f"Path escapes workspace: {requested_path}")
    return resolved
```

### Tool Allowlist

Agents have access to a controlled set of tools:

| Tool | Purpose | Restrictions |
|------|---------|-------------|
| `list_files` | List directory contents | Workspace-only paths |
| `read_file` | Read file contents | Workspace-only paths |
| `search_code` | Search for patterns | Workspace-only paths |
| `write_file` | Write file contents | Workspace-only paths |
| `run_public_tests` | Execute public tests | Command allowlist |
| `inspect_test_output` | View test results | Read-only |
| `inspect_git_diff` | View code changes | Read-only |
| `finish_task` | Signal completion | No side effects |

**No unrestricted shell access.** The `run_public_tests` tool runs commands from a controlled allowlist inside the sandbox.

### Input Validation

All tool arguments are validated against strict Pydantic schemas before execution.

## Credential Security

- API keys are stored in environment variables, never in code or configuration files.
- API keys are **never** logged.
- API keys are **never** mounted into agent containers.
- API keys are **never** stored in the database.
- `.env.example` provides templates without real credentials.

## Data Security

### Trajectory Storage

Trajectories record all agent interactions but exclude:

- API credentials
- Host secrets
- Hidden test contents
- Reference solutions

### Database

- SQLite database stores metadata and serialized JSON.
- No raw API keys in any table.
- Foreign key constraints enforce referential integrity.

## Infrastructure Security

### Interrupted Runs

- Cleanup handlers ensure containers are stopped and temporary files are deleted.
- Partial runs are recorded with `error` status for debugging.
- No orphaned containers or leaked resources.

### Resource Limits

- Maximum steps per run (configurable, default: 50).
- Maximum execution time per run (configurable, default: 300s).
- Maximum container count (configurable, default: 10).

## Security Checklist

Before running ForgeLab in production:

- [ ] Docker daemon is running and accessible
- [ ] Sandbox policy settings are appropriate for your environment
- [ ] API keys are set via environment variables
- [ ] `.env` file is not committed to version control
- [ ] Database file permissions are restricted
- [ ] Network isolation is verified for agent containers
- [ ] Resource limits are set appropriately
- [ ] Cleanup procedures are tested

## Known Limitations

1. **Docker is required.** Without Docker, ForgeLab cannot execute untrusted code safely.
2. **Host-level attacks.** If the Docker daemon is compromised, container isolation is bypassed. Run ForgeLab on a dedicated machine or VM.
3. **Side-channel attacks.** Timing-based side channels are not mitigated.
4. **Resource exhaustion.** While limits are set, a determined agent may still cause resource pressure through rapid container creation.

## Incident Response

If a security issue is discovered:

1. Stop all running containers: `docker rm -f $(docker ps -aq --filter label=forgelab)`
2. Preserve run artifacts for investigation
3. Review trajectory logs for the affected run
4. Report the issue with reproduction steps
5. Apply the fix and re-run validation
