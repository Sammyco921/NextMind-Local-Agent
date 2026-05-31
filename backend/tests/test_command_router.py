from __future__ import annotations

from typing import Any, Dict

import pytest

from core.commands.command_router import CommandIntent, CommandRouter


# ---- CommandIntent tests ----

class TestCommandIntent:
    def test_create(self) -> None:
        intent = CommandIntent("create_file", {"filename": "notes.txt"}, "create a file")
        assert intent.command == "create_file"
        assert intent.parameters == {"filename": "notes.txt"}
        assert intent.original_request == "create a file"

    def test_default_parameters(self) -> None:
        intent = CommandIntent("execute_goal")
        assert intent.parameters == {}
        assert intent.original_request == ""

    def test_to_dict(self) -> None:
        intent = CommandIntent("read_file", {"filename": "test.py"}, "open test.py")
        d = intent.to_dict()
        assert d["command"] == "read_file"
        assert d["parameters"] == {"filename": "test.py"}
        assert d["original_request"] == "open test.py"

    def test_equality(self) -> None:
        a = CommandIntent("create_file", {"filename": "a.txt"})
        b = CommandIntent("create_file", {"filename": "a.txt"})
        c = CommandIntent("create_file", {"filename": "b.txt"})
        assert a == b
        assert a != c

    def test_equality_different_type(self) -> None:
        intent = CommandIntent("test")
        assert intent != "not_an_intent"

    def test_repr(self) -> None:
        intent = CommandIntent("test", {"k": "v"})
        r = repr(intent)
        assert "test" in r
        assert "k" in r


# ---- Routing tests ----

class TestCommandRouterFileCreation:
    def test_create_a_file(self) -> None:
        router = CommandRouter()
        intent = router.route("create a file called notes")
        assert intent.command == "create_file"
        assert intent.parameters.get("filename") == "notes"

    def test_make_a_file(self) -> None:
        intent = CommandRouter().route("make a file called test.txt")
        assert intent.command == "create_file"
        assert intent.parameters.get("filename") == "test.txt"

    def test_make_file(self) -> None:
        intent = CommandRouter().route("make file named foo.py")
        assert intent.command == "create_file"
        assert intent.parameters.get("filename") == "foo.py"

    def test_create_file(self) -> None:
        intent = CommandRouter().route("create file")
        assert intent.command == "create_file"

    def test_new_file(self) -> None:
        intent = CommandRouter().route("new file README")
        assert intent.command == "create_file"
        assert intent.parameters.get("filename") == "README"


class TestCommandRouterFolderCreation:
    def test_make_a_folder(self) -> None:
        intent = CommandRouter().route("make a folder called research")
        assert intent.command == "create_folder"
        assert intent.parameters.get("filename") == "research"

    def test_create_a_folder(self) -> None:
        intent = CommandRouter().route("create a folder named stuff")
        assert intent.command == "create_folder"
        assert intent.parameters.get("filename") == "stuff"

    def test_make_folder(self) -> None:
        intent = CommandRouter().route("make folder data")
        assert intent.command == "create_folder"
        assert intent.parameters.get("filename") == "data"

    def test_create_folder(self) -> None:
        intent = CommandRouter().route("create folder data")
        assert intent.command == "create_folder"
        assert intent.parameters.get("filename") == "data"

    def test_make_a_directory(self) -> None:
        intent = CommandRouter().route("make a directory called foo")
        assert intent.command == "create_folder"
        assert intent.parameters.get("filename") == "foo"

    def test_create_a_directory(self) -> None:
        intent = CommandRouter().route("create a directory named bar")
        assert intent.command == "create_folder"
        assert intent.parameters.get("filename") == "bar"

    def test_make_directory(self) -> None:
        intent = CommandRouter().route("make directory baz")
        assert intent.command == "create_folder"
        assert intent.parameters.get("filename") == "baz"

    def test_new_folder(self) -> None:
        intent = CommandRouter().route("new folder assets")
        assert intent.command == "create_folder"
        assert intent.parameters.get("filename") == "assets"

    def test_new_directory(self) -> None:
        intent = CommandRouter().route("new directory lib")
        assert intent.command == "create_folder"
        assert intent.parameters.get("filename") == "lib"


class TestCommandRouterListing:
    def test_show_my_workspace(self) -> None:
        intent = CommandRouter().route("show my workspace")
        assert intent.command == "list_workspace"

    def test_list_workspace(self) -> None:
        intent = CommandRouter().route("list workspace")
        assert intent.command == "list_workspace"

    def test_show_workspace(self) -> None:
        intent = CommandRouter().route("show workspace")
        assert intent.command == "list_workspace"

    def test_list_files_keyword(self) -> None:
        intent = CommandRouter().route("list files")
        assert intent.command == "list_workspace"


class TestCommandRouterRead:
    def test_open_prefix(self) -> None:
        intent = CommandRouter().route("open notes")
        assert intent.command == "read_file"
        assert intent.parameters.get("filename") == "notes"

    def test_read_prefix(self) -> None:
        intent = CommandRouter().route("read README.md")
        assert intent.command == "read_file"
        assert intent.parameters.get("filename") == "README.md"

    def test_read_long_path(self) -> None:
        intent = CommandRouter().route("read src/main.py")
        assert intent.command == "read_file"
        assert intent.parameters.get("filename") == "src/main.py"

    def test_read_short_path(self) -> None:
        intent = CommandRouter().route("read notes.txt")
        assert intent.command == "read_file"
        assert intent.parameters.get("filename") == "notes.txt"


class TestCommandRouterUpdate:
    def test_add_this_to(self) -> None:
        intent = CommandRouter().route("add this to notes.txt")
        assert intent.command == "update_file"

    def test_update_prefix(self) -> None:
        intent = CommandRouter().route("update config.json")
        assert intent.command == "update_file"
        assert intent.parameters.get("filename") == "config.json"

    def test_edit_prefix(self) -> None:
        intent = CommandRouter().route("edit main.py")
        assert intent.command == "update_file"

    def test_append_to_prefix(self) -> None:
        intent = CommandRouter().route("append to log.txt")
        assert intent.command == "update_file"

    def test_change_prefix(self) -> None:
        intent = CommandRouter().route("change settings.ini")
        assert intent.command == "update_file"


class TestCommandRouterDelete:
    def test_delete_prefix(self) -> None:
        intent = CommandRouter().route("delete old_notes.txt")
        assert intent.command == "delete_file"
        assert intent.parameters.get("filename") == "old_notes.txt"

    def test_remove_prefix(self) -> None:
        intent = CommandRouter().route("remove temp.py")
        assert intent.command == "delete_file"
        assert intent.parameters.get("filename") == "temp.py"


class TestCommandRouterOverview:
    def test_show_project_overview(self) -> None:
        intent = CommandRouter().route("show project overview")
        assert intent.command == "show_overview"

    def test_show_overview(self) -> None:
        intent = CommandRouter().route("show overview")
        assert intent.command == "show_overview"

    def test_project_overview_phrase(self) -> None:
        intent = CommandRouter().route("project overview")
        assert intent.command == "show_overview"

    def test_overview_alone(self) -> None:
        intent = CommandRouter().route("overview")
        assert intent.command == "show_overview"


class TestCommandRouterStructure:
    def test_show_project_structure(self) -> None:
        intent = CommandRouter().route("show project structure")
        assert intent.command == "show_structure"

    def test_project_structure(self) -> None:
        intent = CommandRouter().route("project structure")
        assert intent.command == "show_structure"

    def test_show_structure(self) -> None:
        intent = CommandRouter().route("show structure")
        assert intent.command == "show_structure"


class TestCommandRouterRelationships:
    def test_show_related_files(self) -> None:
        intent = CommandRouter().route("show related files")
        assert intent.command == "show_relationships"

    def test_show_relationships(self) -> None:
        intent = CommandRouter().route("show relationships")
        assert intent.command == "show_relationships"

    def test_related_files(self) -> None:
        intent = CommandRouter().route("related files")
        assert intent.command == "show_relationships"


class TestCommandRouterWorkspaceActivity:
    def test_show_recent_activity(self) -> None:
        intent = CommandRouter().route("show recent activity")
        assert intent.command == "show_workspace"

    def test_recent_activity_keyword(self) -> None:
        intent = CommandRouter().route("recent activity")
        assert intent.command == "show_workspace"

    def test_workspace_activity(self) -> None:
        intent = CommandRouter().route("workspace activity")
        assert intent.command == "show_workspace"


class TestCommandRouterHandoff:
    def test_generate_handoff(self) -> None:
        intent = CommandRouter().route("generate handoff")
        assert intent.command == "generate_handoff"

    def test_create_handoff(self) -> None:
        intent = CommandRouter().route("create handoff")
        assert intent.command == "generate_handoff"

    def test_handoff_package(self) -> None:
        intent = CommandRouter().route("handoff package")
        assert intent.command == "generate_handoff"

    def test_build_handoff(self) -> None:
        intent = CommandRouter().route("build handoff")
        assert intent.command == "generate_handoff"


# ---- Fallback tests ----

class TestCommandRouterFallback:
    def test_unknown_request_falls_to_execute(self) -> None:
        intent = CommandRouter().route("write a python script that calculates fibonacci")
        assert intent.command == "execute_goal"
        assert "goal_text" in intent.parameters

    def test_original_request_preserved(self) -> None:
        request = "write a python script that calculates fibonacci"
        intent = CommandRouter().route(request)
        assert intent.original_request == request

    def test_goal_text_parameter(self) -> None:
        intent = CommandRouter().route("do something random")
        assert intent.command == "execute_goal"
        assert intent.parameters.get("goal_text") == "do something random"

    def test_empty_string_falls_to_execute(self) -> None:
        intent = CommandRouter().route("")
        assert intent.command == "execute_goal"

    def test_gibberish_falls_to_execute(self) -> None:
        intent = CommandRouter().route("asdf qwer zxcv")
        assert intent.command == "execute_goal"


# ---- Precedence tests ----

class TestCommandRouterPrecedence:
    """First matching rule wins — explicit ordering."""

    def test_create_file_before_execute(self) -> None:
        intent = CommandRouter().route("create file")
        assert intent.command == "create_file", "create file should match before execute_goal"

    def test_delete_file_before_execute(self) -> None:
        intent = CommandRouter().route("delete file.txt")
        assert intent.command == "delete_file", "delete should match before execute_goal"

    def test_read_overview_does_not_match_read(self) -> None:
        # "overview" keyword matches show_overview, not read
        intent = CommandRouter().route("overview")
        assert intent.command == "show_overview"

    def test_structure_does_not_match_create(self) -> None:
        intent = CommandRouter().route("project structure")
        assert intent.command == "show_structure"

    def test_handoff_does_not_match_delete(self) -> None:
        intent = CommandRouter().route("generate handoff")
        assert intent.command == "generate_handoff"


# ---- Determinism tests ----

class TestCommandRouterDeterminism:
    def test_same_input_same_output(self) -> None:
        router = CommandRouter()
        inputs = [
            "create a file",
            "make a folder",
            "show workspace",
            "open test.txt",
            "delete foo.txt",
            "overview",
            "generate handoff",
            "unknown random request here",
        ]
        for request in inputs:
            first = router.route(request)
            second = router.route(request)
            assert first == second, f"Non-deterministic for: {request}"

    def test_multiple_router_instances_give_same_result(self) -> None:
        inputs = [
            "create a file called notes",
            "make a folder called research",
            "show workspace",
            "open README.md",
            "related files",
        ]
        for request in inputs:
            a = CommandRouter().route(request)
            b = CommandRouter().route(request)
            assert a == b, f"Different routers disagree on: {request}"


# ---- Edge cases ----

class TestCommandRouterEdgeCases:
    def test_case_insensitive(self) -> None:
        intent = CommandRouter().route("CREATE A FILE")
        assert intent.command == "create_file"

    def test_mixed_case(self) -> None:
        intent = CommandRouter().route("Open MyFile.txt")
        assert intent.command == "read_file"

    def test_extra_whitespace(self) -> None:
        intent = CommandRouter().route("  show workspace  ")
        assert intent.command == "list_workspace"

    def test_filename_with_dots(self) -> None:
        intent = CommandRouter().route("open my.file.name.txt")
        assert intent.command == "read_file"
        assert intent.parameters.get("filename") == "my.file.name.txt"

    def test_filename_with_spaces_in_quotes(self) -> None:
        intent = CommandRouter().route('open "nice file.txt"')
        assert intent.command == "read_file"
        # Extracts first non-skip word, stripping quotes
        assert intent.parameters.get("filename") == "nice"

    def test_no_parameters_for_non_file_commands(self) -> None:
        intent = CommandRouter().route("show recent activity")
        assert intent.command == "show_workspace"
        # should not extract a filename
        assert intent.parameters.get("filename") is None

    def test_rules_property(self) -> None:
        router = CommandRouter()
        rules = router.rules
        assert len(rules) > 0
        for cmd, trigger, match_type in rules:
            assert isinstance(cmd, str)
            assert isinstance(trigger, str)
            assert match_type in ("keyword", "prefix")


# ---- Workspace session commands ----

class TestCommandRouterWorkspaceSessions:
    def test_create_workspace_prefix(self) -> None:
        intent = CommandRouter().route("create workspace website-redesign")
        assert intent.command == "create_workspace"
        assert intent.parameters.get("name") == "website-redesign"

    def test_switch_workspace_prefix(self) -> None:
        intent = CommandRouter().route("switch workspace personal-notes")
        assert intent.command == "switch_workspace"
        assert intent.parameters.get("name") == "personal-notes"

    def test_switch_to_workspace_prefix(self) -> None:
        intent = CommandRouter().route("switch to workspace my-project")
        assert intent.command == "switch_workspace"
        assert intent.parameters.get("name") == "my-project"

    def test_show_workspaces_keyword(self) -> None:
        intent = CommandRouter().route("show workspaces")
        assert intent.command == "show_workspaces"

    def test_current_workspace_keyword(self) -> None:
        intent = CommandRouter().route("current workspace")
        assert intent.command == "current_workspace"

    def test_what_workspace_am_i_in(self) -> None:
        intent = CommandRouter().route("what workspace am I in")
        assert intent.command == "current_workspace"

    def test_create_workspace_no_conflict_with_create_file(self) -> None:
        intent = CommandRouter().route("create workspace")
        assert intent.command == "create_workspace"

    def test_show_workspaces_not_confused_with_list_workspace(self) -> None:
        # "show workspaces" (plural) should match before "list workspace"
        intent = CommandRouter().route("show workspaces")
        assert intent.command == "show_workspaces"


# ---- Intent to_dict consistency ----

class TestCommandIntentRoundtrip:
    def test_to_dict_contains_all_fields(self) -> None:
        intent = CommandRouter().route("create a file called test.txt")
        d = intent.to_dict()
        assert "command" in d
        assert "parameters" in d
        assert "original_request" in d
        assert d["command"] == "create_file"
