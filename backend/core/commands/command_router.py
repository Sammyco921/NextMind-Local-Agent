from __future__ import annotations

from typing import Any, Dict, List, Tuple


class CommandIntent:
    """Deterministic result of routing a raw user request.

    - command: one of the known command names
    - parameters: extracted from the request (e.g. filename, path)
    - original_request: the raw input string
    """

    def __init__(
        self,
        command: str,
        parameters: Dict[str, Any] | None = None,
        original_request: str = "",
    ) -> None:
        self.command = command
        self.parameters = parameters or {}
        self.original_request = original_request

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command": self.command,
            "parameters": dict(self.parameters),
            "original_request": self.original_request,
        }

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CommandIntent):
            return NotImplemented
        return (
            self.command == other.command
            and self.parameters == other.parameters
        )

    def __repr__(self) -> str:
        return f"CommandIntent(command={self.command!r}, params={self.parameters})"


class CommandRouter:
    """Deterministic, explicit, ordered command router.

    Rules are plain keyword checks in priority order.
    First match wins. No ML, no scoring, no embeddings, no probabilities.
    Unmatched requests fall through to execute_goal.
    """

    def __init__(self) -> None:
        self._rules: List[Tuple[str, str, str | None]] = [
            # (command, keyword_or_prefix, match_type)
            # match_type: "keyword" = word-in-request, "prefix" = starts-with

            # File creation
            ("create_file", "create a file", "keyword"),
            ("create_file", "make a file", "keyword"),
            ("create_file", "make file", "keyword"),
            ("create_file", "create file", "keyword"),
            ("create_file", "new file", "keyword"),

            # Folder creation
            ("create_folder", "make a folder", "keyword"),
            ("create_folder", "create a folder", "keyword"),
            ("create_folder", "make folder", "keyword"),
            ("create_folder", "create folder", "keyword"),
            ("create_folder", "make a directory", "keyword"),
            ("create_folder", "create a directory", "keyword"),
            ("create_folder", "make directory", "keyword"),
            ("create_folder", "new folder", "keyword"),
            ("create_folder", "new directory", "keyword"),

            # Session workspace management
            ("create_workspace", "create workspace ", "prefix"),
            ("create_workspace", "create workspace", "keyword"),
            ("switch_workspace", "switch workspace ", "prefix"),
            ("switch_workspace", "switch to workspace ", "prefix"),
            ("show_workspaces", "show workspaces", "keyword"),
            ("current_workspace", "current workspace", "keyword"),
            ("current_workspace", "what workspace am i in", "keyword"),

            # Workspace listing
            ("list_workspace", "show my workspace", "keyword"),
            ("list_workspace", "list workspace", "keyword"),
            ("list_workspace", "show workspace", "keyword"),
            ("list_workspace", "list files", "keyword"),

            # Read file — prefix match for "open " and "read "
            ("read_file", "open ", "prefix"),
            ("read_file", "read ", "prefix"),

            # Update file
            ("update_file", "add this to ", "prefix"),
            ("update_file", "update ", "prefix"),
            ("update_file", "edit ", "prefix"),
            ("update_file", "append to ", "prefix"),
            ("update_file", "change ", "prefix"),

            # Delete file
            ("delete_file", "delete ", "prefix"),
            ("delete_file", "remove ", "prefix"),

            # Project overview
            ("show_overview", "show project overview", "keyword"),
            ("show_overview", "show overview", "keyword"),
            ("show_overview", "project overview", "keyword"),
            ("show_overview", "overview", "keyword"),

            # Project structure
            ("show_structure", "show project structure", "keyword"),
            ("show_structure", "project structure", "keyword"),
            ("show_structure", "show structure", "keyword"),

            # Relationships
            ("show_relationships", "show related files", "keyword"),
            ("show_relationships", "show relationships", "keyword"),
            ("show_relationships", "related files", "keyword"),

            # Workspace activity
            ("show_workspace", "show recent activity", "keyword"),
            ("show_workspace", "recent activity", "keyword"),
            ("show_workspace", "workspace activity", "keyword"),

            # Handoff
            ("generate_handoff", "generate handoff", "keyword"),
            ("generate_handoff", "create handoff", "keyword"),
            ("generate_handoff", "handoff package", "keyword"),
            ("generate_handoff", "build handoff", "keyword"),
        ]

    def route(self, request: str) -> CommandIntent:
        req_stripped = request.strip()
        req_lower = req_stripped.lower()

        for command, trigger, match_type in self._rules:
            if match_type == "prefix":
                if req_lower.startswith(trigger):
                    rest = req_stripped[len(trigger):].strip()
                    params = self._extract_file_params(rest, command)
                    return CommandIntent(
                        command=command,
                        parameters=params,
                        original_request=request,
                    )
            else:
                idx = req_lower.find(trigger)
                if idx != -1:
                    rest = req_stripped[idx + len(trigger):].strip()
                    params = self._extract_file_params(rest, command)
                    return CommandIntent(
                        command=command,
                        parameters=params,
                        original_request=request,
                    )

        return CommandIntent(
            command="execute_goal",
            parameters={"goal_text": request},
            original_request=request,
        )

    def _extract_file_params(
        self, remaining: str, command: str
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if command in ("create_file", "read_file", "update_file", "delete_file", "create_folder"):
            filename = self._extract_filename(remaining)
            if filename:
                params["filename"] = filename
                params["path"] = filename
        elif command in ("create_workspace", "switch_workspace"):
            name = remaining.strip().strip("'\"").split()[0] if remaining.split() else ""
            if name:
                params["name"] = name
        return params

    @staticmethod
    def _extract_filename(text: str) -> str:
        cleaned = text.strip().strip(".").strip()
        words = cleaned.split()
        if not words:
            return ""
        SKIP = frozenset({"a", "an", "the", "my", "this", "that", "called", "named", "titled", "with", "as", "to"})
        while words and words[0] in SKIP:
            words = words[1:]
        if not words:
            return ""
        return words[0].strip("'\"")

    @property
    def rules(self) -> List[Tuple[str, str, str]]:
        return list(self._rules)
