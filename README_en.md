<div align="center">
  <h1>OK-NTE Community Team Workshop</h1>
  <p>Share, browse, and import community-authored OK-NTE team packages and external character code.</p>

[简体中文](README.md) | English
</div>

## What this repository is

This is the community team-package repository for [OK-NTE](https://github.com/BnanZ0/ok-nte).
Each ZIP contains a team configuration and any external Python character code required by that team.
OK-NTE's **Team Management** page reads the generated `teams.json` catalog so users can search,
inspect, and import packages from the Workshop.

The repository is a static distribution channel. Contributors upload ZIP files through pull
requests. After a merge, GitHub Actions validates the packages, rebuilds the catalog, and syncs
`codes/` and `teams.json` to the CNB mirror.

## Use a community package

1. Open **Team Management** in OK-NTE.
2. Select **Workshop** and search by package name, character, or author.
3. Select a package and import it. Review its metadata, then choose a local team name and external
   code directory.

You can also use **Import** to select a local ZIP obtained elsewhere. Importing never overwrites
an existing external-code directory or local team; use a distinct directory for every version.

> [!WARNING]
> Community packages can contain external Python code. CI checks the archive structure, JSON, and
> Python syntax but **does not execute** submitted code. After import, OK-NTE must load external
> code to run the character logic. Import only packages from trusted authors or sources you have
> reviewed yourself.

## Included example: Zankou Disarray Community Edition

`Zankou Disarray Community Edition 1.0.1` uses Zankou, Daffodill, Iroi, and Adler:

- Daffodill charges the first Q with heavy attacks and casts it as soon as it is ready.
- Adler prioritizes a shield; Iroi uses E/Q for healing and buffs, then leaves the field.
- Zankou holds heavy attack to light the gold E, casts purple E, and follows with two Q casts
  before repeating the short support handoff.

The package uses only OK-NTE's public character and planner APIs and contains no databases,
feature files, or extra assets.

## Export and submit a package

### 1. Export from OK-NTE

In **Team Management**, select the team you want to share and click **Export**. Fill in its name,
description, author, and version. Start with `1.0.0` and increment the version whenever you change
the combat logic. The exported filename is:

```text
<members>_<author>_<version>.zip
```

The filename is for readability only. The `team.json` inside the archive is authoritative.

### 2. Create a pull request in GitHub's web UI

1. Open [`codes/`](https://github.com/BnanZ0/ok-nte-char-code/tree/main/codes).
2. Choose **Add file** → **Upload files** and upload the exported ZIP to the `codes/` root.
3. Choose **Create a new branch for this commit and start a pull request**, then select
   **Propose changes**.
4. Create the pull request and wait for validation and maintainer review.

Do not edit `teams.json` directly. The publish workflow generates it after a PR is merged and
updates both GitHub and the CNB mirror. Different authors or versions of the same team remain
separate catalog entries.

## ZIP v1 format

The ZIP root may contain only `team.json` and the external `.py` files declared by it:

```text
Example_Author_1.0.0.zip
├── team.json
├── character_a.py
└── character_b.py
```

`team.json` defines one to four slots. Built-in characters use an existing `impl_id`; external
characters declare a Python filename, class name, and Chinese/English display names:

```json
{
  "format_version": 1,
  "name": "Example Team",
  "description": "Team rotation and usage notes",
  "author": "Author name",
  "version": "1.0.0",
  "slots": [
    {
      "index": 0,
      "kind": "builtin",
      "impl_id": "builtin:ExampleBuiltin",
      "display": {"zh_CN": "内置角色", "en_US": "Builtin Character"}
    },
    {
      "index": 1,
      "kind": "external",
      "file": "character_a.py",
      "class_name": "CharacterA",
      "display": {"zh_CN": "角色 A", "en_US": "Character A"}
    }
  ]
}
```

`display` may be omitted, in which case the class name or built-in implementation name is used.
External scripts must be UTF-8 `.py` files in the ZIP root, and `class_name` must be a valid Python
identifier.

## Validation and limits

To keep this repository from becoming a general-purpose file host, every package must meet all of
these requirements:

- The ZIP must be at most 2 MiB, and its total uncompressed content must also be at most 2 MiB.
- An archive may have at most five files. Each Python file may be at most 512 KiB, and `team.json`
  may be at most 64 KiB.
- Names are limited to 100 characters, descriptions to 2,000, authors to 64, and versions to 32.
- Directory entries, nested paths, path traversal, duplicate filenames, symlinks, encrypted ZIPs,
  binary assets, and undeclared files are rejected.
- Do not include databases, character features, images, models, recordings, text move lists,
  credentials, or unrelated content.
- Validation only reads JSON and parses Python with AST. It never imports, instantiates, or executes
  submitted Python.

Pull requests run validation with read-only permissions and never receive the CNB sync secret. A
merge to `main` runs the same validation again and produces a compact `teams.json`. A catalog above
2 MiB emits a warning; one above 5 MiB fails publication.

## Contribution rules

- `author` is display metadata, not a verified GitHub identity. Use a stable, recognizable nickname
  or community ID.
- Submit only code you are allowed to publish. Do not submit malicious code, infringing material,
  personal data, or credentials.
- Contributors are responsible for code origin, licensing, and third-party dependencies. Maintainers
  may reject or remove packages that do not follow these rules.
- There is no automatic update, overwrite, or synchronization of already imported local packages.
  Publish new versions as new ZIPs and import them into a new local external-code directory.

## Validate locally

```powershell
python scripts/build_catalog.py --check
python -m unittest discover -s tests -p "test_*.py"
```

## Repository links

- GitHub: [BnanZ0/ok-nte-char-code](https://github.com/BnanZ0/ok-nte-char-code)
- Upload directory: [`codes/`](https://github.com/BnanZ0/ok-nte-char-code/tree/main/codes)
- CNB mirror: [BnanZ0/ok-nte-char-code](https://cnb.cool/BnanZ0/ok-nte-char-code)
