# MPW 拼版 CLI 小程序开发计划

## 目标

开发一个用于 MPW 流片拼版的 CLI 工具。该工具把多个子设计 GDS 按指定坐标放入一个 MPW 顶层版图中，生成 framework GDS、dummy fill GDS、placeholder GDS，并最终输出可交付流片的 MPW GDS。

工具需要支持各步骤单独运行，也需要支持一键执行完整流程。

## 技术栈选择

- 主语言：Python 3.11
- GDS 处理：优先使用 `gdsfactory 9.35.0`
- 底层 GDS API：必要时下沉到 `kfactory` / `klayout.db`
- CLI 框架：`typer`
- 配置文件：YAML，使用 `pyyaml` 或 `ruamel.yaml`
- 几何检查：第一版使用自定义 rectangle / bounding-box 检查
- Calibre 集成：由全局 YAML 配置提供 Calibre 执行环境和 deck 模板，具体输入/输出由各阶段任务自动派生

选择理由：

- 当前环境已有 `gdsfactory 9.35.0`。
- 拼版对象主要是矩形子设计，第一版不需要复杂 polygon boolean。
- CLI + YAML 更适合描述多个子设计、层配置和 dummy flow 参数。
- Calibre dummy filler 与 foundry rule deck 绑定较强。YAML 只配置 Calibre 执行环境和 deck 模板；输入 GDS、topcell、输出 GDS、summary/report 和 chip window 坐标都由当前阶段任务自动生成；其他工艺选项仍保留在 deck 模板中手工维护。

## 推荐项目结构

```text
autompw/
  pyproject.toml
  README.md
  plan.md
  examples/
    mpw_2512.yaml
  autompw/
    __init__.py
    cli.py
    config.py
    geometry.py
    gds_io.py
    framework.py
    dummy.py
    assemble.py
    report.py
  templates/
    dummy_script_metal.svrf.tpl
    dummy_script_ODPO.svrf.tpl
  tests/
    test_geometry.py
    test_config.py
```

当前仓库中的 `dummy_script_metal`、`dummy_script_ODPO` 应作为 Calibre deck 模板的来源；`fill_metal`、`fill_ODPO` 只是 Calibre 调用 wrapper，后续可由 YAML 配置替代；`MPW_2512.gds` 可作为参考 GDS；`gdsfactory_basic_usage.md` 后续可整合进 README。

## 配置文件设计

建议使用 YAML 描述一次 MPW 拼版任务。示例：

```yaml
mpw:
  name: MPW_2512
  size_um: [4000, 3000]
  origin: [0, 0]
  dicing_margin_um: 50

layers:
  marker: [0, 0]
  dummy_blocker:
    layers:
      - layer: [150, 0]
        grow_um: 1
      - layer: [150, 1]
        grow_um: 3
  edge_fill:
    layers:
      - [5, 0]
      - [162, 2]
    ring_width_um: 0.45

calibre:
  executable: calibre
  shell: csh
  setup_script: /home/cshrc/.cshrc.mentor22crack
  args: "-drc -hier -turbo 32 -turbo_all -hyper connect"
  work_dir: ./build/calibre
  flows:
    metal:
      enabled: true
      deck_template: ./templates/dummy_script_metal.svrf.tpl
      output_suffix: _DM
      summary_name: DM.sum
    odpo:
      enabled: true
      deck_template: ./templates/dummy_script_ODPO.svrf.tpl
      output_suffix: _DODPO
      summary_name: DODPO.sum

output:
  framework_gds: ./build/framework.gds
  final_gds: ./build/mpw_final.gds

designs:
  - name: adc_top
    gds: ./input/adc_top.gds
    topcell: ADC_TOP
    size_um: [800, 600]
    coord: [100, 100]
    anchor: bottom_left
    replace_with_placeholder: false

  - name: pll_top
    gds: ./input/pll_top.gds
    topcell: PLL_TOP
    size_um: [600, 500]
    coord: [3000, 2500]
    anchor: top_right
    replace_with_placeholder: true
```

`anchor` 支持以下值：

```text
bottom_left
bottom_center
bottom_right
center_left
center
center_right
top_left
top_center
top_right
```

这样可以覆盖四个角、四条边中点和中心点坐标。

## CLI 命令规划

```bash
autompw check config.yaml
autompw framework config.yaml
autompw dummy-fill config.yaml
autompw placeholders config.yaml
autompw assemble config.yaml
autompw all config.yaml
autompw inspect-gds MPW_2512.gds
```

命令职责：

- `check`：检查拼版方案是否合法。
- `framework`：生成 framework GDS。
- `dummy-fill`：基于 framework GDS 调用 dummy filler 生成 dummy fill GDS。
- `placeholders`：为每个子设计生成 blank placeholder GDS，并调用 dummy filler 生成对应 placeholder GDS。
- `assemble`：合并子设计、framework、dummy fill、placeholder，输出最终 MPW GDS。
- `all`：按顺序执行完整流程。
- `inspect-gds`：查看 GDS 的 topcell、dbu、bbox、层列表等信息。

## 步骤 1：拼版合法性检查

实现 `autompw check config.yaml`。

检查内容：

1. 坐标锚点转换
   - 根据 `coord`、`anchor` 和 `size_um` 统一转换为 bbox。
   - bbox 格式为 `[xmin, ymin, xmax, ymax]`。

2. MPW 边界检查
   - 每个子设计 bbox 必须在 MPW bbox 内。

3. 子设计互相不重叠
   - 对所有子设计 bbox 做两两 overlap 检查。

4. 划片距离检查
   - 默认 `50um`。
   - 只检查子设计之间的最小 spacing。
   - 不检查子设计到 MPW 外边界的划片距离，子设计允许紧贴 MPW 边界。

5. 输出检查报告
   - 控制台打印简要结果。
   - 可选输出 JSON 报告。

后续可以把 spacing 配置拆成：

```yaml
spacing:
  design_to_design_um: 50
```

## 步骤 2：生成 framework GDS

实现 `autompw framework config.yaml`。

framework GDS 内容：

1. MPW 外框
   - 必须在 marker 层生成一个覆盖整个 MPW 尺寸的 rectangle。
   - 默认层：`0/0`。

2. 子设计位置标记层
   - 默认层：`0/0`。
   - 每个子设计按实际有效尺寸生成 rectangle。
   - 建议 cell 名：`FW_MARK_<design_name>`。

3. dummy blocker 层
   - 默认层：`150.x`。
   - 由 marker bbox 按每个 blocker 层独立配置的 `grow_um` 外扩生成。
   - 不同 dummy blocker 层可以使用不同外扩值，例如 `150/0` 外扩 `1um`，`150/1` 外扩 `3um`。
   - 外扩后的图形必须 clip 到 MPW bbox 内，避免超出流片边界。
   - 配置解析时应同时支持显式对象格式，并可选兼容简单列表格式。

4. 边缘补充层
   - 默认层：`5/0`、`162/2`。
   - 在 marker bbox 外包 `0.45um` 的边缘 ring。
   - 建议实现为外矩形减内矩形的 ring polygon，避免覆盖整个子设计区域。
   - ring 图形必须 clip 到 MPW bbox 内。

5. GDS 单位
   - 内部统一使用 `um`。
   - 写 GDS 时明确 dbu，例如 `0.001um`。
   - 如需与参考 GDS 对齐，应从 `MPW_2512.gds` 读取 dbu。

## 步骤 3：调用 dummy filler 生成 dummy fill GDS

实现 `autompw dummy-fill config.yaml`。

流程：

1. 生成或确认 `framework.gds` 存在。
2. 将 framework GDS 作为 Calibre dummy flow 输入。
3. 根据全局 `calibre` 配置组装运行命令。
4. 根据 deck 模板生成本次运行专用 deck。
   - 原始 `dummy_script_metal`、`dummy_script_ODPO` 不直接修改。
   - 程序把模板渲染到当前任务的 build 子目录。
   - 只替换运行期字段：输入 GDS、topcell、输出 GDS、summary report、程序根据当前 GDS 任务尺寸自动生成的 chip window 坐标。
   - 这些运行期字段不在 YAML 中逐项配置，由 `dummy-fill` 或 `placeholders` 阶段根据任务上下文自动派生。
   - 其他工艺开关和 layer / density / fill 规则仍保留在模板中，允许人工修改。
5. 调用 Calibre：
   - 使用 YAML 中的 `calibre.executable`。
   - 使用 YAML 中的 `args` 字符串，例如 `"-drc -hier -turbo 32 -turbo_all -hyper connect"`。
   - 如需 `source /home/cshrc/.cshrc.mentor22crack`，由 `shell` 和 `setup_script` 配置生成 csh 命令。
6. 支持运行模式：
   - 只跑 metal dummy。
   - 只跑 ODPO dummy。
   - 两者都跑。
7. 检查外部命令返回码。
8. 检查 dummy fill 输出文件是否存在。
9. 保存日志到 build 目录。

deck 模板化方案：

- 对 `dummy_script_metal`、`dummy_script_ODPO` 复制出 `.tpl` 模板。
- 在模板 header 中把以下字段替换为占位符：

```text
LAYOUT PATH "{{ input_gds }}"
LAYOUT PRIMARY "{{ input_topcell }}"
DRC RESULTS DATABASE "{{ output_gds }}" GDSII _DM
DFM DEFAULTS RDB GDS FILE "{{ output_gds }}"
DRC SUMMARY REPORT "{{ summary_report }}"
VARIABLE xLB   {{ xLB }}
VARIABLE yLB   {{ yLB }}
VARIABLE xRT   {{ xRT }}
VARIABLE yRT   {{ yRT }}
```

- metal 和 ODPO deck 的输出语句不同，模板渲染器应按 flow 独立处理。
- deck 中的 `input_gds`、`input_topcell`、`output_gds`、`summary_report`、`xLB/yLB/xRT/yRT` 不在 YAML 中配置，由程序按当前 dummy 任务自动生成。
- 跑 MPW dummy fill 时，chip window 使用 MPW 尺寸。
- 跑子设计 placeholder 时，chip window 使用对应子设计尺寸。
- 默认本地窗口为 `[0, 0, width, height]`；如果后续需要非零原点，可由输入 GDS bbox 或任务上下文派生。
- MPW dummy fill 的输入 GDS 固定来自 `output.framework_gds`，topcell 来自 `gds.topcell` 或 `mpw.name`，输出 GDS 由任务名、flow 名和 `output_suffix` 组合生成。
- 子设计 placeholder 的输入 GDS 来自该子设计 blank GDS，topcell 由 `PLACEHOLDER_<design_name>` 生成，输出 GDS 由子设计名、flow 名和 `output_suffix` 组合生成。
- 如用户手工修改模板中的其他内容，程序不覆盖这些修改。

## 步骤 4：生成 placeholder GDS

实现 `autompw placeholders config.yaml`。

目标：

为每个子设计生成一个空白 placeholder GDS，并调用 dummy filler 往其中填充 dummy。这样当某个子设计存在问题时，可以用 placeholder 临时替换该设计。

流程：

1. 对每个子设计创建 blank GDS。
   - top cell 名：`PLACEHOLDER_<design_name>`。
   - 尺寸等于该子设计 `size_um`。
   - 原点建议为 `(0, 0)`。

2. blank GDS 内容：
   - marker rectangle。
   - 不写入 dummy blocker、edge fill 或其他层。

3. 按每个 block 的任务上下文渲染 deck 模板并调用 dummy filler。
   - 输入 GDS 使用该子设计生成的 blank GDS。
   - topcell 使用 `PLACEHOLDER_<design_name>`。
   - chip window 使用该子设计尺寸，默认为 `[0, 0, width, height]`。
   - 输出 GDS 名由子设计名、flow 名和全局 `calibre.flows.<flow>.output_suffix` 组合生成。
   - 每个 block、每个 enabled flow 都应生成独立 rendered deck 和独立日志，避免不同任务互相覆盖。
   - deck 模板中的工艺规则和开关仍由模板本身保留，不在此步骤自动改动。

4. 输出文件：

```text
build/placeholders/
  adc_top_blank.gds
  adc_top_dummy.gds
  pll_top_blank.gds
  pll_top_dummy.gds
```

## 步骤 5：最终拼合 MPW GDS

实现 `autompw assemble config.yaml`。

流程：

1. 创建 MPW top cell。
2. 引入 framework GDS。
3. 引入 dummy fill GDS。
4. 遍历每个子设计：
   - `replace_with_placeholder: false` 时引用原始子设计 GDS。
   - `replace_with_placeholder: true` 时引用对应 placeholder GDS。
5. 按配置中的坐标和 anchor 放置。
6. 输出最终 `mpw_final.gds`。
7. 生成 placement manifest，记录每个子设计的实际放置 bbox 和替换状态。

manifest 示例：

```json
{
  "adc_top": {
    "source": "./input/adc_top.gds",
    "placed_bbox_um": [100, 100, 900, 700],
    "replaced_with_dummy": false
  }
}
```

## 配置参数建议

第一版至少支持：

```yaml
units:
  user_unit: um
  dbu_um: 0.001

spacing:
  design_to_design_um: 50

calibre:
  executable: calibre
  shell: csh
  setup_script: /home/cshrc/.cshrc.mentor22crack
  args: "-drc -hier -turbo 32 -turbo_all -hyper connect"
  work_dir: ./build/calibre
  flows:
    metal:
      enabled: true
      deck_template: ./templates/dummy_script_metal.svrf.tpl
      output_suffix: _DM
      summary_name: DM.sum
    odpo:
      enabled: true
      deck_template: ./templates/dummy_script_ODPO.svrf.tpl
      output_suffix: _DODPO
      summary_name: DODPO.sum

layers:
  marker: [0, 0]
  dummy_blocker:
    layers:
      - layer: [150, 0]
        grow_um: 1
      - layer: [150, 1]
        grow_um: 3
  edge_ring:
    width_um: 0.45
    layers: [[5, 0], [162, 2]]

gds:
  topcell: MPW_TOP
  flatten_final: false
  preserve_child_cells: true
  allow_cell_rename: true
```

## 测试计划

优先测试不依赖 Calibre 的核心逻辑：

1. anchor 到 bbox 的转换。
2. bbox overlap 检查。
3. spacing 检查。
4. MPW boundary 检查。
5. YAML 配置解析和默认值。
6. 小尺寸 mock GDS 的 framework 生成。
7. GDS assemble 中 cell 引用和坐标放置。
8. dummy external command 使用 mock script 测试。

Calibre 相关测试作为 integration test：

- 只在有 Calibre 环境时运行。
- 检查外部命令返回码。
- 检查输出 GDS 是否生成。
- 保存并检查日志。

## 开发里程碑

### 里程碑 1：项目骨架和 CLI

- 创建 `pyproject.toml`。
- 创建 `autompw` Python package。
- 实现基础 CLI。
- 实现 YAML 配置加载。

### 里程碑 2：几何检查

- 实现 anchor 转 bbox。
- 实现 overlap 检查。
- 实现 spacing 检查。
- 实现 boundary 检查。
- 输出 check report。

### 里程碑 3：framework GDS 生成

- 生成 marker 层。
- 生成 dummy blocker 层。
- 生成 edge ring 层。
- 输出 framework GDS。

### 里程碑 4：GDS 拼合

- 读取子设计 GDS。
- 处理 topcell。
- 按坐标引用子设计。
- 输出 final GDS。
- 生成 placement manifest。

### 里程碑 5：dummy filler 接入

- 将 Calibre 执行环境和 flow 模板配置内化到全局 YAML。
- 将 `dummy_script_metal` / `dummy_script_ODPO` 改造为可渲染模板。
- 渲染本次运行专用 deck，按阶段任务自动替换输入 GDS、topcell、输出 GDS、summary report 和 chip window。
- 调用 Calibre 执行渲染后的 deck。
- 保存日志。
- 检查返回码和输出文件。
- 支持只运行指定 dummy flow。

### 里程碑 6：placeholder flow

- 生成每个子设计的 blank GDS。
- 根据每个子设计尺寸和 blank GDS 信息渲染独立 deck。
- 调用 Calibre 生成每个子设计的 placeholder GDS。
- 在 assemble 阶段按配置替换子设计。

### 里程碑 7：文档和样例

- 编写 README。
- 提供 `examples/mpw_2512.yaml`。
- 记录常见错误和排查方法。

## 关键技术风险

1. Calibre deck 模板化需要精确限定自动替换范围
   - 程序只替换 header 中的运行期字段，这些字段来自当前阶段任务，不来自用户逐项配置。
   - foundry 规则、开关、layer map、density 参数等仍由用户在模板中手工维护。
   - 渲染时不能直接覆盖模板源文件，只能输出到 build 目录。

2. 子设计 GDS topcell 选择
   - 部分 GDS 可能有多个 topcell。
   - 配置中需要支持显式指定 `topcell`。

3. 坐标原点约定
   - 建议 MPW 原点固定为左下角。
   - 所有 report 使用同一坐标系。

4. GDS 单位和 dbu 不一致
   - 合并前检查子 GDS、framework GDS 和 dummy GDS 的 dbu。
   - 必要时统一转换。

5. cell name 冲突
   - 多个子设计可能存在同名 cell。
   - assemble 阶段需要支持自动 rename 或 namespace 前缀。

6. placeholder 与真实子设计替换的一致性
   - placeholder GDS 的本地原点、尺寸、topcell bbox 必须与被替换子设计一致。

## 推荐实施顺序

第一版先完成：

```text
check -> framework -> assemble
```

这样可以优先验证拼版几何和最终 GDS 输出正确性。

第二版再完成：

```text
dummy-fill -> placeholders -> replacement assemble
```

这样可以把 foundry dummy flow 的不确定性隔离到后续阶段，降低第一版开发风险。
