#!/usr/bin/env bash
# Installs the GCP/Bruin CLI tooling the pipeline needs (see TD-36 in
# docs/02-architecture/technical-debt-inventory.md), so a fresh Codespace
# doesn't require a manual one-off install that gets lost on rebuild.
set -euo pipefail

if ! command -v gcloud >/dev/null 2>&1; then
  echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" \
    | sudo tee /etc/apt/sources.list.d/google-cloud-sdk.list >/dev/null
  curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg \
    | sudo gpg --yes --dearmor -o /usr/share/keyrings/cloud.google.gpg
  # Scope the update to just the list we added: unrelated pre-existing repos
  # on the base image (e.g. yarnpkg) can have broken signing keys and would
  # otherwise fail the whole `apt-get update`.
  sudo apt-get update -y -o Dir::Etc::sourcelist="sources.list.d/google-cloud-sdk.list" -o Dir::Etc::sourceparts="-" -o APT::Get::List-Cleanup="0"
  sudo apt-get install -y google-cloud-cli
fi

if ! command -v bruin >/dev/null 2>&1; then
  curl -LsSf https://getbruin.com/install/cli | sh
fi

pip install --user "google-cloud-bigquery==3.41.0"

echo "gcloud: $(gcloud --version | head -1)"
echo "bq: $(bq version)"
echo "bruin: $(bruin version | head -1)"
