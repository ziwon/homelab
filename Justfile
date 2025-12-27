set quiet

# Homelab - AI-Driven Kubernetes Platform
# Import submodules

mod claude '.claude'
mod bootstrap 'bootstrap'

default:
    @echo "Homelab Commands"
    @echo ""
    @echo "Modules:"
    @echo "  just claude <cmd>  (or: just c <cmd>)  - AI tools"
    @echo "  just bootstrap <cmd> (or: just b <cmd>) - K3s, Helmfile"
    @echo ""
    @just --list --list-submodules

# ─────────────────────────────────────────────────────────────
# Short aliases
# ─────────────────────────────────────────────────────────────

# just c <recipe> [args] - shortcut for claude module
c *args:
    @just claude {{args}}

# just b <recipe> [args] - shortcut for bootstrap module
b *args:
    @just bootstrap {{args}}
