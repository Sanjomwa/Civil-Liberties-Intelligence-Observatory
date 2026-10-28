#!/usr/bin/env bash
# TD-132: installs the public-docs content check (check_public_docs.py) as this
# clone's git pre-commit hook. Safe to re-run. Runs automatically when a
# Codespace is created (.devcontainer/devcontainer.json, postCreateCommand).
# On any other clone, run it by hand from anywhere inside the repo:
#   bash Bruin/scripts/content_check/install_hook.sh
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
HOOK="$(git rev-parse --git-path hooks)/pre-commit"

if [ -f "$HOOK" ] && ! grep -q "check_public_docs.py" "$HOOK"; then
  echo "install_hook: $HOOK already exists and isn't the TD-132 content check; leaving it alone." >&2
  echo "install_hook: to add the check by hand, put this line in it: python3 Bruin/scripts/content_check/check_public_docs.py" >&2
  exit 1
fi

mkdir -p "$(dirname "$HOOK")"
cat > "$HOOK" <<'HOOK_EOF'
#!/usr/bin/env bash
# Installed by Bruin/scripts/content_check/install_hook.sh (TD-132). Re-run that script to reinstall.
exec python3 "$(git rev-parse --show-toplevel)/Bruin/scripts/content_check/check_public_docs.py"
HOOK_EOF
chmod +x "$HOOK"
echo "install_hook: content check installed at $HOOK"

if ! python3 -c "import yaml" >/dev/null 2>&1; then
  echo "install_hook: PyYAML is missing (the check reads sensitive_terms.yml); installing it."
  python3 -m pip install --user --quiet pyyaml
fi

if [ ! -f Bruin/scripts/content_check/sensitive_terms.local.yml ]; then
  echo "install_hook: note: sensitive_terms.local.yml isn't in this clone. The check will use the public denylist only until it's recreated by hand (it's gitignored on purpose)."
fi
