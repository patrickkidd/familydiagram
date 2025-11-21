import pytest
import os
import sys
import tempfile


@pytest.fixture
def extract_changelog():
    bin_dir = os.path.join(os.path.dirname(__file__), "..", "..", "bin")
    sys.path.insert(0, bin_dir)
    try:
        from extract_changelog import extract_changelog as ec

        yield ec
    finally:
        if bin_dir in sys.path:
            sys.path.remove(bin_dir)


@pytest.fixture
def sample_changelog():
    content = """# Changelog

## 2.1.9

## 2.1.9b2
- Fix critical bug
- Polish feature

## 2.1.9b1
- New feature X
- Refactor Y

## 2.1.8
- Stable release

## 2.1.8b1
- Bug fixes
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(content)
        temp_path = f.name

    yield temp_path

    os.unlink(temp_path)


@pytest.mark.no_gui
def test_extract_beta_version(extract_changelog, sample_changelog):
    result = extract_changelog("2.1.9b1", sample_changelog)

    assert "<ul>" in result
    assert "<li>New feature X</li>" in result
    assert "<li>Refactor Y</li>" in result
    assert "</ul>" in result


@pytest.mark.no_gui
def test_extract_release_with_content(extract_changelog, sample_changelog):
    result = extract_changelog("2.1.8", sample_changelog)

    assert "<ul>" in result
    assert "<li>Stable release</li>" in result
    assert "</ul>" in result
    assert "Bug fixes" not in result


@pytest.mark.no_gui
def test_extract_release_aggregates_betas(extract_changelog, sample_changelog):
    result = extract_changelog("2.1.9", sample_changelog)

    assert "<ul>" in result
    assert "<li>New feature X</li>" in result
    assert "<li>Refactor Y</li>" in result
    assert "<li>Fix critical bug</li>" in result
    assert "<li>Polish feature</li>" in result
    assert "</ul>" in result


@pytest.mark.no_gui
def test_version_not_found(extract_changelog, sample_changelog):
    result = extract_changelog("3.0.0", sample_changelog)

    assert result == ""


@pytest.mark.no_gui
def test_beta_version_ordering(extract_changelog):
    content = """# Changelog

## 2.1.9b3
- Third beta change

## 2.1.9b1
- First beta change

## 2.1.9b2
- Second beta change
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(content)
        temp_path = f.name

    try:
        result = extract_changelog("2.1.9b2", temp_path)

        assert "<li>Second beta change</li>" in result
        assert "First beta change" not in result
        assert "Third beta change" not in result
    finally:
        os.unlink(temp_path)


@pytest.mark.no_gui
def test_version_with_brackets(extract_changelog):
    content = """# Changelog

## [2.1.9]
- Release with brackets
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(content)
        temp_path = f.name

    try:
        result = extract_changelog("2.1.9", temp_path)

        assert "<li>Release with brackets</li>" in result
    finally:
        os.unlink(temp_path)


@pytest.mark.no_gui
def test_alpha_version(extract_changelog):
    content = """# Changelog

## 2.1.9a1
- Alpha feature
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(content)
        temp_path = f.name

    try:
        result = extract_changelog("2.1.9a1", temp_path)

        assert "<li>Alpha feature</li>" in result
    finally:
        os.unlink(temp_path)
