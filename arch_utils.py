from __future__ import annotations

import re
from pathlib import Path

SIZE_PATTERN = re.compile(r"^(\s*size:\s*)(.*)$")


def generate_scaled_memory_yaml(prefix: str, memory_name: str, multiplier: int) -> Path:
    """Create a new YAML file with a scaled memory size entry.

    The size line is rewritten as `size: <multiplier> * <original>`, preserving
    existing arithmetic expressions used by the YAML configuration.

    Args:
        prefix: Path prefix (without extension) for the source YAML file.
        memory_name: Name of the !Memory node whose size should be scaled.
        multiplier: Scale factor inserted after the `size:` field.

    Returns:
        Path to the newly created YAML file, or the existing file if present.

    Raises:
        FileNotFoundError: If the source YAML file does not exist.
        ValueError: If the target memory node or its size entry is missing.
    """
    base_path = Path(f"{prefix}.yaml")
    if not base_path.exists():
        raise FileNotFoundError(f"Missing base YAML file: {base_path}")

    output_path = base_path.with_name(f"{base_path.stem}-{multiplier}.yaml")
    if output_path.exists():
        return output_path

    lines = base_path.read_text().splitlines(keepends=True)

    in_memory_block = False
    target_memory_active = False
    memory_indent = None
    found_target = False
    size_updated = False
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
            match = SIZE_PATTERN.match(line_body)
            if match:
                lines[index] = f"{match.group(1)}{multiplier} * {match.group(2)}{line_ending}"
                size_updated = True
                break

    if not found_target:
        raise ValueError(f"Memory '{memory_name}' not found in {base_path}")
    if not size_updated:
        raise ValueError(f"No size found for memory '{memory_name}' in {base_path}")

    output_path.write_text("".join(lines))
    return output_path
