from toolguard.buildtime.utils.py import top_level_types


def test_top_level_types_reads_utf8(tmp_path):
    """Generated files must be parsed as UTF-8, not the platform default.

    Regression: ``Path(path).read_text()`` with no ``encoding`` uses the locale
    default (cp1252 on a stock Windows launch), which raises
    ``UnicodeDecodeError: 'charmap' ...`` on non-ASCII content and aborts Generate.
    """
    f = tmp_path / "types.py"
    f.write_text(
        'NAME = "café — naïve ☃"\n\n\nclass Foo:\n    pass\n',
        encoding="utf-8",
    )

    assert top_level_types(f) == {"NAME", "Foo"}
