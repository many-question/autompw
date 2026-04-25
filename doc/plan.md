# MPW 鎷肩増 CLI 灏忕▼搴忓紑鍙戣鍒?
## 鐩爣

寮€鍙戜竴涓敤浜?MPW 娴佺墖鎷肩増鐨?CLI 宸ュ叿銆傝宸ュ叿鎶婂涓瓙璁捐 GDS 鎸夋寚瀹氬潗鏍囨斁鍏ヤ竴涓?MPW 椤跺眰鐗堝浘涓紝鐢熸垚 framework GDS銆乨ummy fill GDS銆乸laceholder GDS锛屽苟鏈€缁堣緭鍑哄彲浜や粯娴佺墖鐨?MPW GDS銆?
宸ュ叿闇€瑕佹敮鎸佸悇姝ラ鍗曠嫭杩愯锛屼篃闇€瑕佹敮鎸佷竴閿墽琛屽畬鏁存祦绋嬨€?
## 鎶€鏈爤閫夋嫨

- 涓昏瑷€锛歅ython 3.11
- GDS 澶勭悊锛氫紭鍏堜娇鐢?`gdsfactory 9.35.0`
- 搴曞眰 GDS API锛氬繀瑕佹椂涓嬫矇鍒?`kfactory` / `klayout.db`
- CLI 妗嗘灦锛歚typer`
- 閰嶇疆鏂囦欢锛歒AML锛屼娇鐢?`pyyaml` 鎴?`ruamel.yaml`
- 鍑犱綍妫€鏌ワ細绗竴鐗堜娇鐢ㄨ嚜瀹氫箟 rectangle / bounding-box 妫€鏌?- Calibre 闆嗘垚锛氱敱鍏ㄥ眬 YAML 閰嶇疆鎻愪緵 Calibre 鎵ц鐜鍜?deck 妯℃澘锛屽叿浣撹緭鍏?杈撳嚭鐢卞悇闃舵浠诲姟鑷姩娲剧敓

閫夋嫨鐞嗙敱锛?
- 褰撳墠鐜宸叉湁 `gdsfactory 9.35.0`銆?- 鎷肩増瀵硅薄涓昏鏄煩褰㈠瓙璁捐锛岀涓€鐗堜笉闇€瑕佸鏉?polygon boolean銆?- CLI + YAML 鏇撮€傚悎鎻忚堪澶氫釜瀛愯璁°€佸眰閰嶇疆鍜?dummy flow 鍙傛暟銆?- Calibre dummy filler 涓?foundry rule deck 缁戝畾杈冨己銆俌AML 鍙厤缃?Calibre 鎵ц鐜鍜?deck 妯℃澘锛涜緭鍏?GDS銆乼opcell銆佽緭鍑?GDS銆乻ummary/report 鍜?chip window 鍧愭爣閮界敱褰撳墠闃舵浠诲姟鑷姩鐢熸垚锛涘叾浠栧伐鑹洪€夐」浠嶄繚鐣欏湪 deck 妯℃澘涓墜宸ョ淮鎶ゃ€?
## 鎺ㄨ崘椤圭洰缁撴瀯

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

褰撳墠浠撳簱涓殑 `dummy_script_metal`銆乣dummy_script_ODPO` 搴斾綔涓?Calibre deck 妯℃澘鐨勬潵婧愶紱`fill_metal`銆乣fill_ODPO` 鍙槸 Calibre 璋冪敤 wrapper锛屽悗缁彲鐢?YAML 閰嶇疆鏇夸唬锛沗MPW_2512.gds` 鍙綔涓哄弬鑰?GDS锛沗gdsfactory_basic_usage.md` 鍚庣画鍙暣鍚堣繘 README銆?
## 閰嶇疆鏂囦欢璁捐

寤鸿浣跨敤 YAML 鎻忚堪涓€娆?MPW 鎷肩増浠诲姟銆傜ず渚嬶細

```yaml
mpw:
  name: MPW_2512
  size_um: [4000, 3000]
  origin: [0, 0]

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

`anchor` 鏀寔浠ヤ笅鍊硷細

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

杩欐牱鍙互瑕嗙洊鍥涗釜瑙掋€佸洓鏉¤竟涓偣鍜屼腑蹇冪偣鍧愭爣銆?
## CLI 鍛戒护瑙勫垝

```bash
autompw check config.yaml
autompw framework config.yaml
autompw dummy-fill config.yaml
autompw placeholders config.yaml
autompw assemble config.yaml
autompw all config.yaml
autompw inspect-gds MPW_2512.gds
```

鍛戒护鑱岃矗锛?
- `check`锛氭鏌ユ嫾鐗堟柟妗堟槸鍚﹀悎娉曘€?- `framework`锛氱敓鎴?framework GDS銆?- `dummy-fill`锛氬熀浜?framework GDS 璋冪敤 dummy filler 鐢熸垚 dummy fill GDS銆?- `placeholders`锛氫负姣忎釜瀛愯璁＄敓鎴?blank placeholder GDS锛屽苟璋冪敤 dummy filler 鐢熸垚瀵瑰簲 placeholder GDS銆?- `assemble`锛氬悎骞跺瓙璁捐銆乫ramework銆乨ummy fill銆乸laceholder锛岃緭鍑烘渶缁?MPW GDS銆?- `all`锛氭寜椤哄簭鎵ц瀹屾暣娴佺▼銆?- `inspect-gds`锛氭煡鐪?GDS 鐨?topcell銆乨bu銆乥box銆佸眰鍒楄〃绛変俊鎭€?
## 姝ラ 1锛氭嫾鐗堝悎娉曟€ф鏌?
瀹炵幇 `autompw check config.yaml`銆?
妫€鏌ュ唴瀹癸細

1. 鍧愭爣閿氱偣杞崲
   - 鏍规嵁 `coord`銆乣anchor` 鍜?`size_um` 缁熶竴杞崲涓?bbox銆?   - bbox 鏍煎紡涓?`[xmin, ymin, xmax, ymax]`銆?
2. MPW 杈圭晫妫€鏌?   - 姣忎釜瀛愯璁?bbox 蹇呴』鍦?MPW bbox 鍐呫€?
3. 瀛愯璁′簰鐩镐笉閲嶅彔
   - 瀵规墍鏈夊瓙璁捐 bbox 鍋氫袱涓?overlap 妫€鏌ャ€?
4. 鍒掔墖璺濈妫€鏌?   - 榛樿 `50um`銆?   - 鍙鏌ュ瓙璁捐涔嬮棿鐨勬渶灏?spacing銆?   - 涓嶆鏌ュ瓙璁捐鍒?MPW 澶栬竟鐣岀殑鍒掔墖璺濈锛屽瓙璁捐鍏佽绱ц创 MPW 杈圭晫銆?
5. 杈撳嚭妫€鏌ユ姤鍛?   - 鎺у埗鍙版墦鍗扮畝瑕佺粨鏋溿€?   - 鍙€夎緭鍑?JSON 鎶ュ憡銆?
鍚庣画鍙互鎶?spacing 閰嶇疆鎷嗘垚锛?
```yaml
spacing:
  design_to_design_um: 50
```

## 姝ラ 2锛氱敓鎴?framework GDS

瀹炵幇 `autompw framework config.yaml`銆?
framework GDS 鍐呭锛?
1. MPW 澶栨
   - 蹇呴』鍦?marker 灞傜敓鎴愪竴涓鐩栨暣涓?MPW 灏哄鐨?rectangle銆?   - 榛樿灞傦細`0/0`銆?
2. 瀛愯璁′綅缃爣璁板眰
   - 榛樿灞傦細`0/0`銆?   - 姣忎釜瀛愯璁℃寜瀹為檯鏈夋晥灏哄鐢熸垚 rectangle銆?   - 寤鸿 cell 鍚嶏細`FW_MARK_<design_name>`銆?
3. dummy blocker 灞?   - 榛樿灞傦細`150.x`銆?   - 鐢?marker bbox 鎸夋瘡涓?blocker 灞傜嫭绔嬮厤缃殑 `grow_um` 澶栨墿鐢熸垚銆?   - 涓嶅悓 dummy blocker 灞傚彲浠ヤ娇鐢ㄤ笉鍚屽鎵╁€硷紝渚嬪 `150/0` 澶栨墿 `1um`锛宍150/1` 澶栨墿 `3um`銆?   - 澶栨墿鍚庣殑鍥惧舰蹇呴』 clip 鍒?MPW bbox 鍐咃紝閬垮厤瓒呭嚭娴佺墖杈圭晫銆?   - 閰嶇疆瑙ｆ瀽鏃跺簲鍚屾椂鏀寔鏄惧紡瀵硅薄鏍煎紡锛屽苟鍙€夊吋瀹圭畝鍗曞垪琛ㄦ牸寮忋€?
4. 杈圭紭琛ュ厖灞?   - 榛樿灞傦細`5/0`銆乣162/2`銆?   - 鍦?marker bbox 澶栧寘 `0.45um` 鐨勮竟缂?ring銆?   - 寤鸿瀹炵幇涓哄鐭╁舰鍑忓唴鐭╁舰鐨?ring polygon锛岄伩鍏嶈鐩栨暣涓瓙璁捐鍖哄煙銆?   - ring 鍥惧舰蹇呴』 clip 鍒?MPW bbox 鍐呫€?
5. GDS 鍗曚綅
   - 鍐呴儴缁熶竴浣跨敤 `um`銆?   - 鍐?GDS 鏃舵槑纭?dbu锛屼緥濡?`0.001um`銆?   - 濡傞渶涓庡弬鑰?GDS 瀵归綈锛屽簲浠?`MPW_2512.gds` 璇诲彇 dbu銆?
## 姝ラ 3锛氳皟鐢?dummy filler 鐢熸垚 dummy fill GDS

瀹炵幇 `autompw dummy-fill config.yaml`銆?
娴佺▼锛?
1. 鐢熸垚鎴栫‘璁?`framework.gds` 瀛樺湪銆?2. 灏?framework GDS 浣滀负 Calibre dummy flow 杈撳叆銆?3. 鏍规嵁鍏ㄥ眬 `calibre` 閰嶇疆缁勮杩愯鍛戒护銆?4. 鏍规嵁 deck 妯℃澘鐢熸垚鏈杩愯涓撶敤 deck銆?   - 鍘熷 `dummy_script_metal`銆乣dummy_script_ODPO` 涓嶇洿鎺ヤ慨鏀广€?   - 绋嬪簭鎶婃ā鏉挎覆鏌撳埌褰撳墠浠诲姟鐨?build 瀛愮洰褰曘€?   - 鍙浛鎹㈣繍琛屾湡瀛楁锛氳緭鍏?GDS銆乼opcell銆佽緭鍑?GDS銆乻ummary report銆佺▼搴忔牴鎹綋鍓?GDS 浠诲姟灏哄鑷姩鐢熸垚鐨?chip window 鍧愭爣銆?   - 杩欎簺杩愯鏈熷瓧娈典笉鍦?YAML 涓€愰」閰嶇疆锛岀敱 `dummy-fill` 鎴?`placeholders` 闃舵鏍规嵁浠诲姟涓婁笅鏂囪嚜鍔ㄦ淳鐢熴€?   - 鍏朵粬宸ヨ壓寮€鍏冲拰 layer / density / fill 瑙勫垯浠嶄繚鐣欏湪妯℃澘涓紝鍏佽浜哄伐淇敼銆?5. 璋冪敤 Calibre锛?   - 浣跨敤 YAML 涓殑 `calibre.executable`銆?   - 浣跨敤 YAML 涓殑 `args` 瀛楃涓诧紝渚嬪 `"-drc -hier -turbo 32 -turbo_all -hyper connect"`銆?   - 濡傞渶 `source /home/cshrc/.cshrc.mentor22crack`锛岀敱 `shell` 鍜?`setup_script` 閰嶇疆鐢熸垚 csh 鍛戒护銆?6. 鏀寔杩愯妯″紡锛?   - 鍙窇 metal dummy銆?   - 鍙窇 ODPO dummy銆?   - 涓よ€呴兘璺戙€?7. 妫€鏌ュ閮ㄥ懡浠よ繑鍥炵爜銆?8. 妫€鏌?dummy fill 杈撳嚭鏂囦欢鏄惁瀛樺湪銆?9. 淇濆瓨鏃ュ織鍒?build 鐩綍銆?
deck 妯℃澘鍖栨柟妗堬細

- 瀵?`dummy_script_metal`銆乣dummy_script_ODPO` 澶嶅埗鍑?`.tpl` 妯℃澘銆?- 鍦ㄦā鏉?header 涓妸浠ヤ笅瀛楁鏇挎崲涓哄崰浣嶇锛?
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

- metal 鍜?ODPO deck 鐨勮緭鍑鸿鍙ヤ笉鍚岋紝妯℃澘娓叉煋鍣ㄥ簲鎸?flow 鐙珛澶勭悊銆?- deck 涓殑 `input_gds`銆乣input_topcell`銆乣output_gds`銆乣summary_report`銆乣xLB/yLB/xRT/yRT` 涓嶅湪 YAML 涓厤缃紝鐢辩▼搴忔寜褰撳墠 dummy 浠诲姟鑷姩鐢熸垚銆?- 璺?MPW dummy fill 鏃讹紝chip window 浣跨敤 MPW 灏哄銆?- 璺戝瓙璁捐 placeholder 鏃讹紝chip window 浣跨敤瀵瑰簲瀛愯璁″昂瀵搞€?- 榛樿鏈湴绐楀彛涓?`[0, 0, width, height]`锛涘鏋滃悗缁渶瑕侀潪闆跺師鐐癸紝鍙敱杈撳叆 GDS bbox 鎴栦换鍔′笂涓嬫枃娲剧敓銆?- MPW dummy fill 鐨勮緭鍏?GDS 鍥哄畾鏉ヨ嚜 `output.framework_gds`锛宼opcell 鏉ヨ嚜 `gds.topcell` 鎴?`mpw.name`锛岃緭鍑?GDS 鐢变换鍔″悕銆乫low 鍚嶅拰 `output_suffix` 缁勫悎鐢熸垚銆?- 瀛愯璁?placeholder 鐨勮緭鍏?GDS 鏉ヨ嚜璇ュ瓙璁捐 blank GDS锛宼opcell 鐢?`PLACEHOLDER_<design_name>` 鐢熸垚锛岃緭鍑?GDS 鐢卞瓙璁捐鍚嶃€乫low 鍚嶅拰 `output_suffix` 缁勫悎鐢熸垚銆?- 濡傜敤鎴锋墜宸ヤ慨鏀规ā鏉夸腑鐨勫叾浠栧唴瀹癸紝绋嬪簭涓嶈鐩栬繖浜涗慨鏀广€?
## 姝ラ 4锛氱敓鎴?placeholder GDS

瀹炵幇 `autompw placeholders config.yaml`銆?
鐩爣锛?
涓烘瘡涓瓙璁捐鐢熸垚涓€涓┖鐧?placeholder GDS锛屽苟璋冪敤 dummy filler 寰€鍏朵腑濉厖 dummy銆傝繖鏍峰綋鏌愪釜瀛愯璁″瓨鍦ㄩ棶棰樻椂锛屽彲浠ョ敤 placeholder 涓存椂鏇挎崲璇ヨ璁°€?
娴佺▼锛?
1. 瀵规瘡涓瓙璁捐鍒涘缓 blank GDS銆?   - top cell 鍚嶏細`PLACEHOLDER_<design_name>`銆?   - 灏哄绛変簬璇ュ瓙璁捐 `size_um`銆?   - 鍘熺偣寤鸿涓?`(0, 0)`銆?
2. blank GDS 鍐呭锛?   - marker rectangle銆?   - 涓嶅啓鍏?dummy blocker銆乪dge fill 鎴栧叾浠栧眰銆?
3. 鎸夋瘡涓?block 鐨勪换鍔′笂涓嬫枃娓叉煋 deck 妯℃澘骞惰皟鐢?dummy filler銆?   - 杈撳叆 GDS 浣跨敤璇ュ瓙璁捐鐢熸垚鐨?blank GDS銆?   - topcell 浣跨敤 `PLACEHOLDER_<design_name>`銆?   - chip window 浣跨敤璇ュ瓙璁捐灏哄锛岄粯璁や负 `[0, 0, width, height]`銆?   - 杈撳嚭 GDS 鍚嶇敱瀛愯璁″悕銆乫low 鍚嶅拰鍏ㄥ眬 `calibre.flows.<flow>.output_suffix` 缁勫悎鐢熸垚銆?   - 姣忎釜 block銆佹瘡涓?enabled flow 閮藉簲鐢熸垚鐙珛 rendered deck 鍜岀嫭绔嬫棩蹇楋紝閬垮厤涓嶅悓浠诲姟浜掔浉瑕嗙洊銆?   - deck 妯℃澘涓殑宸ヨ壓瑙勫垯鍜屽紑鍏充粛鐢辨ā鏉挎湰韬繚鐣欙紝涓嶅湪姝ゆ楠よ嚜鍔ㄦ敼鍔ㄣ€?
4. 杈撳嚭鏂囦欢锛?
```text
build/placeholders/
  adc_top_blank.gds
  adc_top_dummy.gds
  pll_top_blank.gds
  pll_top_dummy.gds
```

## 姝ラ 5锛氭渶缁堟嫾鍚?MPW GDS

瀹炵幇 `autompw assemble config.yaml`銆?
娴佺▼锛?
1. 鍒涘缓 MPW top cell銆?2. 寮曞叆 framework GDS銆?3. 寮曞叆 dummy fill GDS銆?4. 閬嶅巻姣忎釜瀛愯璁★細
   - `replace_with_placeholder: false` 鏃跺紩鐢ㄥ師濮嬪瓙璁捐 GDS銆?   - `replace_with_placeholder: true` 鏃跺紩鐢ㄥ搴?placeholder GDS銆?5. 鎸夐厤缃腑鐨勫潗鏍囧拰 anchor 鏀剧疆銆?6. 杈撳嚭鏈€缁?`mpw_final.gds`銆?7. 鐢熸垚 placement manifest锛岃褰曟瘡涓瓙璁捐鐨勫疄闄呮斁缃?bbox 鍜屾浛鎹㈢姸鎬併€?
manifest 绀轰緥锛?
```json
{
  "adc_top": {
    "source": "./input/adc_top.gds",
    "placed_bbox_um": [100, 100, 900, 700],
    "replaced_with_dummy": false
  }
}
```

## 閰嶇疆鍙傛暟寤鸿

绗竴鐗堣嚦灏戞敮鎸侊細

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

## 娴嬭瘯璁″垝

浼樺厛娴嬭瘯涓嶄緷璧?Calibre 鐨勬牳蹇冮€昏緫锛?
1. anchor 鍒?bbox 鐨勮浆鎹€?2. bbox overlap 妫€鏌ャ€?3. spacing 妫€鏌ャ€?4. MPW boundary 妫€鏌ャ€?5. YAML 閰嶇疆瑙ｆ瀽鍜岄粯璁ゅ€笺€?6. 灏忓昂瀵?mock GDS 鐨?framework 鐢熸垚銆?7. GDS assemble 涓?cell 寮曠敤鍜屽潗鏍囨斁缃€?8. dummy external command 浣跨敤 mock script 娴嬭瘯銆?
Calibre 鐩稿叧娴嬭瘯浣滀负 integration test锛?
- 鍙湪鏈?Calibre 鐜鏃惰繍琛屻€?- 妫€鏌ュ閮ㄥ懡浠よ繑鍥炵爜銆?- 妫€鏌ヨ緭鍑?GDS 鏄惁鐢熸垚銆?- 淇濆瓨骞舵鏌ユ棩蹇椼€?
## 寮€鍙戦噷绋嬬

### 閲岀▼纰?1锛氶」鐩鏋跺拰 CLI

- 鍒涘缓 `pyproject.toml`銆?- 鍒涘缓 `autompw` Python package銆?- 瀹炵幇鍩虹 CLI銆?- 瀹炵幇 YAML 閰嶇疆鍔犺浇銆?
### 閲岀▼纰?2锛氬嚑浣曟鏌?
- 瀹炵幇 anchor 杞?bbox銆?- 瀹炵幇 overlap 妫€鏌ャ€?- 瀹炵幇 spacing 妫€鏌ャ€?- 瀹炵幇 boundary 妫€鏌ャ€?- 杈撳嚭 check report銆?
### 閲岀▼纰?3锛歠ramework GDS 鐢熸垚

- 鐢熸垚 marker 灞傘€?- 鐢熸垚 dummy blocker 灞傘€?- 鐢熸垚 edge ring 灞傘€?- 杈撳嚭 framework GDS銆?
### 閲岀▼纰?4锛欸DS 鎷煎悎

- 璇诲彇瀛愯璁?GDS銆?- 澶勭悊 topcell銆?- 鎸夊潗鏍囧紩鐢ㄥ瓙璁捐銆?- 杈撳嚭 final GDS銆?- 鐢熸垚 placement manifest銆?
### 閲岀▼纰?5锛歞ummy filler 鎺ュ叆

- 灏?Calibre 鎵ц鐜鍜?flow 妯℃澘閰嶇疆鍐呭寲鍒板叏灞€ YAML銆?- 灏?`dummy_script_metal` / `dummy_script_ODPO` 鏀归€犱负鍙覆鏌撴ā鏉裤€?- 娓叉煋鏈杩愯涓撶敤 deck锛屾寜闃舵浠诲姟鑷姩鏇挎崲杈撳叆 GDS銆乼opcell銆佽緭鍑?GDS銆乻ummary report 鍜?chip window銆?- 璋冪敤 Calibre 鎵ц娓叉煋鍚庣殑 deck銆?- 淇濆瓨鏃ュ織銆?- 妫€鏌ヨ繑鍥炵爜鍜岃緭鍑烘枃浠躲€?- 鏀寔鍙繍琛屾寚瀹?dummy flow銆?
### 閲岀▼纰?6锛歱laceholder flow

- 鐢熸垚姣忎釜瀛愯璁＄殑 blank GDS銆?- 鏍规嵁姣忎釜瀛愯璁″昂瀵稿拰 blank GDS 淇℃伅娓叉煋鐙珛 deck銆?- 璋冪敤 Calibre 鐢熸垚姣忎釜瀛愯璁＄殑 placeholder GDS銆?- 鍦?assemble 闃舵鎸夐厤缃浛鎹㈠瓙璁捐銆?
### 閲岀▼纰?7锛氭枃妗ｅ拰鏍蜂緥

- 缂栧啓 README銆?- 鎻愪緵 `examples/mpw_2512.yaml`銆?- 璁板綍甯歌閿欒鍜屾帓鏌ユ柟娉曘€?
## 鍏抽敭鎶€鏈闄?
1. Calibre deck 妯℃澘鍖栭渶瑕佺簿纭檺瀹氳嚜鍔ㄦ浛鎹㈣寖鍥?   - 绋嬪簭鍙浛鎹?header 涓殑杩愯鏈熷瓧娈碉紝杩欎簺瀛楁鏉ヨ嚜褰撳墠闃舵浠诲姟锛屼笉鏉ヨ嚜鐢ㄦ埛閫愰」閰嶇疆銆?   - foundry 瑙勫垯銆佸紑鍏炽€乴ayer map銆乨ensity 鍙傛暟绛変粛鐢辩敤鎴峰湪妯℃澘涓墜宸ョ淮鎶ゃ€?   - 娓叉煋鏃朵笉鑳界洿鎺ヨ鐩栨ā鏉挎簮鏂囦欢锛屽彧鑳借緭鍑哄埌 build 鐩綍銆?
2. 瀛愯璁?GDS topcell 閫夋嫨
   - 閮ㄥ垎 GDS 鍙兘鏈夊涓?topcell銆?   - 閰嶇疆涓渶瑕佹敮鎸佹樉寮忔寚瀹?`topcell`銆?
3. 鍧愭爣鍘熺偣绾﹀畾
   - 寤鸿 MPW 鍘熺偣鍥哄畾涓哄乏涓嬭銆?   - 鎵€鏈?report 浣跨敤鍚屼竴鍧愭爣绯汇€?
4. GDS 鍗曚綅鍜?dbu 涓嶄竴鑷?   - 鍚堝苟鍓嶆鏌ュ瓙 GDS銆乫ramework GDS 鍜?dummy GDS 鐨?dbu銆?   - 蹇呰鏃剁粺涓€杞崲銆?
5. cell name 鍐茬獊
   - 澶氫釜瀛愯璁″彲鑳藉瓨鍦ㄥ悓鍚?cell銆?   - assemble 闃舵闇€瑕佹敮鎸佽嚜鍔?rename 鎴?namespace 鍓嶇紑銆?
6. placeholder 涓庣湡瀹炲瓙璁捐鏇挎崲鐨勪竴鑷存€?   - placeholder GDS 鐨勬湰鍦板師鐐广€佸昂瀵搞€乼opcell bbox 蹇呴』涓庤鏇挎崲瀛愯璁′竴鑷淬€?
## 鎺ㄨ崘瀹炴柦椤哄簭

绗竴鐗堝厛瀹屾垚锛?
```text
check -> framework -> assemble
```

杩欐牱鍙互浼樺厛楠岃瘉鎷肩増鍑犱綍鍜屾渶缁?GDS 杈撳嚭姝ｇ‘鎬с€?
绗簩鐗堝啀瀹屾垚锛?
```text
dummy-fill -> placeholders -> replacement assemble
```

杩欐牱鍙互鎶?foundry dummy flow 鐨勪笉纭畾鎬ч殧绂诲埌鍚庣画闃舵锛岄檷浣庣涓€鐗堝紑鍙戦闄┿€?
