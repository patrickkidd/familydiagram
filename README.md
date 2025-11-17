# Family Diagram App

Author: Dr. Patrick Stinson

## Vision and Purpose

Family Diagram is a research and development tool for clinical science in behavioral health. Unlike traditional "genograms" that map family structure, this application is aimed at improving objective clinical assessments in behavioral health with a novel clinical model.

### Core Philosophy

This tool is part of developing the **SARF** clinical model—a novel approach to
behavioral health grounded in observation rather than opinion-driven
assumptions. The goal is to create a framework that organizes factual
observations into testable models that predict behavior, moving clinical
psychology away from untested assumptions and toward empirical knowledge.

### Applications

Family Diagram enables professionals to quickly gain a broader perspective on
the relationship context of individual problems systems. Primary use cases
include:

- Family or individual psychotherapy
- Organizational coaching
- Case presentations
- Research into family emotional process

### Target Users

The tool is designed for clinicians, coaches, and researchers interested in
evidence-based approaches to behavioral health. It provides a practical method
for documenting and analyzing how individuals function within their relational
contexts.

## Related Articles

For deeper exploration of the theory and methodology behind Family Diagram:

- [Example Research and Development Program Proposal](https://alaskafamilysystems.com/2024/01/example-research-and-development-program-proposal/)
- [Barriers to Science for Bowen theory](https://alaskafamilysystems.com/2023/11/barriers-to-science-for-bowen-theory/)
- [An Emotional Systems Research Methodology](https://alaskafamilysystems.com/2023/05/an-emotional-systems-research-methodology/)
- [Induction and Family Diagram](https://alaskafamilysystems.com/2022/10/induction-and-family-diagram/)
- [Emotion As Vectors, A Definition of Anxiety, and A 9th Concept](https://alaskafamilysystems.com/2022/05/emotion-as-vectors-a-definition-of-anxiety-and-a-9th-concept/)
- [Using Tags in the Visual Timeline](https://alaskafamilysystems.com/2022/03/using-tags-in-the-visual-timeline/)
- [Daily Logging in Family Diagram with Toward and Away](https://alaskafamilysystems.com/2021/09/daily-logging-in-family-diagram-with-toward-and-away/)
- [The Role of Modeling in Scientific Theory](https://alaskafamilysystems.com/2021/05/the-role-of-modeling-in-scientific-theory/)
- [The Importance of the Timeline in Family Diagram](https://alaskafamilysystems.com/2021/02/the-importance-of-the-timeline-in-family-diagram/)
- [Dr Katherine Kott: Clinical Research Framework and App](https://alaskafamilysystems.com/2021/01/dr-katherine-kott-clinical-research-framework-and-app-with-dr-laura-havstad-and-dr-patrick-stinson/)
- [Dr Laura Havstad: Family Practice and Research Using Family Diagram](https://alaskafamilysystems.com/2021/01/dr-laura-havstad-family-practice-and-research-using-family-diagram-2/)
- [Remote Video Coaching with Family Diagram](https://alaskafamilysystems.com/2020/11/remote-video-coaching-with-family-diagram/)
- [Defining a Machine Learning Data Model for Family Emotional Process](https://alaskafamilysystems.com/2020/10/defining-a-machine-learning-data-model-for-family-emotional-process/)
- [The Implicit Model: A case for thinking, objectivity, and theory](https://alaskafamilysystems.com/2020/03/the-implicit-model-a-concept-for-research-and-a-case-for-thinking-objectivity-and-theory/)
- [Guidelines for Natural Systems Models (Video)](https://alaskafamilysystems.com/2020/02/guidelines-for-natural-systems-models/)
- [Some Guidelines for Natural Systems Models](https://alaskafamilysystems.com/2020/02/some-guidelines-for-natural-systems-models/)

## Developers

```
$ uv sync
$ python main.py
```


### Release Processes
- Set up build env
    - All secrets, provisioning, etc set through env (complains if something missing)
        - Example: `base64 <path-to-provisioning-profile> | pbcopy` -> `export FD_PROVISIONING_PROFILE="<PASTE HERE>"`
    - Set in .env file on dev machine

- Build
    - Canonical entryopint: bin/build.sh
        - Entire env comes through (mostly confidential) env vars
    - Confidential env vars (validated in bin/build_env.sh):
        - FD_BUILD_PEPPER The app secret that is used for encrypted disk writes.
          Written to pepper.py and imported in python.
        - FD_BUILD_PROVISIONING_PROFILE_BASE64: Hashed contents of the provisioning profile.
        - FD_BUILD_CERTIFICATE_BASE64: Hashed contents of the signing certificate
        - FD_BUILD_PRIVATE_KEY_BASE64: Private key for the signing certificate
        - FD_BUILD_AC_AUTH_KEY_ID: AppCenter authorization key id
        - FD_BUILD_AC_AUTH_KEY_BASE64: AppCenter authorization key contents
        - FD_BUILD_AC_AUTH_KEY_ISSUER: App Developer Team ID (UUID)
    - Temporary confidential artifacts set up in bin/setup_provisioning_profile.sh
        - Deletest & recreates transient Keychain build.keychain-db
        - Imports provisioning profile into that keychain
    - macOS
        - `bin/build.sh [osx-release|osx-alpha|osx-beta]`
            - Creates `build/osx` from `build/osx-config`
        - CD setup in `./.github`
    - Windows
        - `bin\build.bat`
            - Creates `build/win32` from `build/win32-config`
- Versioning
    - VERSION_COMPAT in `version.py`
    - `Info.plist` updated according to `version.py` at build time

