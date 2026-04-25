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
```

## 2. 跑单元测试

```bash
pytest -q
```

预期结果：

```text
9 passed
```

## 3. 检查参考 GDS

```bash
autompw inspect-gds MPW_2512.gds
```

重点确认：

- `dbu_um` 为 `0.001`。
- topcell 为 `MPW_2512`。
- bbox 为 `[0, 0, 3333, 2222]`。

## 4. 检查 YAML 拼版配置

```bash
autompw check examples/mpw_2512.yaml
```

预期结果：

```text
OK: placement check passed
```

## 5. 生成 framework GDS

```bash
autompw framework examples/mpw_2512.yaml
```

预期生成：

```text
examples/build/framework.gds
```

检查输出 GDS：

```bash
autompw inspect-gds examples/build/framework.gds
```

重点确认：

- topcell 为 `MPW_2512`。
- 包含 marker 层 `0/0`。
- 包含 dummy blocker 层，例如 `150/0`、`150/1`。
- 包含 edge fill 层，例如 `5/0`、`162/2`。

## 6. dry-run Calibre deck 渲染

先不真正运行 Calibre，只检查 deck 自动替换是否正确：

```bash
autompw dummy-fill examples/mpw_2512.yaml --dry-run
```

检查 metal deck：

```bash
grep -E 'LAYOUT PATH|LAYOUT PRIMARY|RESULTS DATABASE|SUMMARY REPORT|VARIABLE xLB|VARIABLE yLB|VARIABLE xRT|VARIABLE yRT' \
  examples/build/calibre/mpw/metal/MPW_2512_metal.svrf
```

重点确认：

- `LAYOUT PATH` 指向 `examples/build/framework.gds`。
- `LAYOUT PRIMARY "MPW_2512"`。
- `VARIABLE xLB` 为 `0`。
- `VARIABLE yLB` 为 `0`。
- `VARIABLE xRT` 为 `3333`。
- `VARIABLE yRT` 为 `2222`。

同样检查 ODPO deck：

```bash
grep -E 'LAYOUT PATH|LAYOUT PRIMARY|DFM DEFAULTS RDB GDS FILE|SUMMARY REPORT|VARIABLE xLB|VARIABLE yLB|VARIABLE xRT|VARIABLE yRT' \
  examples/build/calibre/mpw/odpo/MPW_2512_odpo.svrf
```

## 7. 真实运行 Calibre

先确认 `examples/mpw_2512.yaml` 中的 Calibre 配置适合当前 Linux 环境：

```yaml
calibre:
  executable: calibre
  shell: csh
  setup_script: /home/cshrc/.cshrc.mentor22crack
```

然后运行：

```bash
autompw dummy-fill examples/mpw_2512.yaml
```

预期生成类似文件：

```text
examples/build/calibre/mpw/metal/MPW_2512_DM.gds
examples/build/calibre/mpw/odpo/MPW_2512_DODPO.gds
```

如果失败，优先检查：

- `calibre` 是否在 PATH 中。
- `csh` 是否可用。
- `setup_script` 是否存在。
- rendered deck 中的输入 GDS、topcell、输出路径是否正确。
- Calibre log 文件中的错误信息。

## 8. placeholder dry-run

```bash
autompw placeholders examples/mpw_2512.yaml --dry-run
```

该命令会：

- 为每个 design 生成 blank placeholder GDS。
- blank placeholder GDS 只包含 marker 层，不包含 dummy blocker 或 edge fill 层。
- 按每个 block 的尺寸渲染独立 deck。
- 为每个 enabled flow 生成独立日志和 rendered deck。

注意：当前示例中的 `example_block` 是占位。真实测试前需要把 `designs[].gds` 和 `designs[].topcell` 改成 Linux 上真实存在的子设计。

## 9. 最终拼合

在真实子设计 GDS 和 dummy GDS 都准备好后运行：

```bash
autompw assemble examples/mpw_2512.yaml
```

预期输出：

```text
examples/build/mpw_final.gds
examples/build/mpw_final.manifest.json
```

检查最终 GDS：

```bash
autompw inspect-gds examples/build/mpw_final.gds
```

## 推荐验证顺序

第一轮建议只放一个小 block：

```text
check -> framework -> dummy-fill --dry-run -> placeholders --dry-run
```

确认路径、topcell、尺寸窗口和输出命名都正确后，再运行真实 Calibre。

第二轮再扩展到完整 MPW：

```text
check -> framework -> dummy-fill -> placeholders -> assemble
```
