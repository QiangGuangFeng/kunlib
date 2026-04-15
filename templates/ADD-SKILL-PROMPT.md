# KunLib 添加技能 — Agent Prompt 模板

Agent不是全知全能，合理的prompt和人工审查与验证尤为重要

若初次使用GitHub 和 Agent coding，也许多次修改后才能完善并成功注册你的技能，但熟能生巧

祝好运

## 使用流程

1. Fork `kzy599/kunlib`
2. 在你的 fork 里创建 `skills/<你的技能名>/` 目录
3. **有脚本的情况**：把你的脚本文件**原样放进去**（Python、R、Shell 都行，不需要做任何修改）
4. **没有脚本的情况**（编排型/信息型）：在目录里放一个简短的**描述文件**（如 `SKILL.md` 或直接在 prompt 中描述），说明技能的功能和流程
5. 复制下面的 prompt 模板，填写 7 项必填信息（4 项推荐填写）
6. 在 issue 或 comment 中 @copilot 并粘贴填好的 prompt
7. Agent 自动完成所有改造并提交到你的 fork

## --demo 模式

> **注意**：`--demo` 主要适用于 `data` 和 `generator` 类型的技能。
> `validator` 类型需要提供输入目录来校验（测试时可用合成数据目录）。
> `orchestrator` 类型的 `--demo` 应透传给所有子技能。
> `info` 类型通常不需要 `--demo`。

每个 data/generator 型技能**必须**支持 `--demo` 模式，让用户无需准备数据就能验证技能运行。

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
请参考AGENTS.md, 将 skills/<技能名>/ 目录中的脚本改造为 kunlib 标准技能。

# 🟢 必填项

技能名: <填写技能名，kebab-case，如 bindiff-gwas>
作者：Zhang3Li4Wang5
描述: <填写技能的简要描述，一句话>
技能类型: <data / generator / orchestrator / validator / info，不确定就填 data>
脚本语言: <Python / R / Shell / 混合 / 无脚本（仅描述）>
输入: <描述输入文件及格式，如 "phe.csv(ID+表型列) + geno.csv(0/1/2基因型矩阵)"。编排型填调用的子技能名，info型填"无">
输出: <描述关键输出文件，如 "ebv_result.csv(ID+EBV列), manhattan.png"。编排型填"子技能各自输出"，info型填"无/仅日志">
依赖: <列出所有外部依赖及安装方式，如 "plink 1.9(conda -c bioconda), R/data.table(CRAN), hiblup(手动下载 https://hiblup.github.io/)"。info型填"无">

# 🟡 推荐项（有则填，没有 agent 自行推理）

参数说明: <如 "trait-pos: int, 表型列位置, 默认4; threads: int, 线程数, 默认32">
方法学: <如 "VanRaden Method 1 建立 GRM，Henderson MME 求解 GBLUP">
Demo 数据: <"自带 demo/ 目录" 或 "让脚本生成" 或 不填>
参考文献: <如 "VanRaden 2008, doi:10.3168/jds.2007-0980">
其他：任何你觉得可以加深agent对技能理解的描述，甚至让技能更完善的描述都可以添加，不限于以上几项。
<如 "当前脚本并不完善，整体框架是为了输入ID、选择指数和基因型并输出配种方案，rel_mat也支持系谱，扩展系谱法">
```

> 必填 7 项（含技能类型），推荐 4+项。agent 会自动完成：`@skill` 装饰器（含 `kind`）、`SKILL.md`、`--demo` 模式、标准目录结构、测试。

## 示例

### 示例 1：data 型（有脚本）

```
请参考AGENTS.md，将 skills/bindiff-gwas/ 目录中的脚本改造为 kunlib 标准技能。

# 🟢 必填项

技能名: bindiff-gwas
作者：Zhang3Li4Wang5
描述: 利用品种间 GWAS 结果识别差异 SNP 位点
技能类型: data
脚本语言: Python
输入: "gwas_result.csv(SNP_ID + P_value + Beta列)"
输出: "diff_snp.csv(差异SNP列表), manhattan.png"
依赖: "Python/pandas(pip), Python/matplotlib(pip)"

# 🟡 推荐项

参数说明: "pval-threshold: float, P值阈值, 默认5e-8; top-n: int, 输出前N个SNP, 默认100"
方法学: "按P值过滤 SNP，基于 Beta 系数方向区分品种间差异位点"
Demo 数据: 让脚本生成
参考文献: —
```

### 示例 2：generator 型（生成合成数据）

```
请参考AGENTS.md，在 skills/sim-breeding-pop/ 中创建 kunlib 标准技能。

# 🟢 必填项

技能名: sim-breeding-pop
作者：kzy599
描述: 利用 AlphaSimR 生成合成育种群体数据（表型+基因型+系谱）
技能类型: generator
脚本语言: Python + R
输入: 无（generator 凭空生成数据）
输出: "phe.csv(个体表型), geno.csv(0/1/2基因型矩阵), ped.csv(系谱)"
依赖: "Rscript(conda -c conda-forge), R/AlphaSimR(CRAN), R/data.table(CRAN)"

# 🟡 推荐项

参数说明: "n-ind: int, 个体数, 默认200; n-snp: int, SNP数, 默认1000; h2: float, 遗传力, 默认0.3"
方法学: "AlphaSimR 模拟基础群体 → 随机交配 → 导出表型、基因型、系谱"
Demo 数据: 不需要（generator 本身就是生成数据）
参考文献: "Gaynor et al. 2021, doi:10.1534/g3.120.401882"
```

### 示例 3：orchestrator 型（无脚本，仅描述）

```
请参考AGENTS.md，在 skills/ebv-mating-pipeline/ 中创建 kunlib 标准技能。

# 🟢 必填项

技能名: ebv-mating-pipeline
作者：kzy599
描述: 先跑 hiblup-ebv 估计育种值，再拿育种值结果跑 lagm-mating 生成配种方案
技能类型: orchestrator
脚本语言: 无脚本（仅描述）
输入: 调用子技能 hiblup-ebv 和 lagm-mating
输出: 子技能各自输出
依赖: 无额外依赖（子技能自带）

# 🟡 推荐项

参数说明: "demo: flag, 透传给所有子技能"
方法学: —
Demo 数据: 透传 --demo 给子技能
参考文献: —
```

### 示例 4：validator 型（数据校验）

```
请参考AGENTS.md，将 skills/geno-qc/ 目录中的脚本改造为 kunlib 标准技能。

# 🟢 必填项

技能名: geno-qc
作者：Zhang3Li4Wang5
描述: 校验基因型文件格式（0/1/2 编码、缺失率、MAF 等）
技能类型: validator
脚本语言: Python
输入: "geno.csv(第1列ID，其余列SNP 0/1/2编码)"
输出: "validation_report.csv(每个检查项的通过/失败状态)"
依赖: "Python/pandas(pip), Python/numpy(pip)"

# 🟡 推荐项

参数说明: "max-missing-rate: float, 最大缺失率, 默认0.1; min-maf: float, 最小MAF, 默认0.01; strict: flag, 严格模式"
方法学: "检查编码范围、样本缺失率、位点MAF、重复ID等"
Demo 数据: 让脚本生成
参考文献: —
```

### 示例 5：info 型（无脚本，纯信息）

```
请参考AGENTS.md，在 skills/env-check/ 中创建 kunlib 标准技能。

# 🟢 必填项

技能名: env-check
作者：kzy599
描述: 检查当前环境中 KunLib 所需的外部工具（python3, Rscript, plink 等）是否已安装
技能类型: info
脚本语言: 无脚本（仅描述）
输入: 无
输出: 无/仅日志
依赖: 无

# 🟡 推荐项

参数说明: 无额外参数
```

## Agent 会做什么

收到 prompt 后，agent 会自动：

1. 分析你的原始脚本（如有）或描述文本（输入、输出、参数、依赖）
2. **根据"技能类型"字段选择对应的 AGENTS.md 模板**（data/generator/orchestrator/validator/info）
3. 用 `@skill` 装饰器包装，接入 KunLib 框架（包含 `kind=`、`SkillRequires` 和 `IOField` 声明）
4. 根据 kind 确定 `--input` 注入策略和输出目录结构
5. 添加 `--demo` 模式（data/generator：脚本生成合成数据或使用你提供的 demo 文件；orchestrator：透传给子技能）
6. 创建 `SKILL.md` 方法学文档
7. 编写测试（`tests/test_<skill>.py`）
8. 验证 `kunlib list` 和 `kunlib run <skill> --demo`（或对应 kind 的运行方式）均可正常工作
9. 提交到你的 fork

## 改造规则参考

详见 [AGENTS.md](../AGENTS.md) §"Converting a User Script into a KunLib Skill"。
