#!/usr/bin/env python3
"""Engine bootstrap entrypoint.

This script reads an engine or app spec, validates it, and writes generated
files to disk. It is designed to support self-modification and application
scaffolding without requiring manual editing of generated outputs.

Supported capabilities:
- engine self-rewrite from spec
- application generation from init spec
- multi-file project output
- validator layer
- iterative refinement

Design goals:
- Preserve OpenAI Responses API compatibility by keeping the implementation
  independent of any specific client/runtime contract.
- Preserve GitHub Actions bootstrap by providing a simple CLI entrypoint that
  can be invoked from CI.
- Use safe relative paths only.
- Generate full files only.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SPEC_CANDIDATES = (
    PROJECT_ROOT / "engine" / "spec.json",
    PROJECT_ROOT / "spec.json",
    PROJECT_ROOT / "engine" / "bootstrap.spec.json",
)


class SpecError(RuntimeError):
    pass


@dataclasses.dataclass(frozen=True)
class FileSpec:
    path: str
    content: str


@dataclasses.dataclass(frozen=True)
class EngineSpec:
    kind: str
    files: Tuple[FileSpec, ...]
    overwrite: bool = True
    dry_run: bool = False


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _is_safe_relative_path(p: str) -> bool:
    if not p or p.strip() != p:
        return False
    normalized = Path(p)
    if normalized.is_absolute():
        return False
    parts = normalized.parts
    if any(part in ("..", "") for part in parts):
        return False
    return True


def _resolve_safe_path(relative_path: str) -> Path:
    if not _is_safe_relative_path(relative_path):
        raise SpecError(f"Unsafe relative path: {relative_path!r}")
    resolved = (PROJECT_ROOT / relative_path).resolve()
    if PROJECT_ROOT not in resolved.parents and resolved != PROJECT_ROOT:
        raise SpecError(f"Path escapes project root: {relative_path!r}")
    return resolved


def _coerce_files(raw_files: Any) -> Tuple[FileSpec, ...]:
    if not isinstance(raw_files, list):
        raise SpecError("Spec field 'files' must be a list")
    files: List[FileSpec] = []
    for idx, item in enumerate(raw_files):
        if not isinstance(item, dict):
            raise SpecError(f"Spec file entry {idx} must be an object")
        path = item.get("path")
        content = item.get("content")
        if not isinstance(path, str) or not isinstance(content, str):
            raise SpecError(f"Spec file entry {idx} must have string 'path' and 'content'")
        if path.startswith(".github/workflows/"):
            # Preserve GitHub Actions bootstrap: this engine may write the required
            # bootstrap workflow if explicitly requested, but we avoid generating
            # arbitrary workflow files.
            if path != ".github/workflows/bootstrap.yml":
                raise SpecError("Generation of .github/workflows/* is restricted")
        if not _is_safe_relative_path(path):
            raise SpecError(f"Unsafe file path in spec: {path!r}")
        files.append(FileSpec(path=path, content=content))
    return tuple(files)


def load_spec_from_path(path: Path) -> EngineSpec:
    try:
        raw = json.loads(_read_text(path))
    except FileNotFoundError as exc:
        raise SpecError(f"Spec file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SpecError(f"Invalid JSON spec at {path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise SpecError("Top-level spec must be a JSON object")

    kind = raw.get("kind", "engine")
    if not isinstance(kind, str):
        raise SpecError("Spec field 'kind' must be a string")

    overwrite = raw.get("overwrite", True)
    dry_run = raw.get("dry_run", False)
    if not isinstance(overwrite, bool) or not isinstance(dry_run, bool):
        raise SpecError("Spec fields 'overwrite' and 'dry_run' must be booleans")

    files = _coerce_files(raw.get("files", []))
    return EngineSpec(kind=kind, files=files, overwrite=overwrite, dry_run=dry_run)


def load_spec(spec_path: Optional[str]) -> EngineSpec:
    if spec_path:
        return load_spec_from_path(_resolve_safe_path(spec_path))

    for candidate in DEFAULT_SPEC_CANDIDATES:
        if candidate.exists():
            return load_spec_from_path(candidate)

    # Minimal fallback: preserve bootstrap behavior by generating nothing if no
    # spec is present, but still succeed.
    return EngineSpec(kind="engine", files=(), overwrite=True, dry_run=True)


def validate_spec(spec: EngineSpec) -> None:
    for file_spec in spec.files:
        if file_spec.path == ".github/workflows/bootstrap.yml":
            # Explicitly allowed required bootstrap workflow.
            continue
        if file_spec.path.startswith(".github/workflows/"):
            raise SpecError("Workflow generation is restricted to bootstrap.yml only")
        if not _is_safe_relative_path(file_spec.path):
            raise SpecError(f"Unsafe path: {file_spec.path!r}")


def apply_spec(spec: EngineSpec) -> List[str]:
    written: List[str] = []
    for file_spec in spec.files:
        target = _resolve_safe_path(file_spec.path)
        if target.exists() and not spec.overwrite:
            continue
        if spec.dry_run:
            written.append(file_spec.path)
            continue
        _write_text(target, file_spec.content)
        written.append(file_spec.path)
    return written


def build_report(spec: EngineSpec, written: Iterable[str]) -> Dict[str, Any]:
    written_list = list(written)
    return {
        "kind": spec.kind,
        "dry_run": spec.dry_run,
        "overwrite": spec.overwrite,
        "requested_files": [dataclasses.asdict(f) for f in spec.files],
        "written_files": written_list,
        "count": len(written_list),
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Bootstrap the software factory engine")
    parser.add_argument("--spec", help="Relative path to a JSON spec file", default=None)
    parser.add_argument("--emit-report", action="store_true", help="Print a JSON report to stdout")
    parser.add_argument("--strict", action="store_true", help="Fail if no files are generated")
    args = parser.parse_args(argv)

    try:
        spec = load_spec(args.spec)
        validate_spec(spec)
        written = apply_spec(spec)
        if args.strict and not written:
            raise SpecError("No files were generated")
        if args.emit_report:
            print(json.dumps(build_report(spec, written), indent=2, sort_keys=True))
        return 0
    except SpecError as exc:
        print(f"bootstrap error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"unexpected error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
