"""
Checks that the tool reference in AGENT.md matches the registered MCP tool schemas.

`check(markdown, tools)` returns a list of readable problems; an empty list means the document
agrees with the schemas. It verifies tool names, argument names, required/optional status, argument
types and the `confirmed` default. Return values, side effects and credentials are prose and are
not machine-checked.

Two layouts are understood:
- A `### \\`tool\\`` section with `- \\`arg\\` (type, required|optional[, default \\`x\\`]): ...` bullets.
- A bullet list of `tool(arg, optional?)` entries; types are not documented there and are not checked.
"""

import re

SECTION_START = "## 2. Executable Tools"
SECTION_END = "## 3."

HEADING = re.compile(r"^### `([a-z_]+)`\s*$")
ARG_LINE = re.compile(r"^\s+- `([a-z_]+)` \(([^)]*)\)")
COMPACT = re.compile(r"`([a-z_]+)\(([^)]*)\)`")

DOC_TYPES = {
    "string": "string",
    "boolean": "boolean",
    "list of strings": "array",
}


def _schema_type(prop: dict) -> str:
    if "type" in prop:
        return prop["type"]
    kinds = [option["type"] for option in prop.get("anyOf", []) if option.get("type") != "null"]
    return kinds[0] if len(kinds) == 1 else "unknown"


def parse(markdown: str) -> tuple[dict, dict]:
    """Return (sections, compact): documented tools with typed args, and tools listed as name(args)."""
    start = markdown.index(SECTION_START)
    end = markdown.index(SECTION_END, start)
    sections: dict[str, dict] = {}
    compact: dict[str, dict] = {}
    current = None
    for line in markdown[start:end].splitlines():
        heading = HEADING.match(line)
        if heading:
            current = heading.group(1)
            sections[current] = {}
            continue
        if line.startswith("#"):
            current = None
            continue
        arg = ARG_LINE.match(line)
        if arg and current:
            sections[current][arg.group(1)] = [part.strip() for part in arg.group(2).split(",")]
            continue
        for name, args in COMPACT.findall(line):
            compact[name] = {
                "args": {a.strip().rstrip("?"): a.strip().endswith("?") for a in args.split(",") if a.strip()},
                "takes_confirmed": "does not take `confirmed`" not in line,
            }
    return sections, compact


def check(markdown: str, tools: list[dict]) -> list[str]:
    """Compare AGENT.md with `tools`, a list of {"name": ..., "inputSchema": ...} dicts."""
    sections, compact = parse(markdown)
    registered = {tool["name"]: tool["inputSchema"] for tool in tools}
    problems = []

    for name in sorted(set(registered) - set(sections) - set(compact)):
        problems.append(f"{name}: registered tool is not documented in AGENT.md")
    for name in sorted((set(sections) | set(compact)) - set(registered)):
        problems.append(f"{name}: documented tool is not registered")

    for name, doc_args in sections.items():
        if name not in registered:
            continue
        props = registered[name].get("properties", {})
        required = set(registered[name].get("required", []))
        for arg in sorted(set(doc_args) - set(props)):
            problems.append(f"{name}.{arg}: documented argument does not exist")
        for arg in sorted(set(props) - set(doc_args)):
            problems.append(f"{name}.{arg}: argument is not documented")
        for arg, words in doc_args.items():
            if arg not in props:
                continue
            doc_type = DOC_TYPES.get(words[0], words[0])
            if doc_type != _schema_type(props[arg]):
                problems.append(f"{name}.{arg}: documented type '{words[0]}' but schema type is '{_schema_type(props[arg])}'")
            status = "required" if "required" in words else "optional" if "optional" in words else None
            actual = "required" if arg in required else "optional"
            if status != actual:
                problems.append(f"{name}.{arg}: documented as {status} but schema says {actual}")
        if "confirmed" in props:
            default = props["confirmed"].get("default")
            line = next((w for w in doc_args["confirmed"] if w.startswith("default")), "")
            if line != f"default `{str(default).lower()}`":
                problems.append(f"{name}.confirmed: documented default does not match schema default {default}")

    for name, entry in compact.items():
        if name not in registered:
            continue
        props = registered[name].get("properties", {})
        required = set(registered[name].get("required", []))
        has_confirmed = "confirmed" in props
        if entry["takes_confirmed"] != has_confirmed:
            problems.append(f"{name}: documented {'with' if entry['takes_confirmed'] else 'without'} `confirmed` but schema is the opposite")
        schema_args = {arg: arg not in required for arg in props if arg != "confirmed"}
        for arg in sorted(set(entry["args"]) - set(schema_args)):
            problems.append(f"{name}.{arg}: documented argument does not exist")
        for arg in sorted(set(schema_args) - set(entry["args"])):
            problems.append(f"{name}.{arg}: argument is not documented")
        for arg, optional in entry["args"].items():
            if arg in schema_args and optional != schema_args[arg]:
                problems.append(f"{name}.{arg}: documented as {'optional' if optional else 'required'} but schema says {'optional' if schema_args[arg] else 'required'}")
    return problems
