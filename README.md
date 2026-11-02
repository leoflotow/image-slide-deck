# image-slide-deck

面向 Codex 及其他支持 Agent Skills 的智能体，制作图片型 PowerPoint 的通用 Skill。涵盖资料梳理、大纲、视觉样张、生图、分层组装与验收，不绑定特定主题或生图模型。

## 功能

- 支持整页生图，以及图文一体的正文图片与可编辑标题、Logo、页码分层组装。
- 根据页面类型选择模式；默认在大纲和样张确认后继续批量制作。
- 通过配置和脚本校验素材、固定元素、页面模式和已保存 PPTX 的原生标题。
- 保留逐页视觉、文字和事实核对；结构检查不能代替人工查看渲染。

## 安装与使用

将本仓库作为 `image-slide-deck` 目录放入兼容智能体的 skills 目录。在 Codex 中可放在 `~/.codex/skills/image-slide-deck/`；重新打开会话后使用 `$image-slide-deck` 并说明主题、受众、页数与素材。

入口为 [SKILL.md](SKILL.md)。脚本需要 Python、Pillow 和 python-pptx；运行 `python scripts/check_environment.py` 检查环境。生图依赖所用智能体实际提供的能力，脚本本身不调用生图 API。详细用法见 [组装配置](references/assembly.md) 与 [跨环境说明](references/portability.md)。

大纲示例和配置示例在 `assets/templates/`。运行 `python -m unittest discover -s tests -v` 进行结构测试。

## 许可

MIT License。
