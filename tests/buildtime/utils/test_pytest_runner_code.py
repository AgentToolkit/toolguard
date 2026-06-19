from pathlib import Path, PureWindowsPath

import pytest

from toolguard.buildtime.utils.pytest import _build_runner_code


def test_runner_code_compiles_with_windows_paths():
    """A Windows work dir must not break the generated pytest snippet.

    Regression: ``str(WindowsPath)`` contains backslashes, and ``C:\\Users``
    embeds ``\\U`` — an invalid unicode escape. Interpolating it raw into a string
    literal made the snippet fail to compile (``truncated \\UXXXXXXXX escape``)
    inside the sandboxed executor, so pytest never ran and the JSON report was
    never written. ``PureWindowsPath`` reproduces the rendering on any host.
    """
    folder = PureWindowsPath(r"C:\Users\bob\proj\Step_2")
    test_file = PureWindowsPath("tool/test_item.py")
    report_file = PureWindowsPath("debug/tool/item/guard_0_pytest.json")

    code = _build_runner_code(folder, test_file, report_file)

    # This is exactly what the sandboxed executor does with the snippet.
    compile(code, "<runner>", "exec")

    # Both paths are present, correctly escaped.
    assert repr(str(folder / test_file)) in code
    assert repr(f"--json-report-file={folder / report_file}") in code


def test_runner_code_compiles_with_posix_paths():
    """POSIX paths keep working unchanged."""
    folder = Path("/tmp/proj/Step_2")
    code = _build_runner_code(folder, Path("tool/test_item.py"), Path("debug/r.json"))
    compile(code, "<runner>", "exec")


def test_raw_interpolation_would_break_on_windows_paths():
    """Pins the bug: the previous raw interpolation does not compile for C:\\Users."""
    folder = PureWindowsPath(r"C:\Users\bob\proj\Step_2")
    test_file = PureWindowsPath("tool/test_item.py")
    buggy = f'\nimport pytest\npytest.main(["{folder / test_file}"])\n'
    with pytest.raises(SyntaxError):
        compile(buggy, "<runner>", "exec")
