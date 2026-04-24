from __future__ import annotations

import re
from pathlib import Path


def generate_scaled_memory_yaml(prefix: str, memory_name: str, n: int) -> Path:
    base_path = Path(f"{prefix}.yaml")
    if not base_path.exists():
        raise FileNotFoundError(f"Missing base YAML file: {base_path}")

    output_path = base_path.with_name(f"{base_path.stem}-{n}.yaml")
    if output_path.exists():
        return output_path

    lines = base_path.read_text().splitlines(keepends=True)

    in_memory_block = False
    target_memory_active = False
    memory_indent = None
    found_target = False
    size_updated = False
    size_pattern = re.compile(r"^(\s*size:\s*)(.*)$")

    for index, line in enumerate(lines):
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        if stripped.startswith("- !"):
            if target_memory_active and memory_indent is not None and indent <= memory_indent:
                target_memory_active = False
            in_memory_block = stripped.startswith("- !Memory")
            memory_indent = indent if in_memory_block else None
            target_memory_active = False
            continue

        if not in_memory_block:
            continue

        if stripped.startswith("name:"):
            name_value = stripped.split("name:", 1)[1].strip()
            target_memory_active = name_value == memory_name
            if target_memory_active:
                found_target = True
            continue

        if target_memory_active:
            line_body = line.rstrip("\n")
            line_ending = "\n" if line.endswith("\n") else ""
            match = size_pattern.match(line_body)
            if match:
                lines[index] = f"{match.group(1)}{n} * {match.group(2)}{line_ending}"
                size_updated = True
                break

    if not found_target:
        raise ValueError(f"Memory '{memory_name}' not found in {base_path}")
    if not size_updated:
        raise ValueError(f"No size found for memory '{memory_name}' in {base_path}")

    output_path.write_text("".join(lines))
    return output_path
