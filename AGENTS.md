# 项目约定

- `teams.json` 由 GitHub Actions 自动生成，不要手动修改或提交本地重新生成的内容。
- 修改方案名称、描述或其他元数据时，更新 `codes/` 下对应 ZIP 内的 `team.json`，由 Action 同步生成目录。
- 校验方案包时使用 `scripts/build_catalog.py --check`，避免改写 `teams.json`。
