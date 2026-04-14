# KunLib 添加技能 — Agent Prompt 模板

## 使用流程

1. Fork `kzy599/kunlib`
2. 在你的 fork 里创建 `skills/<你的技能名>/` 目录
3. 把你的脚本文件**原样放进去**（Python、R、Shell 都行，不需要做任何修改）
4. 复制下面的 prompt 模板，填写 3 项基本信息
5. 在 issue 或 comment 中 @copilot 并粘贴填好的 prompt
6. Agent 自动完成所有改造并提交到你的 fork

## --demo 模式

每个技能**必须**支持 `--demo` 模式，让用户无需准备数据就能验证技能运行。

Demo 数据有两种来源，agent 会自动选择最合适的方式：

| 方式 | 做法 | 适用场景 |
|------|------|----------|
| **脚本生成（推荐）** | `--demo` 时在 `work/` 中动态生成合成数据 | 大多数场景 |
| **静态文件** | 放在 `skills/<名>/demo/` 目录中 | 数据格式复杂、难以自动生成时 |

**推荐做法：不放文件，让脚本生成。** 这样仓库更轻，demo 数据也更容易保持与代码同步。

### 如果你自带 demo 数据文件

放在 `skills/<技能名>/demo/` 目录下，遵守以下限制：

| 限制项 | 要求 | 原因 |
|--------|------|------|
| 单文件大小 | ≤ 5 MB | GitHub 超过 50MB 拒绝 push，超过 100MB 需要 Git LFS |
| demo/ 总大小 | ≤ 20 MB | 保持仓库轻量，clone 速度快 |
| 文件格式 | 纯文本优先（CSV/TSV/JSON） | 便于 diff 和 review |
| 数据内容 | **合成数据或公开数据** | 绝不能含真实个体遗传数据 |
| 数据量 | 10-100 条记录 | 验证流程即可，不是 benchmark |

### 如果你不提供 demo 数据

不需要做任何事。agent 会根据你的脚本自动添加合成数据生成逻辑。

## Prompt 模板

```
@copilot 请将 skills/<技能名>/ 目录中的脚本改造为 kunlib 标准技能。

技能名: <填写技能名，kebab-case，如 bindiff-gwas>
描述: <填写技能的简要描述>
脚本语言: <Python / R / Shell / 混合>
```

> 只需填 3 行。agent 会自动完成：`@skill` 装饰器、`SKILL.md`、`--demo` 模式、标准目录结构、测试。

## 示例

```
@copilot 请将 skills/bindiff-gwas/ 目录中的脚本改造为 kunlib 标准技能。

技能名: bindiff-gwas
描述: 利用品种间 GWAS 结果识别差异 SNP 位点
脚本语言: Python
```

## Agent 会做什么

收到 prompt 后，agent 会自动：

1. 分析你的原始脚本（输入、输出、参数、依赖）
2. 用 `@skill` 装饰器包装，接入 KunLib 框架
3. 添加 `--demo` 模式（脚本生成合成数据 或 使用你提供的 demo 文件）
4. 创建 `SKILL.md` 方法学文档
5. 编写测试（`tests/test_<skill>.py`）
6. 验证 `kunlib list` 和 `kunlib run <skill> --demo` 均可正常工作
7. 提交到你的 fork

## 改造规则参考

详见 [AGENTS.md](../AGENTS.md) §"Converting a User Script into a KunLib Skill"。
