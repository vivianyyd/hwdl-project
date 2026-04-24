from __future__ import annotations

import re
from pathlib import Path

SIZE_PATTERN = re.compile(r"^(\s*size:\s*)(.*\S)(\s*)$")


def _strip_quotes(value: str) -> str:
    if value.startswith(("'", '"')) and value.endswith(("'", '"')):
        return value[1:-1]
    return value


def generate_scaled_memory_yaml(
    prefix: str,
    memory_multipliers: list[tuple[str, int]],
) -> Path:
    """Create a new YAML file with scaled memory size entries.

    The size line is rewritten as `size: <multiplier> * <original>`, preserving
    existing arithmetic expressions used by the YAML configuration. The original
    size expression is wrapped in parentheses to preserve evaluation order when
    applying the multiplier. The output filename suffix is the multiplier for a
    single entry, or name/multiplier pairs joined by "-" for multiple entries.

    Args:
        prefix: Path prefix (without extension) for the source YAML file.
        memory_multipliers: List of (memory name, multiplier) pairs to scale.

    Returns:
        Path to the newly created YAML file, or the existing file if present.

    Raises:
        FileNotFoundError: If the source YAML file does not exist.
        ValueError: If the target memory node or its size entry is missing,
            if no memories are provided, or if a memory appears more than once.
    """
    if not memory_multipliers:
        raise ValueError("At least one memory multiplier pair is required.")

    multipliers_by_name: dict[str, int] = {}
    for name, multiplier in memory_multipliers:
        if name in multipliers_by_name:
            raise ValueError(f"Duplicate memory entry for '{name}'.")
        multipliers_by_name[name] = multiplier

    base_path = Path(f"{prefix}.yaml")
    if not base_path.exists():
        raise FileNotFoundError(f"Missing base YAML file: {base_path}")

    if len(memory_multipliers) == 1:
        suffix = str(memory_multipliers[0][1])
    else:
        suffix = "-".join(
            f"{name}-{multiplier}" for name, multiplier in memory_multipliers
        )
    output_path = base_path.with_name(f"{base_path.stem}-{suffix}.yaml")
    if output_path.exists():
        return output_path

    lines = base_path.read_text(encoding="utf-8").splitlines(keepends=True)

    in_memory_block = False
    target_memory_active = False
    active_memory: str | None = None
    found_targets: set[str] = set()
    updated_targets: set[str] = set()
    for index, line in enumerate(lines):
        stripped = line.lstrip()

        if stripped.startswith("- !"):
            if target_memory_active and active_memory and active_memory not in updated_targets:
                raise ValueError(f"No size found for memory '{active_memory}' in {base_path}")

            in_memory_block = stripped.startswith("- !Memory")
            target_memory_active = False
            active_memory = None
            if in_memory_block and "name:" in stripped:
                name_value = _strip_quotes(stripped.split("name:", 1)[1].strip())
                if name_value in multipliers_by_name:
                    target_memory_active = True
                    active_memory = name_value
                    found_targets.add(name_value)
            continue

        if not in_memory_block:
            continue

        if stripped.startswith("name:"):
            name_value = _strip_quotes(stripped.split("name:", 1)[1].strip())
            if name_value in multipliers_by_name:
                target_memory_active = True
                active_memory = name_value
                found_targets.add(name_value)
            else:
                target_memory_active = False
                active_memory = None
            continue

        if target_memory_active and active_memory:
            match = SIZE_PATTERN.match(line)
            if match:
                if active_memory in updated_targets:
                    raise ValueError(
                        f"Multiple size entries found for memory '{active_memory}' in {base_path}"
                    )
                multiplier = multipliers_by_name[active_memory]
                original_size = match.group(2).strip()
                lines[index] = (
                    f"{match.group(1)}{multiplier} * ({original_size}){match.group(3)}"
                )
                updated_targets.add(active_memory)
                continue

    if target_memory_active and active_memory and active_memory not in updated_targets:
        raise ValueError(f"No size found for memory '{active_memory}' in {base_path}")

    missing_targets = [name for name in multipliers_by_name if name not in found_targets]
    if missing_targets:
        raise ValueError(f"Memory entries not found in {base_path}: {', '.join(missing_targets)}")

    output_path.write_text("".join(lines), encoding="utf-8")
    return output_path
