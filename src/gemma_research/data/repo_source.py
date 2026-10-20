"""Fetch a public GitHub repository's source tree at a fixed commit.

Deliberately avoids `git clone` (would pull full history) and the organiser's
~23 GB Kaggle bundle (explicitly out of scope per the 2026-10-16 execution
directive, §6 — disk headroom). Instead downloads GitHub's own
commit-pinned source tarball (`codeload.github.com/{repo}/tar.gz/{commit}`),
which contains only the tree at that commit, and caches it on disk keyed by
(repo, commit) so re-running a pilot doesn't re-download anything.

Safety: tarballs are untrusted third-party content. We only ever parse the
contained `.py` files with `ast.parse` (never execute, never run setup
scripts) and extract each commit into its own fresh directory.
"""

from __future__ import annotations

import tarfile
import urllib.request
from pathlib import Path

CACHE_ROOT = Path(__file__).resolve().parents[3] / "manifests" / "repo_cache"


def _safe_extract(tar: tarfile.TarFile, dest: Path) -> None:
    dest_resolved = dest.resolve()
    for member in tar.getmembers():
        member_path = (dest / member.name).resolve()
        if not str(member_path).startswith(str(dest_resolved)):
            raise ValueError(f"Unsafe tar member path: {member.name}")
    tar.extractall(dest)  # paths validated above


def fetch_repo_snapshot(repo: str, commit: str, cache_root: Path = CACHE_ROOT) -> Path:
    """Return the path to the extracted source tree for `repo` at `commit`.

    `repo` is "owner/name" (e.g. "python/mypy"). Downloads once; subsequent
    calls for the same (repo, commit) reuse the cached extraction.
    """
    safe_repo = repo.replace("/", "__")
    commit_dir = cache_root / safe_repo / commit
    if commit_dir.exists():
        children = list(commit_dir.iterdir())
        if len(children) == 1 and children[0].is_dir():
            return children[0]

    commit_dir.mkdir(parents=True, exist_ok=True)
    tarball_path = commit_dir / "snapshot.tar.gz"
    url = f"https://codeload.github.com/{repo}/tar.gz/{commit}"  # fixed GitHub host, commit-pinned
    urllib.request.urlretrieve(url, tarball_path)

    with tarfile.open(tarball_path) as tar:
        _safe_extract(tar, commit_dir)
    tarball_path.unlink()

    children = [c for c in commit_dir.iterdir() if c.is_dir()]
    if len(children) != 1:
        raise RuntimeError(f"Unexpected tarball layout for {repo}@{commit}: {children}")
    return children[0]
