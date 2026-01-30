# PKPM-CAE 叠合梁参数化建模工具（交接版）

本仓库用于交接“PKPM-CAE 叠合梁参数化建模工具”项目：从 Excel/UI 参数生成可在 PKPM-CAE 运行的 PyPCAE 脚本，覆盖客户反馈的关键建模/验收点，并内置 `[CHECK]` 体检日志用于定量验收与快速定位问题。

## 你需要先知道的 3 件事（非常重要）

1. PKPM 脚本建模运行时，控制台 traceback 里常显示 `instance.py`：这是 PKPM 运行时把脚本内容落盘后的名字，不是我们额外维护的第二份源码入口。
2. “几何阶段不强行 Coupling/支座/叠合面 Tie”：官方技术定调为网格后在有限元环境里做。脚本会预置参考点与 Nset 集合，并在末尾打印“分析前必做 3 步指南”。
3. 所有修复以控制台 `[CHECK] item expected=... actual=... => PASS/FAIL` 为准：FAIL（STRICT）会直接 `raise RuntimeError` 中断，避免残次品输出。

## 目录结构（建议从这里开始看）

- `阶段成果/pkpm_composite_beam_V3.2_FINAL/pkpm_composite_beam/`
  - `ui_main_pro.py`：UI（生成 Excel + 调用生成器）
  - `main.py`：生成器核心（读取 Excel → 生成 `pkpm_composite_beam_model.py`）
  - `core/rebar_engine.py`：配筋引擎（全局箍筋 ring13、洞口补强、角部纵筋、避洞等）
  - `parsers/excel_parser.py`：Excel 参数解析与模板导出（含 Prestress.Method）
  - `test_final_acceptance.xlsx` / `test_final_acceptance.xlsx`：验收用例（7.8m 专家工况）
  - `pkpm_composite_beam_model.py`：生成后的“可在 PKPM 运行”的脚本（会覆盖更新）
- `Demond/README.md`：PyPCAE 手册摘录与用法（遇到 API 不确定时必须先查这里）
- `阶段反馈意见/`：客户与官方反馈（docx/pdf）
- `任务说明/`、`项目小结/`：过程文档

## 快速开始（新同事 10 分钟上手）

### A. 运行 UI（推荐）

1) 进入目录：

`阶段成果/pkpm_composite_beam_V3.2_FINAL/pkpm_composite_beam/`

2) 运行：

`运行_UI界面.bat`

3) 在 UI 里选择/生成 Excel，然后点击生成脚本。

输出脚本固定生成到：

`阶段成果/pkpm_composite_beam_V3.2_FINAL/pkpm_composite_beam/pkpm_composite_beam_model.py`

### B. 命令行生成（调试用）

在 `阶段成果/pkpm_composite_beam_V3.2_FINAL/pkpm_composite_beam/` 下：

`python main.py --excel test_final_acceptance.xlsx`

### C. 在 PKPM-CAE 里运行

在 PKPM-CAE 的“几何模型 → 脚本建模”中加载/粘贴 `pkpm_composite_beam_model.py` 并运行，观察控制台 `[CHECK]` 段落是否 `summary => PASS`。

## 关键验收点（对应 `[CHECK]` 证据）

以下是当前版本已经稳定 PASS 的典型项（以最新一次验收控制台为准）：

- 洞口净空 + 钢筋避让：`rebar.hole_void.edges`
- 洞口侧边箍筋贯通全高：`hole.side_stirrup.full_height.left/right`
- 洞口上下小梁 ring13 + 严格 Z 带：`rebar.local_small_beam`（badz=0）
- 波纹管孔道健壮性（避免端面共面）：`duct.mode/internal` + `duct.ends_on_beam_faces=False` + `duct.cap_surfs=2`
- 波纹管避洞口/不外露：`duct.z_avoid_hole` / `duct.within_web_y` / `duct.within_web_z`
- 右端简支是一排点：`support.right.linear_nodes`
- 网格后耦合流：`support.post_mesh_mode` + `coupling.registered expected=skipped`
- 面荷载（Surface Load）：`load.uniform.mode=Ebsload` + `load.uniform.surface_esides>0`
- 预应力闭环与开关：`prestress.method` / `prestress.excel_enabled` / `prestress.applied`

## 预应力说明（先张/后张）

- `Prestress.Method=post_tension`：后张法，可预留孔道（duct）并施加预应力。
- `Prestress.Method=pretension`：先张法，不挖孔道（脚本会强制 `duct_diameter=0`），仅施加 `PreStress`（更稳的网格/更符合常见工程流程）。

## 时间线（交接用）

> 以“问题→修复→证据”的方式记录，便于后续追溯。

- 2026-01-07：形成 7.8m 复杂工况方向；开始引入洞口/补强/支座/荷载等全链路。
- 2026-01-12：引入 STRICT/DEBUG 自检框架；逐条把“洞口净空、箍筋闭合、Coupling/支座、荷载注入”等变成定量输出（见 `阶段反馈意见/20260112调试意见.*`）。
- 2026-01-13：官方技术支持定调：几何阶段 Nset 不适合“选表面节点做耦合”；Coupling/约束应网格后在有限元模块创建。由此落地“post_mesh 支撑流 + 预置集合/参考点 + 3 步指南”（见 `阶段反馈意见/1.13补充信息.txt`）。
- 2026-01-14~01-16：处理 tmesh Sweep 崩溃/非流形风险：孔道两端内收 1mm（避免与端面共面），并加入 `duct.mode/internal` + `duct.cap_surfs` 证据项。
- 2026-01-15：客户指出洞口小梁箍筋“到顶/缺外箍”；落地洞顶/洞底 ring13 + Z 带限制，并加入 `rebar.local_small_beam` STRICT 自检（见 `阶段反馈意见/20260115调试意见.docx`）。
- 2026-01-16~01-19：补齐 `Prestress.Method`（UI/Excel/脚本闭环），并修复自检计算细节（嵌套 locals() 误用导致误判）。

## 当前遗留/下一步（给接手同事）

1) tmesh Sweep 0xc0000005 仍可能在某些网格尺寸触发：脚本已规避“端面共面孔道”并给出指南；如需更彻底，建议研究是否能在脚本侧强制 tetra（目前 API 未暴露）。
2) “叠合面 Tie”目前只做操作引导与集合预置：若后续 PKPM 提供几何阶段可选面的 API，可考虑自动化 Tie（需先对照手册验证）。
3) 若要对外发布 EXE：优先跑 `PKPM叠合梁工具.spec` 的打包链路，并在 README 增加发布/版本号规范。

## 贡献/修改注意事项

- 不要猜 API：遇到不确定方法，先查 `Demond/README.md` 与 `Demond/` 示例脚本。
- 所有修复都必须补 `[CHECK]` 证据项，并能在客户用例上复现 PASS。
