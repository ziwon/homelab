# Coding Style Rules

## General Principles

- **All comments must be written in English**
- Keep comments concise and meaningful
- Avoid obvious comments that just repeat the code

## YAML Files

### Indentation
- 2 spaces (no tabs)
- Nested blocks must be consistently aligned

### Strings
```yaml
# Plain strings - no quotes
name: myapp
namespace: default

# Special characters - use quotes
description: "This is a: special string"
command: "echo 'hello world'"

# Multiline - literal block
script: |
  #!/bin/bash
  set -e
  echo "Starting..."

# Long string folding
description: >
  This is a very long description
  that spans multiple lines but
  will be joined into one line.
```

### Numbers and Versions
```yaml
# Versions are always strings
version: "1.0.0"
targetRevision: "3.2.1"

# Ports are numbers
port: 8080
replicas: 3
```

## Helm Values

### Environment Separation
```
values/
├── default.yaml      # Common defaults
├── home.yaml         # Home environment
└── cloud.yaml        # Cloud environment
```

### gotmpl Usage
```yaml
# home.yaml.gotmpl
domain: {{ .Values.domain | default "home.lab" }}
replicas: {{ .Values.replicas | default 1 }}
```

## Shell Scripts

### Shebang and Options
```bash
#!/usr/bin/env bash
set -euo pipefail
```

### Variables
```bash
# Uppercase with underscores
NAMESPACE="default"
POD_NAME="myapp"

# Local variables use local keyword
local result=$(kubectl get pods)
```

### Preferred Tools
| Instead of | Use | Reason |
|------------|-----|--------|
| `grep` | `rg` (ripgrep) | Faster, respects .gitignore |
| `find` | `fd` | Faster, simpler syntax |
| `cat` | `bat` | Syntax highlighting (optional) |
| `ls` | `eza` / `lsd` | Better formatting (optional) |

```bash
# Example: search for pattern
rg "pattern" --type yaml

# Example: find files
fd "\.yaml$" platform/
```

## Python (Ray/Feast related)

### Type Hints Required
```python
def process_data(input_path: str, output_path: str) -> bool:
    ...
```

### Formatters
- black (line length: 100)
- isort (import sorting)
- ruff (linter)

## Comment Rules

### Language
- **All comments must be in English** (no exceptions)
- Use clear, professional English

### YAML Comments
```yaml
# Add comments only for complex configurations
# Self-explanatory settings need no comments

# GPU resources - based on RTX 5080 16GB
resources:
  limits:
    nvidia.com/gpu: "1"
```

### Code Comments
```python
# TODO: Needs improvement later
# FIXME: Bug fix required
# NOTE: Important reference
# HACK: Temporary workaround
```

### Comment Guidelines
- Explain "why", not "what"
- Keep comments up-to-date with code changes
- Remove commented-out code before committing

## File Naming

| Type | Pattern | Example |
|------|---------|---------|
| K8s manifests | `{name}.yaml` | `redis.yaml` |
| Helm values | `{env}.yaml` | `home.yaml` |
| gotmpl | `{name}.yaml.gotmpl` | `home.yaml.gotmpl` |
| Shell | `{action}.sh` | `entrypoint.sh` |
| Python | `{module}.py` | `feature_store.py` |

## Git Commit Messages

- Write in English
- Use imperative mood: "Add feature" not "Added feature"
- Keep first line under 50 characters
- Reference issue numbers when applicable
