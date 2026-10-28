"""
Local file ingestion, chunking, and metadata extractor for Spectre-CLI.
Parses source code, legacy markdown, log archives, and git commits into resurrectable artifacts.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Any, Generator
import subprocess

IGNORE_PATTERNS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv", "env",
    "dist", "build", ".next", ".turbo", ".spectre_cache", "site-packages",
    ".idea", ".vscode", ".DS_Store"
}

ALLOWED_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".rs", ".go", ".c", ".cpp", ".h",
    ".java", ".rb", ".php", ".sh", ".bash", ".md", ".txt", ".log", ".json",
    ".yaml", ".yml", ".toml", ".ini", ".cfg", ".sql"
}


class FileIngestor:
    """
    Crawls and chunks forgotten project repositories, scripts, and logs.
    """

    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 150):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def scan_directory(self, target_dir: Path) -> List[Path]:
        """
        Recursively scans target directory for eligible source files, logs, and docs.
        """
        target_path = Path(target_dir).resolve()
        eligible_files = []

        if target_path.is_file():
            if target_path.suffix.lower() in ALLOWED_EXTENSIONS:
                return [target_path]
            return []

        for root, dirs, files in os.walk(target_path):
            # Prune ignored directories in-place
            dirs[:] = [d for d in dirs if d not in IGNORE_PATTERNS and not d.startswith(".")]

            for file_name in files:
                p = Path(root) / file_name
                if p.suffix.lower() in ALLOWED_EXTENSIONS and p.stat().st_size < 1_000_000:
                    eligible_files.append(p)

        return eligible_files

    def chunk_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Reads a file, analyzes ghost signals (TODOs, deprecations), and splits into chunks.
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception:
            return []

        if not content.strip():
            return []

        stat = file_path.stat()
        mtime = stat.st_mtime
        lines = content.splitlines()

        # Ghost signals detector (abandoned plans, technical debt)
        ghost_signals = []
        for line_no, line in enumerate(lines, 1):
            if re.search(r"\b(TODO|FIXME|HACK|DEPRECATED|ABANDONED|GHOST|TEMP|WIP)\b", line, re.IGNORECASE):
                ghost_signals.append(f"L{line_no}: {line.strip()[:80]}")

        # Sliding window chunking
        chunks = []
        step = max(self.chunk_size - self.chunk_overlap, 100)

        for i in range(0, len(content), step):
            snippet = content[i : i + self.chunk_size].strip()
            if not snippet:
                continue

            chunk_meta = {
                "file_path": str(file_path),
                "file_name": file_path.name,
                "file_type": file_path.suffix,
                "file_size_bytes": stat.st_size,
                "last_modified_timestamp": mtime,
                "total_lines": len(lines),
                "ghost_signals": ghost_signals[:5],
            }

            chunks.append({
                "text": snippet,
                "source_file": str(file_path),
                "chunk_index": len(chunks),
                "metadata": chunk_meta,
            })

        return chunks

    def extract_git_ghosts(self, repo_dir: Path, limit: int = 15) -> List[Dict[str, Any]]:
        """
        Attempts to resurrect forgotten git commit logs if repository is under git control.
        """
        git_dir = Path(repo_dir) / ".git"
        if not git_dir.exists():
            return []

        try:
            cmd = ["git", "-C", str(repo_dir), "log", f"-n{limit}", "--pretty=format:%h|%an|%ad|%s"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=5)
            log_lines = result.stdout.strip().splitlines()

            git_chunks = []
            for idx, line in enumerate(log_lines):
                parts = line.split("|", 3)
                if len(parts) == 4:
                    commit_hash, author, date, subject = parts
                    text = f"Git Commit [{commit_hash}] by {author} on {date}: {subject}"
                    git_chunks.append({
                        "text": text,
                        "source_file": f"{repo_dir}/.git/log",
                        "chunk_index": idx,
                        "metadata": {
                            "type": "git_commit_echo",
                            "hash": commit_hash,
                            "author": author,
                            "date": date,
                        },
                    })
            return git_chunks
        except Exception:
            return []
