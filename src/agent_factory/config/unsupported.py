EXECUTABLE_TOP_LEVEL_SECTIONS = {
    "meta",
    "agent",
    "runtime",
    "tools",
    "permissions",
    "memory",
    "skills",
    "policy",
    "hooks",
    "automation",
    "mcp",
}

MOCKED_TOP_LEVEL_SECTIONS = {
    "workflow",
    "team",
    "notifications",
}


def collect_unsupported_warnings(raw: dict[str, object]) -> tuple[str, ...]:
    warnings: list[str] = []
    for key in raw:
        if key in MOCKED_TOP_LEVEL_SECTIONS:
            warnings.append(f"Top-level section '{key}' is recognized but mocked in MVP.")
        elif key not in EXECUTABLE_TOP_LEVEL_SECTIONS:
            warnings.append(f"Top-level section '{key}' is not recognized by schema v1.")
    return tuple(warnings)
