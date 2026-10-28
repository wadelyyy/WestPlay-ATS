"""Prepare a reviewed source-only file list. Never create an archive or read runtime account stores."""

from fnmatch import fnmatchcase
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
POLICY = json.loads((ROOT / "tools/source-package-policy.json").read_text(encoding="utf-8"))
SECRET_MARKERS = {
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github-token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b"),
    "slack-token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    "service-secret-key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b"),
}


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=ROOT)


def exclusion(path: str) -> str | None:
    file = ROOT / path
    if not file.is_file():
        return "not a current file"
    if file.is_symlink() or not file.resolve().is_relative_to(ROOT):
        return "symlink or path outside the source repository"
    parts = Path(path).parts
    forbidden = {name.casefold() for name in POLICY["denyDirectoryNames"]}
    for index, part in enumerate(parts[:-1]):
        if part.casefold() in forbidden:
            if part == "public" and "/".join(parts[:index + 1]) == POLICY["allowedPublicDirectory"]:
                continue
            return "excluded generated, private, or runtime directory"
    if path in POLICY["licensedOriginalBinaryAssets"]:
        # These upstream assets are needed by include_bytes!, and their permission note stays with them.
        original = git("show", f"HEAD:{path}")
        return None if file.read_bytes() == original else "licensed original asset changed; manual review required"
    if any(fnmatchcase(path.casefold(), glob.casefold()) for glob in POLICY["denyPathGlobs"]):
        return "excluded local metadata, runtime data, binary, or game-derived asset"
    if path in POLICY["allowRootFiles"]:
        return None
    if parts[0] in POLICY["allowDirectories"]:
        return None
    if any(fnmatchcase(path, pattern) for pattern in POLICY["allowDocumentation"]):
        return None
    return "outside source/documentation allowlist"


def main() -> None:
    candidates = sorted(set(path.decode("utf-8") for path in git("ls-files", "--cached", "--others", "--exclude-standard", "-z").split(b"\0") if path))
    selected = []
    excluded = []
    secret_hits = []
    for path in candidates:
        reason = exclusion(path)
        if reason:
            excluded.append({"path": path, "reason": reason})
            continue
        file = ROOT / path
        data = file.read_bytes()
        if b"\0" not in data:
            text = data.decode("utf-8", errors="replace")
            for name, pattern in SECRET_MARKERS.items():
                if pattern.search(text):
                    # Report locations and marker names only, never credential values.
                    secret_hits.append({"path": path, "marker": name})
        selected.append({"path": path, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
    selected_names = {item["path"] for item in selected}
    missing_licenses = [path for path in POLICY["requiredLicenseFiles"] if path not in selected_names]
    report = {"kind": "source-only allowlist audit; no archive created", "candidateCount": len(candidates),
              "selectedCount": len(selected), "files": selected, "excluded": excluded,
              "secretMarkerHits": secret_hits, "missingLicenseFiles": missing_licenses,
              "readyForArchiveReview": not secret_hits and not missing_licenses}
    destination = ROOT / "docs/source-package-audit.json"
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ["candidateCount", "selectedCount", "secretMarkerHits", "missingLicenseFiles", "readyForArchiveReview"]}, ensure_ascii=False))
    print(str(destination))
    if secret_hits or missing_licenses:
        raise SystemExit(1)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
