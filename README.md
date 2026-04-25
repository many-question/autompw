# AutoMPW

AutoMPW 是一个用于 MPW 流片拼版的 Python CLI 工具。它把多个子设计 GDS 按指定坐标放入一个 MPW 顶层版图中，生成 framework GDS 和 placeholder GDS，基于 Calibre deck 模板生成 dummy fill 结果，并最终拼合输出 MPW GDS。

项目目标部署环境是 Linux EDA 环境。基础检查、GDS 生成、deck 渲染 dry-run 和单元测试不依赖 Calibre；真实 dummy fill 需要 Calibre 环境。

## 当前功能

- 生成模板配置文件：`autompw init`
- 检查子设计放置是否合法
- 支持 9 种坐标锚点：四角、四边中点、中心点
- 生成 framework GDS：
  - 覆盖整个 MPW 尺寸的 marker rectangle
  - 每个子设计的 marker rectangle
  - 每个子设计外扩后的 dummy blocker 层
  - 每个子设计边缘补充 edge fill ring
- dummy blocker 和 edge fill 外扩后自动裁剪到 MPW bbox 内
- 生成 placeholder blank GDS：
  - 只包含 marker 层
  - 不包含 dummy blocker、edge fill 或其他层
- 为 MPW dummy fill 和 placeholder fill 渲染 Calibre deck
- 自动写入 Calibre 运行期字段：
  - `LAYOUT PATH`
  - `LAYOUT PRIMARY`
  - output GDS
  - summary report
  - `xLB/yLB/xRT/yRT`
- 拼合最终 MPW GDS
- 输出 placement manifest

## 文件结构

当前主要文件结构如下：

```text
autompw/
  autompw/
    cli.py              CLI 命令入口
    config.py           YAML 配置解析
    geometry.py         bbox、anchor、spacing 检查
    framework.py        framework / placeholder blank GDS 生成
    dummy.py            dummy fill / placeholder Calibre 任务生成
    calibre.py          deck 渲染和 Calibre 调用
    assemble.py         最终 GDS 拼合
    gds_io.py           KLayout GDS 读写工具
    templates.py        init 命令使用的默认配置模板
  bin/
    autompw             Linux 可执行入口
  deck/
    dummy_script_metal  metal dummy fill deck 模板
    dummy_script_ODPO   OD/PO dummy fill deck 模板
  doc/
    plan.md             开发计划
    test_plan.md        Linux 测试方案
  examples/
    mpw_2512.yaml       示例配置
  tests/
    test_*.py           单元测试
  MPW_2512.gds          参考 GDS
  pyproject.toml
```

## 安装

推荐在 Linux 上使用虚拟环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install pytest
```

安装后可以直接使用：

```bash
autompw --help
```

仓库也提供 Linux 可执行入口。如果暂时不想安装 package，可以在项目根目录运行：

```bash
./bin/autompw --help
```

`bin/autompw` 实际调用：

```bash
python3 -m autompw.cli "$@"
```

## 依赖

Python 依赖定义在 [pyproject.toml](pyproject.toml)：

- `typer`
- `pyyaml`
- `klayout`

真实 dummy fill 还需要 Linux 环境中可用的：

- `calibre`
- `csh`
- 对应的 Calibre setup script，例如 `/edamgr/setup_calibre.csh`

## 快速开始

生成一份模板配置：

```bash
autompw init
```

默认输出：

```text
mpw_config.yaml
```

也可以指定路径：

```bash
autompw init my_mpw.yaml
```

如果目标文件已经存在，`init` 会拒绝覆盖。

检查示例配置：

```bash
autompw check examples/mpw_2512.yaml
```

生成 framework GDS：

```bash
autompw framework examples/mpw_2512.yaml
```

只渲染 Calibre deck，不运行 Calibre：

```bash
autompw dummy-fill examples/mpw_2512.yaml --dry-run
autompw placeholders examples/mpw_2512.yaml --dry-run
```

运行完整流程：

```bash
autompw all examples/mpw_2512.yaml
```

如果只是验证 deck 渲染，不想真实运行 Calibre：

```bash
autompw all examples/mpw_2512.yaml --dry-run-calibre
```

## CLI 命令

```bash
autompw init [CONFIG.yaml]
autompw check CONFIG.yaml
autompw framework CONFIG.yaml
autompw dummy-fill CONFIG.yaml [--dry-run]
autompw placeholders CONFIG.yaml [--dry-run]
autompw assemble CONFIG.yaml
autompw all CONFIG.yaml [--dry-run-calibre]
autompw inspect-gds FILE.gds
```

### `init`

创建模板配置文件。

```bash
autompw init
autompw init examples/new_mpw.yaml
```

默认文件名为 `mpw_config.yaml`。

### `check`

检查拼版几何是否合法。

```bash
autompw check examples/mpw_2512.yaml
```

检查内容：

- 每个子设计 bbox 必须在 MPW bbox 内
- 子设计之间不能重叠
- 子设计之间 spacing 必须不小于 `spacing.design_to_design_um`

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

输出路径来自：

```yaml
output:
  framework_gds: ./build/framework.gds
```

framework GDS 包含：

- MPW 全尺寸 marker rectangle
- 每个子设计的 marker rectangle
- 每个子设计的 dummy blocker 外扩层
- 每个子设计的 edge fill ring

dummy blocker 和 edge fill ring 都会被 clip 到 MPW bbox 内。

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
- 输出 GDS：由 topcell、flow 名和 `output_suffix` 组合生成

### `placeholders`

为每个子设计生成 blank placeholder GDS，然后渲染独立 Calibre deck，并在非 `--dry-run` 模式下调用 Calibre 往 placeholder 中填充 dummy。

```bash
autompw placeholders examples/mpw_2512.yaml --dry-run
autompw placeholders examples/mpw_2512.yaml
```

blank placeholder GDS 只包含 marker 层，不包含 dummy blocker 层或 edge fill 层。

每个 placeholder 的运行期信息由程序自动生成：

- 输入 GDS：该子设计生成的 blank placeholder GDS
- 输入 topcell：`PLACEHOLDER_<design_name>`
- chip window：该子设计尺寸
- 输出 GDS：由设计名、flow 名和 `output_suffix` 组合生成

### `assemble`

拼合最终 MPW GDS。

```bash
autompw assemble examples/mpw_2512.yaml
```

最终 GDS 路径来自：

```yaml
output:
  final_gds: ./build/mpw_final.gds
```

同时会生成：

```text
mpw_final.manifest.json
```

manifest 中记录每个子设计的源 GDS、topcell、放置 bbox 和是否使用 placeholder 替换。

### `all`

完整流程：

```text
check -> framework -> dummy-fill -> placeholders -> assemble
```

```bash
autompw all examples/mpw_2512.yaml
```

dry-run Calibre：

```bash
autompw all examples/mpw_2512.yaml --dry-run-calibre
```

### `inspect-gds`

查看 GDS 信息：

```bash
autompw inspect-gds MPW_2512.gds
```

输出包含：

- DBU
- topcell 列表
- topcell bbox
- layer/datatype 列表

## 配置文件

主输入是 YAML 文件。示例见 [examples/mpw_2512.yaml](examples/mpw_2512.yaml)。

### MPW

```yaml
mpw:
  name: MPW_2512
  size_um: [3333, 2222]
  origin: [0, 0]
```

MPW 边界只用于检查子设计是否越界；不会检查子设计到 MPW 边界的划片距离。

### spacing

```yaml
spacing:
  design_to_design_um: 50
```

当前只检查子设计之间的间距。如果不写该字段，默认值为 `50` um。

### Calibre

示例配置：

```yaml
calibre:
  executable: calibre
  shell: csh
  setup_script: /edamgr/setup_calibre.csh
  args: "-drc -hier -turbo 8 -turbo_all -hyper connect"
  work_dir: ./build/calibre
  flows:
    metal:
      enabled: true
      deck_template: ../deck/dummy_script_metal
      output_suffix: _DM
      summary_name: DM.sum
    odpo:
      enabled: true
      deck_template: ../deck/dummy_script_ODPO
      output_suffix: _DODPO
      summary_name: DODPO.sum
```

说明：

- `calibre` 是全局配置，MPW dummy fill 和 placeholder fill 都复用它。
- `deck_template` 是相对 YAML 文件所在目录解析的路径。
- 示例配置文件在 `examples/` 目录下，所以 `../deck/dummy_script_metal` 指向仓库根目录的 `deck/dummy_script_metal`。
- YAML 中不配置每次运行的输入 GDS、输出 GDS、topcell 和 chip window。这些由当前任务自动派生。

### layers

```yaml
layers:
  marker: [0, 0]
  dummy_blocker:
    layers:
      - layer: [150, 1]
        grow_um: 1
      - layer: [150, 9]
        grow_um: 3
  edge_fill:
    layers:
      - [5, 0]
      - [162, 2]
    ring_width_um: 0.45
```

说明：

- `marker` 用于 MPW 全尺寸 marker、子设计 marker 和 placeholder blank GDS。
- `dummy_blocker.layers` 只用于 framework GDS。
- 每个 dummy blocker 层可以单独设置外扩尺寸。
- `edge_fill` 只用于 framework GDS。
- placeholder blank GDS 不写入 dummy blocker 或 edge fill 层。

### GDS

```yaml
gds:
  topcell: MPW_2512
  dbu_um: 0.001
  flatten_final: false
  preserve_child_cells: true
  allow_cell_rename: true
```

当前实现要求参与拼合的 GDS 使用一致的 DBU。

### output

```yaml
output:
  build_dir: ./build
  framework_gds: ./build/framework.gds
  final_gds: ./build/mpw_final.gds
```

相对路径按 YAML 文件所在目录解析。

### designs

```yaml
designs:
  - name: HSY
    gds: ./input/L0_TOP_HSY.gds
    topcell: L0_TOP_v2
    size_um: [987.320, 987.320]
    coord: [1057.000, 0.000]
    anchor: bottom_left
    replace_with_placeholder: false

  - name: ZSY
    gds: ./input/L0_TOP_HSY.gds
    topcell: L0_TOP_v2
    size_um: [987.320, 987.320]
    coord: [0.000, 0.000]
    anchor: bottom_left
    replace_with_placeholder: true
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

`replace_with_placeholder`：

- `false`：最终拼合时使用原始子设计 GDS
- `true`：最终拼合时使用该子设计对应的 placeholder GDS

## Calibre deck 渲染机制

AutoMPW 不会原地修改 `deck_template`。每次运行时，程序会读取模板，替换运行期字段，并把 rendered deck 写到 build 目录。

会自动替换的字段包括：

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

其他 foundry 规则、开关、layer map、density 参数和 fill 规则保留在 deck 模板中，由用户手工维护。

MPW dummy fill 的 rendered deck 示例路径：

```text
examples/build/calibre/mpw/metal/MPW_2512_metal.svrf
examples/build/calibre/mpw/odpo/MPW_2512_odpo.svrf
```

placeholder 的 rendered deck 示例路径：

```text
examples/build/calibre/placeholders/<design_name>/metal/<design_name>_metal.svrf
examples/build/calibre/placeholders/<design_name>/odpo/<design_name>_odpo.svrf
```

## Linux 测试流程

完整测试方案见 [doc/test_plan.md](doc/test_plan.md)。

常用测试命令：

```bash
pytest -q
autompw --help
./bin/autompw --help
autompw init /tmp/mpw_config.yaml
autompw check examples/mpw_2512.yaml
autompw framework examples/mpw_2512.yaml
autompw dummy-fill examples/mpw_2512.yaml --dry-run
autompw placeholders examples/mpw_2512.yaml --dry-run
```

当前单元测试预期：

```text
14 passed
```

真实运行 Calibre 前，确认：

- `calibre` 在 PATH 中
- `csh` 已安装
- `calibre.setup_script` 存在
- YAML 中的 deck 路径指向正确模板
- 子设计 GDS 路径和 topcell 正确

## 开发

运行测试：

```bash
pytest -q
```

检查 Git 状态：

```bash
git status --short
```

`.gitignore` 已忽略常见生成文件，包括：

- `build/`
- `examples/build/`
- Python cache
- Calibre log/report
- 本地 `input/` 和 `output/` 目录

