"""Reading targets.json, and turning it into concrete operations.

Nothing else in the CLI knows a destination path. Adding a tool, or moving
where an artifact lands, is an edit to targets.json alone, and the Integration
table in both READMEs follows from the same file.
"""

from __future__ import annotations

from pathlib import Path


class Tool:
    def __init__(self, raw: dict):
        self.id = raw["id"]
        self.label = raw["label"]
        self.config_dir = raw["config_dir"]
        # "plugin" installs itself, "snippet" needs the user to paste one,
        # "none" means the tool has no hook mechanism at all.
        self.hooks = raw.get("hooks", "none")
        self.install = raw.get("install", {})
        self.extra = raw.get("extra", [])

    def supports(self, artifact_id: str) -> bool:
        if artifact_id == "hooks":
            return self.hooks != "none"
        return artifact_id in self.install

    def installed_hint(self, home: Path) -> bool:
        """Whether the tool looks present, used to pre-check the selection."""
        return (home / self.config_dir).is_dir()


class Artifact:
    def __init__(self, raw: dict):
        self.id = raw["id"]
        self.source = raw["source"]
        self.kind = raw["kind"]
        self.label = raw["label"]
        self.doc = raw["doc"]
        # Hooks stay out of the Integration table: a hook is executable code
        # and its wiring is per tool, documented in hooks/README.md instead.
        self.in_table = raw.get("table", True)


class Operation:
    """One thing to install: a source path and where it goes."""

    def __init__(self, source: Path, destination: Path, tool: str, artifact: str):
        self.source = source
        self.destination = destination
        self.tool = tool
        self.artifact = artifact


class Catalog:
    def __init__(self, raw: dict):
        self.artifacts = [Artifact(a) for a in raw["artifacts"]]
        self.tools = [Tool(t) for t in raw["tools"]]
        self.unsupported = raw.get("unsupported", {})

    def tool(self, tool_id: str) -> Tool:
        for tool in self.tools:
            if tool.id == tool_id:
                return tool
        raise KeyError(tool_id)

    def artifact(self, artifact_id: str) -> Artifact:
        for artifact in self.artifacts:
            if artifact.id == artifact_id:
                return artifact
        raise KeyError(artifact_id)

    def artifacts_for(self, tool_ids) -> list:
        """Only the artifacts at least one of the chosen tools can read.

        Offering agents when Hermes is the only tool selected would let someone
        pick something that can never be installed.
        """
        chosen = [self.tool(t) for t in tool_ids]
        return [a for a in self.artifacts if any(t.supports(a.id) for t in chosen)]


def _members(root: Path, source: str, kind: str) -> list:
    """The individual files or directories a source contributes."""
    path = root / source
    if kind == "file":
        return [path] if path.exists() else []
    if not path.is_dir():
        return []
    # A directory contributes one entry per child: the tools read
    # ~/.claude/skills/<name>, not a link to the whole skills folder.
    return sorted(
        child for child in path.iterdir() if child.name != ".gitkeep"
    )


def _extra_operations(tool, root: Path, home: Path) -> list:
    """Adapter files a tool needs beyond the artifacts themselves."""
    operations = []
    for extra in tool.extra:
        destination_root = home / extra["target"]
        for member in _members(root, extra["source"], extra["kind"]):
            operations.append(
                Operation(member, destination_root / member.name, tool.id, "hooks")
            )
    return operations


def plan(catalog: Catalog, root: Path, home: Path, tool_ids, artifact_ids) -> list:
    """Every operation the given selection implies, in a stable order."""
    operations = []

    for tool in catalog.tools:
        if tool.id not in tool_ids:
            continue

        for artifact in catalog.artifacts:
            if artifact.id not in artifact_ids or not tool.supports(artifact.id):
                continue

            if artifact.kind == "hooks":
                # Only a plugin installs itself. A snippet is pasted by the
                # user, so there is nothing to place here; main.py reports it
                # as the closing step instead.
                if tool.hooks == "plugin":
                    operations.extend(_extra_operations(tool, root, home))
                continue

            destination_root = home / tool.install[artifact.id]
            for member in _members(root, artifact.source, artifact.kind):
                if artifact.kind == "file":
                    # rules/global.md becomes a named file, not a directory entry.
                    destination = destination_root
                else:
                    destination = destination_root / member.name
                operations.append(Operation(member, destination, tool.id, artifact.id))

    return operations
