# Release Process

This document describes the workflow for creating beta and release builds of Family Diagram.

## Overview

Family Diagram uses two release streams:

- **Beta/Alpha builds**: Built from `master` branch, distributed to early adopters
- **Release builds**: Built from `release` branch, distributed to general public

Both streams use a single unified `CHANGELOG.md` file and automated changelog extraction for Sparkle updates.

## Version Numbering

Versions are managed in [pkdiagram/version.py](../pkdiagram/version.py):

```python
VERSION_MAJOR = 2
VERSION_MINOR = 1
VERSION_MICRO = 9
ALPHABETA = "b"        # "b" for beta, "a" for alpha, "" for release
ALPHABETA_SUFFIX = 1   # Numeric suffix for alpha/beta
```

**Version formats**:
- Beta: `2.1.9b1`, `2.1.9b2`, etc.
- Alpha: `2.1.9a1`, `2.1.9a2`, etc.
- Release: `2.1.9`

## Changelog Format

The changelog is maintained in [CHANGELOG.md](../CHANGELOG.md) at the repository root.

**Format**:
```markdown
# Changelog

## 2.1.9

## 2.1.9b2
- Fix critical bug from b1
- Polish feature X

## 2.1.9b1
- New feature X
- Refactor Y

## 2.1.8

## 2.1.8b1
- Bug fixes
```

**Rules**:
- Each version gets its own `## version` section
- Version headers must exactly match the version string from `version.py`
- Bullet points use standard markdown: `- Change description`
- **Empty release sections**: When a release version section is empty, the automated system aggregates all beta/alpha versions with the same base version (e.g., all `2.1.9b*` entries for release `2.1.9`)

## Version Strategy

**Most common**: Beta and release at parity with same changes
- Master: `2.1.9b1`
- Release: `2.1.9` (auto-aggregates from `2.1.9b1`)

**When beta has experimental features**: Beta ahead
- Master: `2.1.10b1` (experimental, unstable)
- Release: `2.1.9` (stable, no merge yet)
- Later: Once `2.1.10` stabilizes, merge and release as `2.1.10`

**Key rule**: Beta version should be at or ahead of release, never behind.

## Workflow: Normal Release Cycle

### 1. Creating a Beta Version

On the `master` branch:

1. Update `pkdiagram/version.py`:
   ```python
   VERSION_MICRO = 9
   ALPHABETA = "b"
   ALPHABETA_SUFFIX = 1  # Creates version 2.1.9b1
   ```

2. Add changelog entry to `CHANGELOG.md`:
   ```markdown
   ## 2.1.9b1
   - New feature X
   - Fix bug Y
   - Refactor Z
   ```

3. Commit and push to `master`

4. Trigger GitHub Actions workflow (Actions → Release → Run workflow)

5. **Automated process**:
   - Validates that `CHANGELOG.md` contains `## 2.1.9b1` section
   - Builds macOS and Windows binaries
   - Creates GitHub release tagged `2.1.9b1` (marked as prerelease)
   - Extracts changelog from `CHANGELOG.md` and includes in GitHub release body
   - Generates appcast XML files with changelog formatted as HTML
   - Updates `appcast_macos_beta.xml` and `appcast_windows_beta.xml` on familydiagram.com

6. Beta users receive Sparkle update notification with changelog

### 2. Creating Additional Beta Versions

Repeat the process with incremented suffix:

1. Update `version.py`:
   ```python
   ALPHABETA_SUFFIX = 2  # Creates version 2.1.9b2
   ```

2. Add new section to `CHANGELOG.md`:
   ```markdown
   ## 2.1.9b2
   - Fix edge case from b1
   - Polish feature X
   ```

3. Push and trigger build

### 3. Creating a Release Version

When ready to release to general public:

1. Merge `master` → `release` branch:
   ```bash
   git checkout release
   git merge master
   ```

2. Update `pkdiagram/version.py` on `release` branch:
   ```python
   VERSION_MICRO = 9
   ALPHABETA = ""         # Remove beta suffix
   ALPHABETA_SUFFIX = 1   # Creates version 2.1.9
   ```

3. Add **empty** release section to `CHANGELOG.md`:
   ```markdown
   ## 2.1.9

   ## 2.1.9b2
   - Fix edge case from b1
   - Polish feature X

   ## 2.1.9b1
   - New feature X
   - Fix bug Y
   ```

4. Commit and push to `release` branch

5. Trigger GitHub Actions workflow

6. **Automated process**:
   - Detects empty `## 2.1.9` section
   - Automatically aggregates all `2.1.9b*` changelog entries
   - Creates GitHub release tagged `2.1.9` (NOT marked as prerelease)
   - Release users see combined changelog from all beta versions
   - Updates `appcast_macos.xml` and `appcast_windows.xml`

### Alternative: Custom Release Notes

If you want different notes for the release than the beta aggregation:

```markdown
## 2.1.9
- Stable release with comprehensive feature set
- Major performance improvements
- See beta versions for detailed changes

## 2.1.9b2
...
```

The system will use your custom content instead of aggregating.

## Workflow: Direct Release (No Betas)

If you want to skip beta testing:

1. Update `version.py` on `release` branch:
   ```python
   VERSION_MICRO = 9
   ALPHABETA = ""
   ```

2. Add changelog with content:
   ```markdown
   ## 2.1.9
   - Direct feature addition
   - Bug fixes
   ```

3. Push and build

## Sparkle Update Display

**How users see updates**:

- **Sparkle reads the appcast XML** and displays all versions between their installed version and the latest version
- **Each version shows its `<description>` field** from the appcast
- **Beta users** see beta-to-beta incremental changes (e.g., 2.1.9b1 → 2.1.9b2)
- **Release users upgrading across versions** see all intervening release changelogs (e.g., 2.1.8 → 2.1.9 → 2.1.10)
- **Beta and release users use separate appcasts**, so release users never see beta versions

## Technical Details

### Changelog Extraction

The [bin/extract_changelog.py](../bin/extract_changelog.py) script:
- Parses `CHANGELOG.md` to find version sections
- Converts markdown bullet lists to HTML `<ul><li>` format
- For empty release sections, aggregates matching beta/alpha versions
- Used by both GitHub Actions and appcast generation

### Appcast Generation

The [bin/github_releases_2_appcast.py](../bin/github_releases_2_appcast.py) script:
- Fetches all GitHub releases via API
- Filters by prerelease flag (beta vs release)
- Calls `extract_changelog.py` for each version
- Generates separate XML files for macOS/Windows and beta/release
- Uploaded to familydiagram.com via SCP

### Build Configuration

Applications are compiled with preprocessor defines that select the correct appcast URL:

**macOS** (`_pkdiagram/_pkdiagram_mac.mm`):
```objc
#ifdef PK_BETA_BUILD
    SparkleFeedURL = @"https://familydiagram.com/appcast_macos_beta.xml";
#else
    SparkleFeedURL = @"https://familydiagram.com/appcast_macos.xml";
#endif
```

**Windows** (`_pkdiagram/_pkdiagram_win32.cpp`):
```cpp
#ifdef PK_BETA_BUILD
    win_sparkle_set_appcast_url("https://familydiagram.com/appcast_windows_beta.xml");
#else
    win_sparkle_set_appcast_url("https://familydiagram.com/appcast_windows.xml");
#endif
```

## Troubleshooting

### Workflow fails: "No changelog entry found"

The validation step checks that `CHANGELOG.md` contains a section matching the version in `version.py`.

**Fix**: Add the missing section header:
```markdown
## 2.1.9b1
```

### Sparkle shows empty changelog

**Cause**: The `extract_changelog.py` script couldn't find matching content.

**Fix**: Ensure:
1. Version header in `CHANGELOG.md` exactly matches `version.py` output
2. Bullet points use standard markdown format: `- Change description`
3. No extra spaces or formatting in version header

### Release shows beta changelogs

**Cause**: The release section in `CHANGELOG.md` has content (not empty).

**Fix**: Remove content from release section to enable auto-aggregation, or verify your custom content is correct.

### Users don't see update

**Possible causes**:
1. Appcast XML not uploaded to familydiagram.com (check workflow logs)
2. User's installed version uses wrong appcast URL (beta vs release)
3. Version number not incrementing properly
4. User has auto-update disabled

## Summary

**Your workflow**:
1. Edit `version.py` to set version number
2. Add corresponding section to `CHANGELOG.md` with changes
3. Push to appropriate branch (`master` for beta, `release` for release)
4. Trigger GitHub Actions workflow
5. ✅ Everything else is automated
