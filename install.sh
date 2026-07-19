#!/usr/bin/env bash
# One-line installer for the Hyperagent → OpenAI gateway.
#   curl -fsSL https://raw.githubusercontent.com/dinhhung893/hyperagent-openai-gateway/main/install.sh | bash
# Installs the `hyperagent-gateway` (alias `hga`) CLI via pipx (preferred),
# uv, or pip, then scaffolds ~/.hyperagent-gateway/.env.
set -euo pipefail

REPO="git+https://github.com/dinhhung893/hyperagent-openai-gateway"
HOME_DIR="${HOME}/.hyperagent-gateway"

say() { printf '\033[1;36m%s\033[0m\n' "$*"; }

install_cli() {
  if command -v pipx >/dev/null 2>&1; then
    say "Installing with pipx…"; pipx install "$REPO" --force
  elif command -v uv >/dev/null 2>&1; then
    say "Installing with uv…"; uv tool install "$REPO"
  else
    say "pipx/uv not found — installing with pip (user)…"
    python3 -m pip install --user --upgrade "$REPO"
  fi
}

scaffold_env() {
  mkdir -p "$HOME_DIR"
  local env_file="$HOME_DIR/.env"
  if [ -f "$env_file" ]; then
    say "Keeping existing $env_file"
    return
  fi
  cat > "$env_file" <<EOF
GATEWAY_UPSTREAM=mcp
HYPERAGENT_MCP_URL=https://hyperagent.com/api/mcp
SHIM_API_KEYS=sk-local-$(head -c6 /dev/urandom | od -An -tx1 | tr -d ' \n')
GATEWAY_PORT=8000
EOF
  chmod 600 "$env_file"
  say "Wrote $env_file"
}

install_cli
scaffold_env
say "Done. Next steps:"
echo "  hga login     # one-time Hyperagent sign-in"
echo "  hga serve     # start the gateway on http://localhost:8000/v1"
echo "  (or 'hga quickstart' to do both)"
