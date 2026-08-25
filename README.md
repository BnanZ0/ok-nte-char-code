# OK-NTE Community Team Codes

This repository distributes community-authored OK-NTE combat team packages.

## Submit a package

1. Export a team package from OK-NTE.
2. Upload the generated `<members>_<author>_<version>.zip` file to `codes/`.
3. Open a pull request. The validation workflow checks the archive without running its Python code.

Each archive contains only these root files:

```text
team.json
external_character.py
```

`team.json` is the package manifest. It contains the package name, description, author, version, and one to four slots. Slots either reference an OK-NTE builtin implementation or one declared Python file. Do not include user databases, character features, screenshots, or credentials.

The build workflow generates `teams.json` after merge. OK-NTE uses that static catalog to browse and download packages.
