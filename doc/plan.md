# AutoMPW 开发计划

## 目标

AutoMPW 是一个面向 MPW 流片拼版的 Linux CLI 工具。工具读取 YAML 配置，把多个子设计 GDS 按坐标放入 MPW 版图，生成 framework GDS、dummy fill GDS、placeholder GDS，并最终拼合输出 MPW GDS。

各阶段既可以单独运行，也可以通过 `autompw all` 顺序执行完整流程。

## 技术栈

- 语言：Python 3.11+
- CLI：Typer
- 配置：YAML / PyYAML
- GDS 读写：KLayout Python API
- 外部 dummy fill：Calibre
- 测试：pytest
- 目标部署环境：Linux EDA 环境

## 项目结构

```text
autompw/
  autompw/                 Python 包
  bin/autompw              Linux CLI 入口
  templates/
    tsmc28/
      mpw_config.yaml      工艺默认配置模板
      deck/
        dmfill_metal       Calibre deck 模板
        dmfill_odpo        Calibre deck 模板
  doc/
    plan.md
    test_plan.md
  tests/
  README.md
  pyproject.toml
```

## 初始化流程

CLI 命令：

```bash
autompw init <process>
```

例如：

```bash
autompw init tsmc28
```

行为：

1. 从 AutoMPW 安装目录的 `templates/<process>/mpw_config.yaml` 复制到当前目录的 `./mpw_config.yaml`。
2. 从 AutoMPW 安装目录的 `templates/<process>/deck/` 复制到当前目录的 `./deck/`。
3. 在当前目录创建 `input/`、`output/`、`work/`。
4. 如果 `mpw_config.yaml` 或 `deck/` 已存在，拒绝覆盖。

`AUTOMPW_TEMPLATE_DIR` 可用于覆盖模板根目录，便于调试或部署私有工艺模板。

## 配置文件

除 `init` 和 `inspect-gds` 外，各命令的配置文件参数都可以省略，默认读取当前目录的 `./mpw_config.yaml`。

```bash
autompw check
autompw framework
autompw dummy-fill --dry-run
autompw placeholders --dry-run
autompw assemble
autompw all
```

也可以显式指定配置文件：

```bash
autompw check path/to/config.yaml
```

核心配置示例：

```yaml
mpw:
  name: MPW
  size_um: [3333, 2222]
  origin: [0, 0]

spacing:
  design_to_design_um: 50

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

gds:
  topcell: MPW
  dbu_um: 0.001
  flatten_final: false
  preserve_child_cells: true
  allow_cell_rename: true

output:
  build_dir: ./output
  framework_gds: ./output/framework.gds
  final_gds: ./output/mpw.gds

designs:
  - name: design1
    gds: ./input/design1.gds
    topcell: DESIGN1
    size_um: [1000, 1000]
    coord: [0, 0]
    anchor: bottom_left
    replace_with_placeholder: false
```

## 拼版检查

`autompw check` 执行以下检查：

1. 根据 `coord`、`anchor`、`size_um` 计算每个子设计的 bbox。
2. 检查每个 bbox 是否完全位于 MPW bbox 内。
3. 检查子设计之间是否重叠。
4. 检查子设计之间的间距是否不小于 `spacing.design_to_design_um`。

只检查 design-to-design spacing，不检查子设计到 MPW 边界的划片距离。子设计允许紧贴 MPW 边界，但不能越界。

支持的 anchor：

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

## Framework GDS

`autompw framework` 生成 framework GDS，内容包括：

1. 覆盖整个 MPW 尺寸的 marker rectangle。
2. 每个子设计的 marker rectangle。
3. 每个子设计对应的 dummy blocker 扩展层。
4. 每个子设计对应的 edge fill ring。

dummy blocker 每个 layer 可以单独配置 `grow_um`。dummy blocker 和 edge fill 扩展后都会 clip 到 MPW bbox 内，避免图形越过 MPW 边界。

## Calibre Deck 渲染

Calibre 是全局配置项，不绑定到某一个 dummy fill 阶段。MPW dummy fill 和 placeholder fill 都复用同一组 `calibre.flows` 配置。

YAML 中只配置：

- Calibre 可执行文件
- shell 和 setup script
- Calibre args 字符串
- work 目录
- flow 列表
- 每个 flow 的 deck 模板、输出后缀、summary 名称

以下运行期字段不在 YAML 中逐项配置，而是由当前任务自动派生：

- 输入 GDS
- 输入 topcell
- 输出 GDS
- summary report
- chip window 坐标

渲染时程序读取 `deck_template`，只替换运行期字段，并把 rendered deck 写到 work 目录。原始 deck 模板不会被原地修改，其他 foundry rule、density、layer map、fill 参数保留给用户手工维护。

MPW dummy fill 的 chip window 自动使用 MPW 尺寸。placeholder fill 的 chip window 自动使用对应子设计尺寸。

## Placeholder Flow

`autompw placeholders` 为每个子设计生成 blank placeholder GDS，并可调用 Calibre 往 placeholder 内填充 dummy。

blank placeholder GDS 只包含 marker 层：

- topcell：`PLACEHOLDER_<design_name>`
- 尺寸：对应子设计 `size_um`
- 坐标窗口：默认 `[0, 0, width, height]`
- 不写入 dummy blocker 层
- 不写入 edge fill 层

随后每个 placeholder、每个 enabled Calibre flow 都会渲染独立 deck，避免不同任务互相覆盖。

## Assemble

`autompw assemble` 拼合最终 MPW GDS：

1. 创建 MPW topcell。
2. 引入 framework GDS。
3. 引入 MPW dummy fill GDS。
4. 遍历每个子设计：
   - `replace_with_placeholder: false` 时使用原始子设计 GDS。
   - `replace_with_placeholder: true` 时使用对应 placeholder GDS。
5. 按配置坐标放置。
6. 输出最终 GDS 和 placement manifest。

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

## 测试策略

优先测试不依赖 Calibre 的核心逻辑：

1. anchor 到 bbox 的转换。
2. bbox overlap 检查。
3. design-to-design spacing 检查。
4. MPW boundary 检查。
5. YAML 配置解析和默认值。
6. `init` 工艺模板复制。
7. framework GDS 生成。
8. placeholder blank GDS 生成。
9. deck 渲染 dry-run。
10. assemble 的 cell 引用和坐标放置。

Calibre 真正执行作为 Linux EDA 环境中的 integration test，检查外部命令返回码、输出 GDS、summary report 和日志。
