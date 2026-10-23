#!/usr/bin/env bash
# Download data_demo/ from Hugging Face into the repository root.
#
#   ./scripts/download_data_demo.sh          # full demo data (~15GB)
#   ./scripts/download_data_demo.sh feicuiwan  # Feicuiwan only (~4.5GB)
#
# Requires: pip install huggingface_hub
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
# The public demo assets live here.  PiLoT-data is the gated training set and
# does not contain data_demo/, so using it can otherwise succeed with 0 files.
REPO="choyaa/PiLoT-demo"
MODE="${1:-all}"

PYTHON_BIN="${PYTHON:-python}"
if ! "$PYTHON_BIN" -c 'import huggingface_hub' &>/dev/null; then
  echo "Install the Hugging Face client: python -m pip install huggingface_hub"
  exit 1
fi

case "$MODE" in
  all|"")
    PATTERNS=("data_demo/**")
    REQUIRED=(
      "data_demo/3dgs_model"
      "data_demo/smbu_model"
      "data_demo/pretrained_model"
    )
    ;;
  feicuiwan)
    PATTERNS=(
      "data_demo/3dgs_model/**"
      "data_demo/pretrained_model/**"
      "data_demo/query/images/3dgs_test/**"
      "data_demo/query/poses/3dgs_test.txt"
      "data_demo/README.md"
    )
    REQUIRED=(
      "data_demo/3dgs_model"
      "data_demo/pretrained_model"
      "data_demo/query/images/3dgs_test"
      "data_demo/query/poses/3dgs_test.txt"
    )
    ;;
  smbu)
    PATTERNS=(
      "data_demo/smbu_model/**"
      "data_demo/pretrained_model/**"
      "data_demo/query/images/smbu_seq2/**"
      "data_demo/query/poses/smbu_seq2.txt"
      "data_demo/README.md"
    )
    REQUIRED=(
      "data_demo/smbu_model"
      "data_demo/pretrained_model"
      "data_demo/query/images/smbu_seq2"
      "data_demo/query/poses/smbu_seq2.txt"
    )
    ;;
  *)
    echo "Usage: $0 [all|feicuiwan|smbu]"
    exit 1
    ;;
esac

echo "Downloading from https://huggingface.co/datasets/$REPO"
echo "Target: $ROOT/data_demo/"
echo "Mode: $MODE"

# PiLoT-demo is stored with Xet.  huggingface_hub 0.36.x sometimes returns
# only README.md in repo_info.siblings for this repository, which makes
# `hf download --include ...` silently skip all Xet files.  Listing the tree
# explicitly provides the complete file list before downloading it.
"$PYTHON_BIN" - "$REPO" "$ROOT" "${PATTERNS[@]}" <<'PY'
import sys
import time
from fnmatch import fnmatch

from huggingface_hub import HfApi, hf_hub_download
from huggingface_hub.hf_api import RepoFile
from requests.exceptions import RequestException

repo_id, local_dir, *patterns = sys.argv[1:]
api = HfApi()
remote_entries = None
last_error = None
for attempt in range(1, 6):
    try:
        remote_entries = list(
            api.list_repo_tree(
                repo_id=repo_id,
                repo_type="dataset",
                path_in_repo="data_demo",
                recursive=True,
            )
        )
        break
    except RequestException as error:
        last_error = str(error)
        if attempt == 5:
            raise SystemExit(
                "Cannot reach Hugging Face after 5 attempts. "
                "Check the network/proxy used by this terminal.\n"
                f"Last error: {last_error}"
            )
        delay = 2 ** (attempt - 1)
        print(
            f"Hugging Face connection failed (attempt {attempt}/5); "
            f"retrying in {delay}s..."
        )
        time.sleep(delay)

files = sorted(
    entry.path
    for entry in remote_entries
    if isinstance(entry, RepoFile)
    and any(fnmatch(entry.path, pattern) for pattern in patterns)
)

if not files:
    raise SystemExit(
        "No remote files matched the requested demo assets. "
        "Check Hugging Face access and the repository layout."
    )

print(f"Resolved {len(files)} files; downloads resume when re-run.")
for index, filename in enumerate(files, start=1):
    print(f"[{index}/{len(files)}] {filename}")
    hf_hub_download(
        repo_id=repo_id,
        filename=filename,
        repo_type="dataset",
        local_dir=local_dir,
    )
PY

has_content() {
  local target="$1"
  if [[ -d "$target" ]]; then
    [[ -n "$(find "$target" -type f -print -quit)" ]]
  else
    [[ -s "$target" ]]
  fi
}

for path in "${REQUIRED[@]}"; do
  if ! has_content "$ROOT/$path"; then
    echo "Download did not produce the expected asset: $path" >&2
    echo "Check access to https://huggingface.co/datasets/$REPO and retry." >&2
    exit 1
  fi
done

echo ""
echo "Download complete."
echo "  Feicuiwan: data_demo/3dgs_model/ + query/images/3dgs_test/"
echo "  SMBU:      data_demo/smbu_model/ + query/images/smbu_seq2/"
echo "  Shared:    data_demo/pretrained_model/"
