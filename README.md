# AutoMPW

AutoMPW 是一个用于 MPW 流片拼版的 Python CLI 工具。它可以把多个子设计 GDS 按指定坐标放入一个 MPW 顶层版图中，生成 framework GDS 和 placeholder GDS，基于模板渲染 Calibre dummy fill deck，并最终拼合输出交付流片用的 MPW GDS。

项目目标部署环境是 Linux EDA 环境，真实 dummy fill 依赖 Calibre。基础开发和单元测试不依赖 Calibre。

## 功能

- 检查 MPW 拼版几何合法性。
- 支持用四个角、四条边中点或中心点作为放置坐标锚点。
- 生成 framework GDS，包括：
  - 覆盖整个 MPW 尺寸的 marker rectangle
  - 位置标记层
  - dummy blocker 层
  - 边缘补充 ring 层
- 支持每种 dummy blocker 层单独配置外扩尺寸。
- 从已有 Calibre deck 模板渲染本次运行专用 deck。
- 自动根据当前任务生成 Calibre 运行期字段：
  - 输入 GDS
  - 输入 topcell
  - 输出 GDS
  - summary report
  - chip window 坐标
- 为每个子设计生成 blank placeholder GDS，并调用 Calibre 往其中填充 dummy。
- 拼合 framework、dummy fill、原始子设计 GDS 和可选 placeholder GDS，输出最终 MPW GDS。

## 目录结构

```text
autompw/
  autompw/                 Python 包
  doc/
    plan.md                开发计划
    test_plan.md           Linux 测试方案
  examples/
    mpw_2512.yaml          示例配置
  tests/                   单元测试
  dummy_script_metal       metal dummy fill Calibre deck 来源/模板
  dummy_script_ODPO        OD/PO dummy fill Calibre deck 来源/模板
  MPW_2512.gds             参考 framework GDS
  pyproject.toml
```

## 安装

在 Linux 中执行：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install pytest
```

确认 CLI 可用：

```bash
autompw --help
```

Python 依赖定义在 [pyproject.toml](pyproject.toml)：

- `typer`
- `pyyaml`
- `klayout`

## 快速测试

运行单元测试：

```bash
pytest -q
```

预期结果：

```text
9 passed
```

检查参考 GDS：

```bash
autompw inspect-gds MPW_2512.gds
```

检查示例拼版配置：

```bash
autompw check examples/mpw_2512.yaml
```

生成 framework GDS：

```bash
autompw framework examples/mpw_2512.yaml
```

只渲染 Calibre deck，不真实运行 Calibre：

```bash
autompw dummy-fill examples/mpw_2512.yaml --dry-run
```

完整 Linux 测试流程见 [doc/test_plan.md](doc/test_plan.md)。

## CLI 命令

```bash
autompw check CONFIG.yaml
autompw framework CONFIG.yaml
autompw dummy-fill CONFIG.yaml [--dry-run]
autompw placeholders CONFIG.yaml [--dry-run]
autompw assemble CONFIG.yaml
autompw all CONFIG.yaml [--dry-run-calibre]
autompw inspect-gds FILE.gds
```

### `check`

检查拼版配置是否合法。

```bash
autompw check examples/mpw_2512.yaml
```

检查内容：

- 每个子设计 bbox 必须在 MPW bbox 内。
- 子设计之间不能重叠。
- 子设计之间的 spacing 必须不小于 `spacing.design_to_design_um`。

注意：不会检查子设计到 MPW 边界的划片距离。子设计可以紧贴 MPW 边界，只要没有超出 MPW bbox。

可选输出 JSON 报告：

```bash
autompw check examples/mpw_2512.yaml --report build/check_report.json
```

### `framework`

生成 framework GDS。

```bash
autompw framework examples/mpw_2512.yaml
```

输出路径来自配置：

```yaml
output:
  framework_gds: ./build/framework.gds
```

### `dummy-fill`

为 MPW 级 dummy fill 渲染 Calibre deck，并在非 `--dry-run` 模式下调用 Calibre。

```bash
autompw dummy-fill examples/mpw_2512.yaml --dry-run
autompw dummy-fill examples/mpw_2512.yaml
```

MPW dummy fill 的运行期信息由程序自动生成：

- 输入 GDS：`output.framework_gds`
- 输入 topcell：`gds.topcell` 或 `mpw.name`
- chip window：MPW 尺寸
- 输出 GDS：由 topcell、flow 名称和 `output_suffix` 组合生成

### `placeholders`

为每个子设计生成 blank placeholder GDS，按每个 block 的尺寸渲染独立 Calibre deck，并在非 `--dry-run` 模式下调用 Calibre 往其中填充 dummy。blank placeholder GDS 只包含 marker 层，不包含 dummy blocker 层或 edge fill 层。

```bash
autompw placeholders examples/mpw_2512.yaml --dry-run
autompw placeholders examples/mpw_2512.yaml
```

每个子设计 placeholder 的运行期信息由程序自动生成：

- 输入 GDS：该子设计的 blank GDS
- 输入 topcell：`PLACEHOLDER_<design_name>`
- chip window：该子设计尺寸
- 输出 GDS：由设计名、flow 名称和 `output_suffix` 组合生成

### `assemble`

拼合最终 MPW GDS。

```bash
autompw assemble examples/mpw_2512.yaml
```

最终 GDS 路径来自配置：

```yaml
output:
  final_gds: ./build/mpw_final.gds
```

同时会在最终 GDS 旁边生成 placement manifest：

```text
mpw_final.manifest.json
```

### `all`

执行完整流程：

```text
check -> framework -> dummy-fill -> placeholders -> assemble
```

```bash
autompw all examples/mpw_2512.yaml
```

如果只是验证 deck 渲染，不想真实运行 Calibre：

```bash
autompw all examples/mpw_2512.yaml --dry-run-calibre
```

## 配置文件

主输入是 YAML 文件，示例见 [examples/mpw_2512.yaml](examples/mpw_2512.yaml)。

### MPW 尺寸

```yaml
mpw:
  name: MPW_2512
  size_um: [3333, 2222]
  origin: [0, 0]
  dicing_margin_um: 50
```

如果没有设置 `spacing.design_to_design_um`，`dicing_margin_um` 会作为子设计之间 spacing 的默认值。它不用于检查子设计到 MPW 边界的距离。

### 拼版间距

```yaml
spacing:
  design_to_design_um: 50
```

当前只检查子设计之间的间距。

### Calibre

```yaml
calibre:
  executable: calibre
  shell: csh
  setup_script: /home/cshrc/.cshrc.mentor22crack
  args: "-drc -hier -turbo 32 -turbo_all -hyper connect"
  work_dir: ./build/calibre
  flows:
    metal:
      enabled: true
      deck_template: ../dummy_script_metal
      output_suffix: _DM
      summary_name: DM.sum
    odpo:
      enabled: true
      deck_template: ../dummy_script_ODPO
      output_suffix: _DODPO
      summary_name: DODPO.sum
```

`calibre` 是全局配置，不只属于 `dummy-fill` 阶段。MPW dummy fill 和子设计 placeholder 都复用这套配置。

YAML 中不配置每次运行的输入/输出文件和 chip window。程序会根据当前阶段任务自动派生这些字段，并写入 rendered deck。

### 层配置

```yaml
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
```

每个 dummy blocker 层都可以独立设置外扩尺寸。

在 framework GDS 中，dummy blocker 外扩图形和 edge fill ring 都会被裁剪到 MPW bbox 内，避免超出流片边界。生成子设计 blank placeholder GDS 时，只写入覆盖该子设计本地尺寸 `[0, 0, width, height]` 的 marker 层，其他层不写入。

### GDS 设置

```yaml
gds:
  topcell: MPW_2512
  dbu_um: 0.001
  flatten_final: false
  preserve_child_cells: true
  allow_cell_rename: true
```

当前实现要求参与拼合的 GDS 使用一致的 DBU。

### 输出路径

```yaml
output:
  build_dir: ./build
  framework_gds: ./build/framework.gds
  final_gds: ./build/mpw_final.gds
```

相对路径会按 YAML 文件所在目录解析。

### 子设计

```yaml
designs:
  - name: example_block
    gds: ./input/example_block.gds
    topcell: EXAMPLE_BLOCK
    size_um: [500, 500]
    coord: [0, 0]
    anchor: bottom_left
    replace_with_placeholder: false
```

支持的 `anchor`：

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

如果希望最终拼版时用 placeholder 替换某个子设计，设置：

```yaml
replace_with_placeholder: true
```

## Calibre deck 渲染机制

AutoMPW 不会原地修改原始 deck 文件。程序会读取 `deck_template`，替换运行期字段，然后把 rendered deck 写到 build 目录中。

程序会自动替换的字段：

```text
LAYOUT PATH
LAYOUT PRIMARY
DRC RESULTS DATABASE
DFM DEFAULTS RDB GDS FILE
DRC SUMMARY REPORT
VARIABLE xLB
VARIABLE yLB
VARIABLE xRT
VARIABLE yRT
```

其他 foundry 规则、开关、layer map、density 参数和 fill 规则都保留在 deck 模板中，由用户手工维护。

## Linux 迁移检查清单

在 Linux 上 clone 后：

```bash
git clone https://github.com/many-question/autompw.git
cd autompw
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install pytest
pytest -q
```

然后验证示例：

```bash
autompw check examples/mpw_2512.yaml
autompw framework examples/mpw_2512.yaml
autompw dummy-fill examples/mpw_2512.yaml --dry-run
```

真实运行 Calibre 前，确认：

- `calibre` 在 PATH 中。
- `csh` 已安装。
- `calibre.setup_script` 在 Linux 主机上存在。
- YAML 中的 deck 路径指向正确的 deck 模板。
- 子设计 GDS 路径和 topcell 正确。

## 开发

运行测试：

```bash
pytest -q
```

提交前检查 Git 状态：

```bash
git status --short
```

`.gitignore` 已忽略常见生成文件，包括：

- `build/`
- `examples/build/`
- Python cache
- Calibre log/report
- 本地 `input/` 和 `output/` 目录
