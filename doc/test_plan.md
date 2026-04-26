# Linux 测试方案

本文档用于项目迁移到 Linux 环境后，按从基础功能到 Calibre 集成的顺序验证 AutoMPW。

## 1. 安装依赖

在项目根目录执行：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install pytest
```

确认 CLI 可用：

```bash
autompw --help
./bin/autompw --help
```

## 2. 初始化工作目录

在一个新的工作目录中初始化工艺模板：

```bash
mkdir -p /tmp/autompw_init_test
cd /tmp/autompw_init_test
autompw init tsmc28
```

确认生成：

```bash
test -f mpw_config.yaml
test -d deck
test -f deck/dmfill_metal
test -f deck/dmfill_odpo
test -d input
test -d output
test -d work
```

## 3. 跑单元测试

回到项目根目录：

```bash
cd /path/to/autompw
pytest -q
```

预期结果：

```text
16 passed
```

## 4. 检查参考 GDS

```bash
autompw inspect-gds MPW_2512.gds
```

重点确认：

- `dbu_um` 为 `0.001`
- topcell 为 `MPW_2512`
- bbox 为 `[0, 0, 3333, 2222]`

## 5. 检查初始化后的配置

进入初始化后的工作目录：

```bash
cd /tmp/autompw_init_test
autompw check
```

不指定配置文件时，默认读取当前目录的 `./mpw_config.yaml`。

## 6. 生成 framework GDS

```bash
autompw framework
```

预期生成：

```text
output/framework.gds
```

检查输出 GDS：

```bash
autompw inspect-gds output/framework.gds
```

重点确认：

- topcell 与 `mpw_config.yaml` 中的 `gds.topcell` 一致
- 包含 marker 层 `0/0`
- 包含 dummy blocker 层
- 包含 edge fill 层

## 7. dry-run Calibre deck 渲染

先不真正运行 Calibre，只检查 deck 自动替换是否正确：

```bash
autompw dummy-fill --dry-run
```

检查 metal deck：

```bash
grep -E 'LAYOUT PATH|LAYOUT PRIMARY|RESULTS DATABASE|SUMMARY REPORT|VARIABLE xLB|VARIABLE yLB|VARIABLE xRT|VARIABLE yRT' \
  work/dummy/metal/MPW_metal.svrf
```

检查 ODPO deck：

```bash
grep -E 'LAYOUT PATH|LAYOUT PRIMARY|DFM DEFAULTS RDB GDS FILE|SUMMARY REPORT|VARIABLE xLB|VARIABLE yLB|VARIABLE xRT|VARIABLE yRT' \
  work/dummy/odpo/MPW_odpo.svrf
```

## 8. placeholder dry-run

```bash
autompw placeholders --dry-run
```

该命令会：

- 为每个 design 生成 blank placeholder GDS
- blank placeholder GDS 只包含 marker 层
- 按每个 block 的尺寸渲染独立 deck
- 为每个 enabled flow 生成独立日志和 rendered deck
- 真实运行时合并生成 `output/placeholders/<design_name>_placeholder.gds`

## 9. 真实运行 Calibre

先确认 `mpw_config.yaml` 中的 Calibre 配置适合当前 Linux 环境：

```yaml
calibre:
  executable: calibre
  shell: csh
  setup_script: /edamgr/setup_calibre.csh
```

然后运行：

```bash
autompw dummy-fill
autompw placeholders
```

如果失败，优先检查：

- `calibre` 是否在 PATH 中
- `csh` 是否可用
- `setup_script` 是否存在
- rendered deck 中的输入 GDS、topcell、输出路径是否正确
- Calibre log 文件中的错误信息

## 10. 最终拼合

在真实子设计 GDS 和 dummy GDS 都准备好后运行：

```bash
autompw assemble
```

预期输出：

```text
output/mpw.gds
output/mpw.manifest.json
output/framework.gds
output/dummy/dummy_metal.gds
output/dummy/dummy_odpo.gds
output/placeholders/<design_name>_placeholder.gds
```

检查最终 GDS：

```bash
autompw inspect-gds output/mpw.gds
```

## 推荐验证顺序

第一轮建议只放一个小 block：

```text
init -> check -> framework -> dummy-fill --dry-run -> placeholders --dry-run
```

确认路径、topcell、尺寸窗口和输出命名都正确后，再运行真实 Calibre。

第二轮再扩展到完整 MPW：

```text
check -> framework -> dummy-fill -> placeholders -> assemble
```
