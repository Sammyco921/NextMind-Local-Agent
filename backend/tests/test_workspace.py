from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from core.workspace.gateway import WorkspaceFileGateway
from core.workspace.resolver import WorkspaceEscapeError, WorkspaceResolver


class TestWorkspaceResolver:
    def test_default_allowed_roots(self) -> None:
        r = WorkspaceResolver(allowed_roots=["/tmp/test"])
        assert r.allowed_roots == ["/tmp/test"]

    def test_resolve_absolute_within_root(self, tmp_path: Path) -> None:
        root = str(tmp_path)
        r = WorkspaceResolver(allowed_roots=[root])
        target = str(tmp_path / "test.txt")
        assert r.resolve(target) == target

    def test_resolve_absolute_outside_root(self, tmp_path: Path) -> None:
        root = str(tmp_path / "allowed")
        os.makedirs(root)
        r = WorkspaceResolver(allowed_roots=[root])
        outside = str(tmp_path / "outside" / "test.txt")
        with pytest.raises(WorkspaceEscapeError):
            r.resolve(outside)

    def test_resolve_relative_within_root(self, tmp_path: Path) -> None:
        root = str(tmp_path)
        r = WorkspaceResolver(allowed_roots=[root], default_workspace=root)
        resolved = r.resolve("test.txt")
        assert resolved == os.path.join(root, "test.txt")

    def test_resolve_empty_path(self, tmp_path: Path) -> None:
        r = WorkspaceResolver(allowed_roots=[str(tmp_path)])
        with pytest.raises(ValueError):
            r.resolve("")

    def test_resolve_whitespace_path(self, tmp_path: Path) -> None:
        r = WorkspaceResolver(allowed_roots=[str(tmp_path)])
        with pytest.raises(ValueError):
            r.resolve("   ")

    def test_resolve_backend_context(self, tmp_path: Path) -> None:
        root = str(tmp_path)
        backend = "backend"
        os.makedirs(os.path.join(root, backend))
        r = WorkspaceResolver(
            allowed_roots=[root],
            default_workspace=root,
            backend_workspace=backend,
        )
        resolved = r.resolve("./test.txt", context="backend")
        assert os.path.abspath(resolved) == os.path.join(root, backend, "test.txt")

    def test_resolve_auto_with_dot_prefix(self, tmp_path: Path) -> None:
        root = str(tmp_path)
        backend = "backend"
        os.makedirs(os.path.join(root, backend))
        r = WorkspaceResolver(
            allowed_roots=[root],
            default_workspace=root,
            backend_workspace=backend,
        )
        resolved = r.resolve("./test.txt", context="auto")
        assert os.path.abspath(resolved) == os.path.join(root, backend, "test.txt")

    def test_resolve_auto_without_prefix(self, tmp_path: Path) -> None:
        root = str(tmp_path)
        r = WorkspaceResolver(
            allowed_roots=[root],
            default_workspace=root,
        )
        resolved = r.resolve("test.txt", context="auto")
        assert resolved == os.path.join(root, "test.txt")

    def test_no_allowed_roots_no_restriction(self, tmp_path: Path) -> None:
        r = WorkspaceResolver()
        resolved = r.resolve(str(tmp_path / "test.txt"))
        assert resolved == str(tmp_path / "test.txt")

    def test_border_case_root_itself(self, tmp_path: Path) -> None:
        root = str(tmp_path)
        r = WorkspaceResolver(allowed_roots=[root])
        resolved = r.resolve(root)
        assert resolved == root

    def test_properties(self, tmp_path: Path) -> None:
        root = str(tmp_path)
        r = WorkspaceResolver(
            allowed_roots=[root],
            default_workspace=root,
            backend_workspace="./backend",
        )
        assert r.default_workspace == root
        assert r.backend_workspace == "./backend"


class TestWorkspaceFileGateway:
    def test_create_and_read(self, tmp_path: Path) -> None:
        root = str(tmp_path)
        r = WorkspaceResolver(allowed_roots=[root], default_workspace=root)
        gw = WorkspaceFileGateway(r)
        result = gw.create("hello.txt", "hello world")
        assert result["status"] == "success"
        assert result["action"] == "created"
        assert os.path.isfile(os.path.join(root, "hello.txt"))

        read_result = gw.read("hello.txt")
        assert read_result["content"] == "hello world"
        assert read_result["action"] == "read"

    def test_update(self, tmp_path: Path) -> None:
        root = str(tmp_path)
        r = WorkspaceResolver(allowed_roots=[root], default_workspace=root)
        gw = WorkspaceFileGateway(r)
        gw.create("update.txt", "original")
        result = gw.update("update.txt", "modified")
        assert result["action"] == "updated"
        read_result = gw.read("update.txt")
        assert read_result["content"] == "modified"

    def test_update_nonexistent_raises(self, tmp_path: Path) -> None:
        root = str(tmp_path)
        r = WorkspaceResolver(allowed_roots=[root], default_workspace=root)
        gw = WorkspaceFileGateway(r)
        with pytest.raises(FileNotFoundError):
            gw.update("nonexistent.txt", "content")

    def test_read_nonexistent_raises(self, tmp_path: Path) -> None:
        root = str(tmp_path)
        r = WorkspaceResolver(allowed_roots=[root], default_workspace=root)
        gw = WorkspaceFileGateway(r)
        with pytest.raises(FileNotFoundError):
            gw.read("nonexistent.txt")

    def test_list_dir(self, tmp_path: Path) -> None:
        root = str(tmp_path)
        r = WorkspaceResolver(allowed_roots=[root], default_workspace=root)
        gw = WorkspaceFileGateway(r)
        gw.create("a.txt", "a")
        gw.create("b.txt", "b")
        result = gw.list_dir(".")
        assert result["status"] == "success"
        assert "a.txt" in result["items"]
        assert "b.txt" in result["items"]
        assert result["count"] == 2

    def test_list_nonexistent_raises(self, tmp_path: Path) -> None:
        root = str(tmp_path)
        r = WorkspaceResolver(allowed_roots=[root], default_workspace=root)
        gw = WorkspaceFileGateway(r)
        with pytest.raises(FileNotFoundError):
            gw.list_dir("nonexistent")

    def test_delete_file(self, tmp_path: Path) -> None:
        root = str(tmp_path)
        r = WorkspaceResolver(allowed_roots=[root], default_workspace=root)
        gw = WorkspaceFileGateway(r)
        gw.create("delete.txt", "content")
        result = gw.delete("delete.txt")
        assert result["action"] == "deleted"
        assert not os.path.isfile(os.path.join(root, "delete.txt"))

    def test_delete_nonexistent_raises(self, tmp_path: Path) -> None:
        root = str(tmp_path)
        r = WorkspaceResolver(allowed_roots=[root], default_workspace=root)
        gw = WorkspaceFileGateway(r)
        with pytest.raises(FileNotFoundError):
            gw.delete("nonexistent.txt")

    def test_create_with_subdirectory(self, tmp_path: Path) -> None:
        root = str(tmp_path)
        r = WorkspaceResolver(allowed_roots=[root], default_workspace=root)
        gw = WorkspaceFileGateway(r)
        result = gw.create("sub/dir/test.txt", "nested")
        assert result["status"] == "success"
        assert os.path.isfile(os.path.join(root, "sub", "dir", "test.txt"))

    def test_create_outside_workspace_raises(self, tmp_path: Path) -> None:
        root = str(tmp_path / "allowed")
        os.makedirs(root)
        r = WorkspaceResolver(allowed_roots=[root])
        gw = WorkspaceFileGateway(r)
        with pytest.raises(WorkspaceEscapeError):
            gw.create(str(tmp_path / "outside.txt"), "content")

    def test_resolver_property(self, tmp_path: Path) -> None:
        root = str(tmp_path)
        r = WorkspaceResolver(allowed_roots=[root], default_workspace=root)
        gw = WorkspaceFileGateway(r)
        assert gw.resolver is r
