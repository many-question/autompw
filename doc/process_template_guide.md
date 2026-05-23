# 工艺模板开发说明

本文面向后续维护 AutoMPW 的 coding agent，说明如何新增或修改工艺模板。

## init 的发现机制

`autompw init <process>` 不需要为每个工艺写专门代码。它会扫描模板根目录下的子目录：

```text
templates/<process>/
```

只要该目录包含：

```text
templates/<process>/
  mpw_config.yaml
  deck/
```

`init` 就能识别该工艺名。当前可用工艺名来自 `autompw.templates.available_processes()`。

## 新增工艺的最小操作

普通工艺新增通常只需要：

1. 创建目录：

```text
templates/<process>/
  mpw_config.yaml
  deck/
    dmfill_metal
    dmfill_odpo
```

2. 在 `mpw_config.yaml` 中配置：

- `mpw`
- `spacing`
- `calibre`
- `layers`
- `gds`
- `output`
- `designs`

3. 修改 `pyproject.toml` 的 `[tool.setuptools.data-files]`，把新模板和 deck 文件加入安装包。

否则源码树里可以用，但 `pip install .` 之后模板可能不会被安装。

4. 补测试：

- `init <process>` 能复制 `mpw_config.yaml` 和 `deck/`
- deck 能被 `check_calibre_decks()` 识别
- deck 渲染后运行期字段能被替换

## pyproject.toml 必须同步更新

如果项目最终通过 `pip install .`、虚拟环境或绿色安装方式部署，新增工艺模板时必须修改 `pyproject.toml`。原因是 `templates/` 目录不是 Python package，setuptools 不会自动把新增模板目录打进安装结果。

需要在 `[tool.setuptools.data-files]` 中加入新工艺的配置和 deck 文件，例如：

```toml
"templates/<process>" = ["templates/<process>/mpw_config.yaml"]
"templates/<process>/deck" = [
  "templates/<process>/deck/dmfill_metal",
  "templates/<process>/deck/dmfill_odpo",
]
```

如果漏掉这一步：

- 在源码仓库中直接运行可能正常。
- 安装后的 `autompw init <process>` 可能找不到该工艺。
- 或者能找到配置，但 deck 文件没有被复制。

因此新增工艺模板的提交必须同时包含：

- `templates/<process>/mpw_config.yaml`
- `templates/<process>/deck/*`
- `pyproject.toml`
- 对应测试

## deck 模板要求

AutoMPW 会在运行时自动替换以下字段。工艺 deck 中应保留这些 SVRF header 字段，或使用 `{{ ... }}` 占位符：

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

推荐写法：

```text
LAYOUT PATH "{{ input_gds }}"
LAYOUT PRIMARY "{{ input_topcell }}"
DRC RESULTS DATABASE "{{ output_gds }}" GDSII _DM
DRC SUMMARY REPORT "{{ summary_report }}"

VARIABLE xLB   {{ xLB }}
VARIABLE yLB   {{ yLB }}
VARIABLE xRT   {{ xRT }}
VARIABLE yRT   {{ yRT }}
```

不要在 YAML 中配置每次运行的输入 GDS、topcell、输出 GDS 或 chip window。这些由当前任务自动派生：

- MPW dummy fill 使用 MPW framework GDS 和 MPW 尺寸
- placeholder dummy fill 使用 placeholder blank GDS 和子设计尺寸

## layers 配置

常用字段：

```yaml
layers:
  marker: [0, 0]
  dummy_blocker:
    layers:
      - layer: [150, 1]
        grow_um: 1
  edge_fill:
    layers:
      - [55, 0]
    ring_width_um: 12
    location: inside
    include_mpw: true
```

说明：

- `marker` 用于 MPW 全尺寸 marker、子设计 marker 和 placeholder blank GDS。
- `dummy_blocker.layers` 只用于 framework GDS，每个层可单独设置 `grow_um`。
- `edge_fill.location` 支持 `outside` 和 `inside`，默认 `outside`。
- `edge_fill.include_mpw: true` 时，会给 MPW 全尺寸边界也生成 edge fill ring。
- 所有扩展或 ring 都会 clip 到 MPW bbox 内。

## 什么时候需要改代码

如果新工艺能用现有行为表达，只新增 `templates/<process>` 和 `pyproject.toml` 即可。

需要改代码的典型情况：

- framework 需要生成 seal ring cell 或特殊边界 cell。
- edge fill 不是简单 inside/outside ring。
- dummy blocker 不是 bbox grow 后 clip。
- placeholder blank GDS 不只是 marker 层。
- Calibre deck 需要替换新的运行期字段。
- assemble 需要特殊坐标或 cell-name 处理。

改代码后必须补对应单元测试。

## 从代表性 framework GDS 提取模板参数

用 KLayout Python API 读取代表性 GDS，至少确认：

- DBU
- topcell
- MPW bbox 和尺寸
- layer/datatype 列表
- 每个 layer 的 shape 数量和 bbox
- 顶层 own shape 与递归 shape 的区别
- 是否有 seal ring 子 cell

注意：AutoMPW 当前 framework 生成器不会自动复刻任意 seal ring cell。若代表性 GDS 依赖 seal ring 实例，但项目要求 framework 中也生成它，需要新增代码能力，而不只是配置模板。

## tsmc180 经验记录

`tmp/5V.gds` 分析得到：

- DBU：`0.001 um`
- topcell：`5V`
- MPW bbox：`5000 x 5000 um`
- marker 层：`0/0`
- edge fill 层：`55/0`
- edge fill 是向内 ring，宽度约 `12 um`
- edge fill 同时用于 MPW 全尺寸边界和每个子设计边界
- dummy blocker 层：
  - `150/1`
  - `150/2`
  - `150/3`
  - `150/4`
  - `150/5`
  - `150/6`
  - `150/7`
  - `150/15`
  - `150/20`
  - `150/21`
- dummy blocker 外扩约 `1 um`

`tmp/5V.gds` 还包含 `tsmc_c018_sealring_*` 子 cell。当前 tsmc180 模板没有自动生成 seal ring cell；它只配置 AutoMPW 当前支持的 marker、dummy blocker 和 edge fill 行为。

tsmc180 dummy fill deck 来自：

- `tmp/dummy_script_metal`
- `tmp/dummy_script_ODPO`

模板化后放入：

- `templates/tsmc180/deck/dmfill_metal`
- `templates/tsmc180/deck/dmfill_odpo`

并在 `templates/tsmc180/mpw_config.yaml` 中配置为 `metal` 和 `odpo` 两个 enabled flow。
