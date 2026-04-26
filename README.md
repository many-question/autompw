# AutoMPW

AutoMPW 是一个用于 MPW 流片拼版的 Python CLI 工具。它把多个子设计 GDS 按指定坐标放入一个 MPW 顶层版图中，生成 framework GDS 和 placeholder GDS，基于 Calibre deck 模板生成 dummy fill 结果，并最终拼合输出 MPW GDS。

项目目标部署环境是 Linux EDA 环境。基础检查、GDS 生成、deck 渲染 dry-run 和单元测试不依赖 Calibre；真实 dummy fill 需要 Calibre 环境。

## 当前功能

- `autompw init <process>`：从工艺模板初始化当前工作目录
- 检查子设计放置是否合法
- 支持 9 种坐标锚点：四角、四边中点、中心点
- 生成 framework GDS：MPW 全尺寸 marker、子设计 marker、dummy blocker、edge fill ring
- dummy blocker 和 edge fill 外扩后自动裁剪到 MPW bbox 内
- 生成只包含 marker 层的 placeholder blank GDS，并和各 dummy flow 输出合并为最终 placeholder GDS
- 为 MPW dummy fill 和 placeholder fill 渲染 Calibre deck
- 拼合最终 MPW GDS，并输出 placement manifest

## 文件结构

```text
autompw/
  autompw/                 Python 包和 CLI 实现
  bin/autompw              Linux 可执行入口
  templates/tsmc28/        TSMC28 工艺初始化模板
    mpw_config.yaml
    deck/
      dmfill_metal
      dmfill_odpo
  doc/
    plan.md
    test_plan.md
  tests/
  MPW_2512.gds
  pyproject.toml
```

## 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install pytest
```

安装后：

```bash
autompw --help
```

也可以在项目根目录直接调用仓库内入口：

```bash
./bin/autompw --help
```

## 依赖

Python 依赖：

- `typer`
- `pyyaml`
- `klayout`

真实运行 Calibre 还需要：

- `calibre`
- `csh`
- 对应的 Calibre setup script，例如 `/edamgr/setup_calibre.csh`

## 快速开始

在一个新的工作目录中初始化：

```bash
mkdir my_mpw
cd my_mpw
autompw init tsmc28
```

`init` 会在当前目录创建：

```text
mpw_config.yaml
deck/
input/
output/
work/
```

其中：

- `mpw_config.yaml` 来自 AutoMPW 安装目录的 `templates/tsmc28/mpw_config.yaml`
- `deck/` 来自 AutoMPW 安装目录的 `templates/tsmc28/deck/`
- 如果 `mpw_config.yaml` 或 `deck/` 已存在，命令会拒绝覆盖

初始化后，各流程命令都可以省略配置文件名，默认读取当前目录的 `./mpw_config.yaml`：

```bash
autompw check
autompw framework
autompw dummy-fill --dry-run
autompw placeholders --dry-run
```

完整流程：

```bash
autompw all
```

只验证 deck 渲染、不真实运行 Calibre：

```bash
autompw all --dry-run-calibre
```

## CLI 命令

```bash
autompw init PROCESS
autompw check [CONFIG.yaml]
autompw framework [CONFIG.yaml]
autompw dummy-fill [CONFIG.yaml] [--dry-run]
autompw placeholders [CONFIG.yaml] [--dry-run]
autompw assemble [CONFIG.yaml]
autompw all [CONFIG.yaml] [--dry-run-calibre]
autompw inspect-gds FILE.gds
```

### `init`

按工艺模板初始化当前目录：

```bash
autompw init tsmc28
```

当前仓库提供的工艺模板是 `tsmc28`。

### `check`

检查拼版几何是否合法：

```bash
autompw check
autompw check some_config.yaml
```

检查内容：

- 每个子设计 bbox 必须在 MPW bbox 内
- 子设计之间不能重叠
- 子设计之间 spacing 必须不小于 `spacing.design_to_design_um`
- 每个子设计 GDS 文件必须存在，且 `topcell` 可读取
- 如果 `replace_with_placeholder: true`，原始子设计 GDS 不存在或不可读只报 warning
- 子设计 GDS 的 bbox 左下角和尺寸会和 `bottom_left` / `size_um` 对比，不一致时报 warning
- 每个 enabled Calibre flow 的 deck 模板必须存在，并检查是否包含可自动替换的 header 字段
- 默认会试运行 `calibre -version`，确认 `shell`、`setup_script` 和 Calibre 命令可以启动

不会检查子设计到 MPW 边界的划片距离。子设计可以紧贴 MPW 边界，只要没有超出 MPW bbox。

如果当前机器没有 Calibre，或只想做静态检查，可以跳过 Calibre 启动探测：

```bash
autompw check --no-probe-calibre
```

`check` 会打印 error 和 warning；只有 error 会导致命令返回失败。

### `framework`

生成 framework GDS：

```bash
autompw framework
```

framework GDS 包含：

- MPW 全尺寸 marker rectangle
- 每个子设计的 marker rectangle
- 每个子设计的 dummy blocker 外扩层
- 每个子设计的 edge fill ring

dummy blocker 和 edge fill ring 都会被 clip 到 MPW bbox 内。

### `dummy-fill`

为 MPW 级 dummy fill 渲染 Calibre deck，并在非 `--dry-run` 模式下调用 Calibre：

```bash
autompw dummy-fill --dry-run
autompw dummy-fill
```

MPW dummy fill 的运行期信息由程序自动生成：

- 输入 GDS：`output.framework_gds`
- 输入 topcell：`gds.topcell` 或 `mpw.name`
- chip window：MPW 尺寸
- 输出 GDS：由 topcell、flow 名和 `output_suffix` 组合生成

### `placeholders`

为每个子设计生成 blank placeholder GDS，然后渲染独立 Calibre deck，并在非 `--dry-run` 模式下调用 Calibre 往 placeholder 中填充 dummy：

```bash
autompw placeholders --dry-run
autompw placeholders
```

blank placeholder GDS 只包含 marker 层，不包含 dummy blocker 层或 edge fill 层。真实运行后，AutoMPW 会把 marker GDS、metal dummy GDS 和 ODPO dummy GDS 合并成 `output/placeholders/<design_name>_placeholder.gds`。

每个 placeholder 的运行期信息由程序自动生成：

- 输入 GDS：该子设计生成的 blank placeholder GDS
- 输入 topcell：`PLACEHOLDER_<design_name>`
- chip window：该子设计尺寸
- 中间输出 GDS：写入 `work/placeholders/<design_name>/<flow>/`
- 最终 placeholder GDS：写入 `output/placeholders/<design_name>_placeholder.gds`

### `assemble`

拼合最终 MPW GDS：

```bash
autompw assemble
```

同时会在最终 GDS 旁边生成 placement manifest。

### `all`

完整流程：

```text
check -> framework -> dummy-fill -> placeholders -> assemble
```

```bash
autompw all
```

dry-run Calibre：

```bash
autompw all --dry-run-calibre
```

### `inspect-gds`

查看 GDS 信息：

```bash
autompw inspect-gds MPW_2512.gds
```

输出包含 DBU、topcell、bbox 和 layer/datatype 列表。

## 配置文件

主输入是 YAML 文件。不指定配置文件时，各流程命令默认读取当前目录的 `./mpw_config.yaml`。推荐通过 `autompw init <process>` 生成初始配置。

### MPW

```yaml
mpw:
  name: MPW
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

```yaml
calibre:
  executable: calibre
  shell: csh
  setup_script: /edamgr/setup_calibre.csh
  args: "-drc -hier -turbo 32 -turbo_all -hyper connect"
  work_dir: ./work
  flows:
    metal:
      enabled: true
      deck_template: ./deck/dmfill_metal
      output_suffix: _DM
      summary_name: DM.sum
    odpo:
      enabled: true
      deck_template: ./deck/dmfill_odpo
      output_suffix: _DODPO
      summary_name: DODPO.sum
```

说明：

- `calibre` 是全局配置，MPW dummy fill 和 placeholder fill 都复用它
- `deck_template` 是相对 YAML 文件所在目录解析的路径
- `init tsmc28` 会把工艺 deck 模板复制到当前目录的 `./deck/`
- YAML 中不配置每次运行的输入 GDS、输出 GDS、topcell 和 chip window，这些由当前任务自动派生

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

- `marker` 用于 MPW 全尺寸 marker、子设计 marker 和 placeholder blank GDS
- `dummy_blocker.layers` 只用于 framework GDS
- 每个 dummy blocker 层可以单独设置外扩尺寸
- `edge_fill` 只用于 framework GDS
- placeholder blank GDS 不写入 dummy blocker 或 edge fill 层

### GDS

```yaml
gds:
  topcell: MPW
  dbu_um: 0.001
  flatten_final: false
  preserve_child_cells: true
  allow_cell_rename: true
```

当前实现要求参与拼合的 GDS 使用一致的 DBU。

### output

```yaml
output:
  output_dir: ./output
  framework_gds: framework.gds
  final_gds: mpw.gds
```

`output_dir` 是最终输出目录。`framework_gds` 和 `final_gds` 只需要配置文件名，程序会自动放到 `output_dir` 下。MPW dummy fill 输出固定放到 `output/dummy/dummy_<flow>.gds`，placeholder 输出固定放到 `output/placeholders/<design_name>_placeholder.gds`。

### designs

```yaml
designs:
  - name: design1
    gds: ./input/design1.gds
    topcell: DESIGN1
    size_um: [1000, 1000]
    coord: [0, 0]
    anchor: bottom_left
    bottom_left: [0, 0]
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

`replace_with_placeholder`：

- `false`：最终拼合时使用原始子设计 GDS
- `true`：最终拼合时使用该子设计对应的 placeholder GDS

`bottom_left` 是该子设计 GDS 内实际芯片区域的左下角坐标，单位为 um，默认 `[0, 0]`。assemble 时程序会把这个点对齐到 framework 为该子设计预留的 bbox 左下角。这样即使原始 GDS 的实际芯片不在本地原点，也可以正确落到 MPW 预留位置。

## Calibre deck 渲染机制

AutoMPW 不会原地修改 `deck_template`。每次运行时，程序会读取模板，替换运行期字段，并把 rendered deck、log 和中间 GDS 写到 `work/` 相关目录。

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

## Linux 测试流程

完整测试方案见 [doc/test_plan.md](doc/test_plan.md)。

常用测试命令：

```bash
pytest -q
autompw --help
./bin/autompw --help

mkdir -p /tmp/autompw_test
cd /tmp/autompw_test
autompw init tsmc28
autompw check
autompw framework
autompw dummy-fill --dry-run
autompw placeholders --dry-run
```

当前单元测试预期：

```text
16 passed
```

真实运行 Calibre 前，确认：

- `calibre` 在 PATH 中
- `csh` 已安装
- `calibre.setup_script` 存在
- YAML 中的 deck 路径指向正确模板
- 子设计 GDS 路径和 topcell 正确

## 开发

```bash
pytest -q
git status --short
```

`.gitignore` 已忽略常见生成文件，包括 `build/`、`output/`、`work/`、Python cache、Calibre log/report、本地 `input/` 目录。
