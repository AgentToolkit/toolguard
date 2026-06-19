import shutil
import sys

from toolguard.buildtime.utils.pyright import _resolve_pyright


def test_resolve_pyright_returns_non_empty_string():
    result = _resolve_pyright()
    assert isinstance(result, str)
    assert result


def test_resolve_pyright_prefers_interpreter_dir(tmp_path, monkeypatch):
    """The console script next to the interpreter is preferred over PATH.

    Regression: bare ``"pyright"`` raises ``FileNotFoundError [WinError 2]`` when
    the venv ``Scripts`` dir is not on PATH (common on Windows). Resolving against
    the interpreter dir fixes it.
    """
    fake_python = tmp_path / "python"
    fake_python.write_text("")
    (tmp_path / "pyright").write_text("")  # the installed console script
    monkeypatch.setattr(sys, "executable", str(fake_python))

    assert _resolve_pyright() == str(tmp_path / "pyright")


def test_resolve_pyright_falls_back_to_path(tmp_path, monkeypatch):
    """With no script beside the interpreter, fall back to a PATH lookup."""
    fake_python = tmp_path / "python"
    fake_python.write_text("")
    monkeypatch.setattr(sys, "executable", str(fake_python))
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/local/bin/pyright")

    assert _resolve_pyright() == "/usr/local/bin/pyright"
