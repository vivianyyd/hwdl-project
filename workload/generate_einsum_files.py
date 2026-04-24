#!/usr/bin/env python3
"""Generate per-einsum workload YAML files from full workload specs."""

from __future__ import annotations

import argparse
import copy
from pathlib import Path

from ruamel.yaml import YAML


def _load_yaml(path: Path) -> tuple[YAML, dict]:
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=2, offset=2)
    yaml.width = 4096
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} does not contain a YAML mapping at the root.")
    return yaml, data


def _einsums_from(data: dict, path: Path) -> list[dict]:
    workload = data.get("workload")
    if not isinstance(workload, dict):
        raise ValueError(f"{path} is missing a 'workload' mapping.")
    einsums = workload.get("einsums")
    if not isinstance(einsums, list) or not einsums:
        raise ValueError(f"{path} is missing a non-empty 'workload.einsums' list.")
    return einsums


def _resolve_full_paths(inputs: list[Path], full_name: str) -> list[Path]:
    full_paths: list[Path] = []
    for input_path in inputs:
        if input_path.is_dir():
            full_path = input_path / full_name
        else:
            full_path = input_path
        if not full_path.exists():
            raise FileNotFoundError(f"Full workload file not found: {full_path}")
        full_paths.append(full_path)
    return full_paths


def generate_einsum_files(full_path: Path, overwrite: bool) -> int:
    yaml, data = _load_yaml(full_path)
    einsums = _einsums_from(data, full_path)
    output_dir = full_path.parent
    created = 0
    for einsum in einsums:
        if not isinstance(einsum, dict) or "name" not in einsum:
            raise ValueError(f"{full_path} has an einsum entry without a name.")
        name = str(einsum["name"])
        output_path = output_dir / f"{name}.yaml"
        if output_path.exists() and not overwrite:
            continue
        new_data = copy.deepcopy(data)
        new_data["workload"]["einsums"] = [copy.deepcopy(einsum)]
        with output_path.open("w", encoding="utf-8") as handle:
            yaml.dump(new_data, handle)
        created += 1
    return created


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate per-einsum YAML files from a full workload YAML (full.yaml). "
            "Pass directories or full workload file paths."
        )
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        help="Directories containing full.yaml or paths to full workload files.",
    )
    parser.add_argument(
        "--full-name",
        default="full.yaml",
        help="Full workload filename to look for in input directories (default: full.yaml).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing per-einsum YAML files.",
    )
    args = parser.parse_args()

    full_paths = _resolve_full_paths(args.inputs, args.full_name)
    total_created = 0
    for full_path in full_paths:
        total_created += generate_einsum_files(full_path, args.overwrite)
    print(f"Generated {total_created} einsum workload file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
