<div align="center">
  <h1>OK-NTE 社区队伍方案工坊</h1>
  <p>分享, 浏览和导入社区创作的 OK-NTE 队伍方案与外置角色代码。</p>

简体中文 | [English](README_en.md)
</div>

## 这是什么

这是 [OK-NTE](https://github.com/BnanZ0/ok-nte) 的社区队伍方案仓库。每个 ZIP 包包含一个
队伍方案，以及该方案实际需要的外置 Python 角色代码。OK-NTE 的“队伍管理”页面会读取本仓库
生成的 `teams.json`，让用户在工坊内搜索、查看和导入方案。

仓库仅负责静态分发。提交者通过 Pull Request 上传 ZIP，合并后 GitHub Actions 会校验包并更新
索引，再同步 `codes/` 与 `teams.json` 到 CNB 镜像。

## 使用社区方案

1. 打开 OK-NTE 的“队伍管理”。
2. 点击“工坊”，按名称、角色或作者搜索方案。
3. 选择方案并导入，确认 ZIP 中展示的元数据后填写本地方案名称和外置代码目录。

也可以点击“导入”选择其他来源提供的本地 ZIP。导入不会覆盖已有的外置代码目录或本地方案；
请为不同版本使用不同目录。

> [!WARNING]
> 社区包可以包含外置 Python 代码。CI 只检查 ZIP 结构、JSON 和 Python 语法，**不会**执行
> 提交的代码；但导入后，OK-NTE 为运行角色逻辑会加载外置代码。请只导入可信作者或你已自行
> 审查的来源。

## 示例方案：残虹倾陷社区版

当前仓库提供的 `残虹倾陷社区版 1.0.1` 使用残虹、达芙蒂尔、伊洛伊和阿德勒：

- 达芙蒂尔先用重击充能首个 Q，亮起后立即释放；
- 阿德勒优先开盾，伊洛伊使用 E/Q 提供治疗与增益后快速离场；
- 残虹长按重击点亮黄 E，接紫 E 后连续释放两次 Q，之后重复短切辅助与残虹站场循环。

方案只依赖 OK-NTE 的公开角色与规划器接口，包内不包含本地数据库、特征文件或其他资源。

## 第三个提交：残虹安魂曲双核社区版

第三个社区提交为 `残虹安魂曲双核社区版 1.0.0`，队伍由残虹、安魂曲、早雾和阿德勒组成：

- 残虹先用重击点亮黄 E，接紫 E 后连续释放两次 Q；
- 安魂曲接过前台后完整释放 Q/E，并补一段普攻窗口；
- 安魂曲窗口结束后，阿德勒优先开盾，早雾使用 Q/E 短切提供增益，最后回到残虹循环。

两名核心轮流站场，辅助只在交接窗口提供护盾和增益；包内使用公开角色与规划器接口，内置角色继续使用 OK-NTE 自带实现。

## 导出并提交方案

### 1. 从 OK-NTE 导出

在“队伍管理”中选中要分享的方案，点击“导出”，填写名称、描述、作者和版本。建议版本从
`1.0.0` 开始，并在每次修改出招逻辑后递增。导出文件名为：

```text
<角色组合>_<作者>_<版本>.zip
```

文件名仅便于阅读；包内的 `team.json` 才是权威元数据。

### 2. 用 GitHub 网页创建 PR

1. 打开 [`codes/`](https://github.com/BnanZ0/ok-nte-char-code/tree/main/codes)。
2. 点击 **Add file** → **Upload files**，上传导出的 ZIP 到 `codes/` 根目录。
3. 选择 **Create a new branch for this commit and start a pull request**，再点击
   **Propose changes**。
4. 创建 Pull Request，等待校验通过和维护者审核。

不要直接修改 `teams.json`。它由发布工作流生成；PR 合并后会自动更新 GitHub 和 CNB 镜像。
相同队伍的不同作者或不同版本会作为独立条目保留。

## ZIP v1 格式

ZIP 根目录只能包含 `team.json` 和 `team.json` 中声明的外置 `.py` 文件：

```text
Example_Author_1.0.0.zip
├── team.json
├── character_a.py
└── character_b.py
```

`team.json` 包含 1 至 4 个槽位。内置角色引用既有 `impl_id`；外置角色声明脚本文件、类名和
中英文显示名：

```json
{
  "format_version": 1,
  "name": "示例队伍",
  "description": "队伍循环和使用说明",
  "author": "作者昵称",
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

`display` 可省略，此时会回退为类名或内置实现名。外置脚本必须是 UTF-8 编码、位于 ZIP 根目录、
扩展名为 `.py`，且 `class_name` 必须是合法的 Python 标识符。

## 校验与限制

为避免仓库变成文件托管服务，每个包必须同时满足以下限制：

- ZIP 压缩后不超过 2 MiB，解压总量不超过 2 MiB。
- 最多 5 个文件；单个 Python 文件不超过 512 KiB，`team.json` 不超过 64 KiB。
- 名称最多 100 字，描述最多 2,000 字，作者最多 64 字，版本最多 32 字。
- 不接受目录项、嵌套路径、路径穿越、重复文件名、符号链接、加密 ZIP、二进制资源或未声明文件。
- 不接受数据库、角色特征、图片、模型、录像、文字出招表、凭据或与方案无关的内容。
- 校验只读取 JSON 并使用 AST 检查 Python 语法，不会导入、实例化或执行提交的 Python。

PR 使用只读权限运行校验，不会接触 CNB 同步密钥。合并到 `main` 后发布工作流会再次校验，
生成紧凑的 `teams.json`；索引超过 2 MiB 会警告，超过 5 MiB 会阻止发布。

## 提交规范

- `author` 是展示信息，不验证 GitHub 身份；请填写稳定且可识别的昵称或社区 ID。
- 请仅提交你有权发布的代码，不得包含恶意代码、侵权内容、个人资料或任何凭据。
- 提交者应自行确认代码来源、许可证和第三方依赖；维护者可拒绝或移除不符合规则的包。
- 不提供本地方案自动更新、自动覆盖或自动同步。新版本请使用新的 ZIP 和新的本地外置目录。

## 本地校验

```powershell
python scripts/build_catalog.py --check
python -m unittest discover -s tests -p "test_*.py"
```

## 仓库地址

- GitHub 主仓库：[BnanZ0/ok-nte-char-code](https://github.com/BnanZ0/ok-nte-char-code)
- GitHub 上传目录：[codes/](https://github.com/BnanZ0/ok-nte-char-code/tree/main/codes)
- CNB 镜像：[BnanZ0/ok-nte-char-code](https://cnb.cool/BnanZ0/ok-nte-char-code)
