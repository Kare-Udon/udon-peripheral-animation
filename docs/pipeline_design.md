# 图像/动画自动处理流水线设计

## 1. 目标

本设计采用“规则流水线 + Codex 视觉回路”的方案，在本仓库内提供一套可迭代的本地工具，辅助将普通图片或动画自动转换为适合 ZMK nice!view 使用的 1-bit 资源。

目标如下：

1. 输入普通图片或动画，自动产出适合 nice!view 的伪灰度 1-bit 结果。
2. 保留足够的中间产物，方便 Codex 基于预览图做视觉分析和参数迭代。
3. 最终直接生成仓库可接入的 C 资源，尽量去掉手工网页转换环节。
4. 静态图和动画共用同一套核心处理逻辑，动画仅额外加入时序稳定步骤。

这里的“灰度”不是屏幕真灰度，而是先将画面压成有限明度层，再映射为固定黑白纹理，最终仍导出为 1-bit 图。

## 2. 范围与原则

### 2.1 范围

第一阶段聚焦：

1. 单张图片处理。
2. GIF 或视频抽帧后的动画处理。
3. 导出最终 PNG 预览。
4. 导出可接入 LVGL/ZMK 的 C 数组资源。

暂不追求：

1. 对任意输入都能一键达到最佳审美结果。
2. 复杂模型驱动的主体检测、分割或重绘。
3. 通用图像编辑器级别的交互能力。

### 2.2 原则

1. 先保证稳定、可复现，再追求“智能”。
2. 像素级处理交给确定性脚本，Codex 负责控制、对比、调参和迭代。
3. 中间结果必须可落盘、可复查、可局部重跑。
4. 动画优先保证稳定，避免纹理闪烁和档位跳变。
5. 工具默认按 stage 逐步执行，而不是强制一键跑到底。

## 3. 总体架构

建议在仓库下新增以下目录：

```text
tools/pipeline/
  main.py
  config.py
  presets.py
  models.py
  stages/
    ingest.py
    compose.py
    grayscale.py
    quantize.py
    pattern.py
    cleanup.py
    stabilize.py
    export_png.py
    export_lvgl.py
    preview.py
  patterns/
    default_2x2.json
    default_4x4.json
  jobs/
    .gitkeep
```

产物单独放在：

```text
artifacts/
  jobs/
    <job_id>/
      input/
      frames_raw/
      frames_work/
      grayscale/
      quantized/
      patterned/
      preview/
      final_png/
      lvgl/
      manifest.json
```

设计意图：

1. `tools/pipeline/` 只放实现代码。
2. `artifacts/jobs/<job_id>/` 保存一次处理任务的全部输入、中间产物和输出。
3. 任何一步结果都可以被后续复用，不必每次全量重跑。

## 4. 命令行设计

本工具应以“逐步执行”作为默认交互模型，而不是“一次性整链执行”。

设计目标如下：

1. 每个 stage 都可以独立执行。
2. 每个 stage 都有明确输入、输出和参数快照。
3. Codex 可以在任意 stage 结束后查看产物，再决定继续、修改参数重跑当前 stage，或回退到更早 stage 重跑。
4. 整链执行只作为便捷模式存在，本质上仍是多个 stage 的顺序调用。

建议第一版命令分两层：

1. job 级命令：管理任务和查看状态。
2. stage 级命令：逐步执行和重跑单个阶段。

建议主命令如下：

```bash
uv run tools/pipeline/main.py job init <input>
uv run tools/pipeline/main.py job status <job_id>
uv run tools/pipeline/main.py stage run <job_id> <stage_name>
uv run tools/pipeline/main.py stage next <job_id>
uv run tools/pipeline/main.py stage rerun <job_id> <stage_name>
uv run tools/pipeline/main.py emit-zmk <job_id>
```

如果需要保留便捷模式，可以额外提供：

```bash
uv run tools/pipeline/main.py render-static <input>
uv run tools/pipeline/main.py render-anim <input>
```

建议通用参数如下：

```bash
--preset portrait|anime|icon|photo
--size 68x140
--pattern-set default_2x2
--levels 5
--invert auto|on|off
--crop center|entropy|face
--keep-intermediate
--job <job_id>
--resume
--stop-after <stage_name>
--set key=value
```

含义如下：

1. `job init`：创建任务目录、复制输入、写入初始 `manifest.json`。
2. `job status`：展示当前任务执行到哪个 stage、哪些 stage 成功、失败或需要重跑。
3. `stage run`：显式运行某一个阶段。
4. `stage next`：运行当前任务的下一个合法 stage。
5. `stage rerun`：在保留任务上下文的前提下重跑某个阶段，并覆盖其后续失效状态。
6. `emit-zmk`：将某个任务的最终结果导出为 LVGL/ZMK 可用的 C 资源。
7. `render-static` / `render-anim`：便捷命令，内部仍按 stage 依次执行，可通过 `--stop-after` 提前停下。

推荐的 Codex 工作流：

```bash
uv run tools/pipeline/main.py job init input/demo.png
uv run tools/pipeline/main.py stage next <job_id>
uv run tools/pipeline/main.py stage next <job_id>
uv run tools/pipeline/main.py job status <job_id>
```

如果某一步结果不理想：

```bash
uv run tools/pipeline/main.py stage rerun <job_id> grayscale --set gamma=0.9
uv run tools/pipeline/main.py stage next <job_id>
```

## 5. 数据模型

建议 `manifest.json` 记录任务元信息、配置、阶段状态和产物路径，便于续跑和调试。

建议包含：

```json
{
  "job_id": "20260414-demo-001",
  "mode": "static",
  "current_stage": "quantize",
  "input": {
    "path": "input/demo.png",
    "original_size": [1024, 1024]
  },
  "target": {
    "width": 68,
    "height": 140,
    "rotated_width": 140,
    "rotated_height": 68
  },
  "preset": "anime",
  "pattern_set": "default_2x2",
  "levels": 5,
  "stage_order": [
    "ingest",
    "compose",
    "grayscale",
    "quantize",
    "pattern",
    "cleanup",
    "preview",
    "export_lvgl"
  ],
  "stages": {
    "ingest": {
      "status": "completed",
      "params": {},
      "outputs": ["input/demo.png"]
    },
    "compose": {
      "status": "completed",
      "params": {
        "crop": "center"
      },
      "outputs": ["frames_work/001_composed.png"]
    },
    "grayscale": {
      "status": "completed",
      "params": {
        "gamma": 0.92,
        "contrast": 1.15
      },
      "outputs": ["grayscale/001_gray.png"]
    },
    "quantize": {
      "status": "ready",
      "params": {
        "thresholds": [42, 96, 150, 208]
      },
      "outputs": []
    }
  },
  "stage_outputs": {
    "compose": ["frames_work/001_composed.png"],
    "grayscale": ["grayscale/001_gray.png"],
    "quantize": ["quantized/001_levels.png"],
    "pattern": ["patterned/001_bw.png"],
    "final": ["final_png/001_final.png"],
    "preview": ["preview/001_contact.png"],
    "lvgl": ["lvgl/demo.c", "lvgl/demo.h"]
  }
}
```

建议每个 stage 维护以下状态之一：

1. `pending`：尚未执行。
2. `ready`：前置阶段已完成，可以执行。
3. `completed`：已成功执行。
4. `failed`：执行失败。
5. `stale`：由于前置阶段参数变更，结果已失效，需要重跑。

其中 `stale` 很重要。只要某个 stage 被重跑，其后的所有 stage 默认都应被标记为 `stale`，避免 Codex 误用过期产物。

## 5.1 阶段化执行模型

应将 stage 视为本工具的核心抽象。

每个 stage 必须定义：

1. 阶段名。
2. 前置依赖。
3. 输入文件集合。
4. 输出文件集合。
5. 参数 schema。
6. 成功判定。
7. 失败时的错误信息。

建议抽象为：

```text
Stage
  name
  depends_on
  run(context, params) -> outputs
  validate(outputs) -> ok | error
```

好处：

1. Codex 可以精确控制执行粒度。
2. 后续加入新 stage 时不会破坏整体流程。
3. 可以自然支持 `next`、`rerun`、`resume` 和 `stop-after`。

## 5.2 续跑与重跑规则

建议采用以下规则：

1. `stage next` 只执行当前第一个 `ready` 的阶段。
2. `stage run <job_id> <stage_name>` 只有在依赖满足时才允许执行。
3. `stage rerun` 会覆盖当前阶段产物，并将后续阶段全部标记为 `stale`。
4. `job status` 必须能清楚展示：
   - 当前停在哪一步
   - 哪一步最近一次参数是什么
   - 哪些产物可直接查看
   - 哪些结果已经过期

这部分是为 Codex 的分析回路服务的，不是附属能力。

## 6. 静态图流水线

静态图建议拆成以下阶段。默认不是自动串行跑完，而是每完成一个 stage 就可以停下来检查结果。

### 6.1 ingest

职责：

1. 读取输入图片。
2. 统一格式为内部标准对象。
3. 解析尺寸、通道、透明背景信息。
4. 初始化任务目录和 `manifest.json`。

输入：

1. `png`
2. `jpg`
3. `webp`

输出：

1. 标准化后的原始输入备份
2. 任务元数据

### 6.2 compose

职责：

1. 裁切构图。
2. 缩放到目标工作尺寸。
3. 对主体做安全边距控制。

默认规则：

1. 目标尺寸固定为 `68x140`。
2. 第一版使用中心裁切。
3. 后续可增加 `entropy` 或显著性裁切。

输出：

1. `frames_work/001_composed.png`
2. 更新 `compose` stage 状态

### 6.3 grayscale

职责：

1. 将输入转换为结构清晰的灰度母版。
2. 增强主体和背景层次。

建议处理步骤：

1. luma 灰度转换。
2. 自动对比度拉伸。
3. gamma 调整。
4. 局部对比度增强。
5. 轻微锐化。

目标不是“自然灰度”，而是“结构清楚、主体可读”的灰度设计稿。

输出：

1. `grayscale/001_gray.png`
2. 更新 `grayscale` stage 状态

### 6.4 quantize

职责：

1. 将灰度图压成离散 5 档。
2. 为后续纹理映射生成标签图。

默认 5 档：

1. `0`：白
2. `1`：浅灰
3. `2`：中灰
4. `3`：深灰
5. `4`：黑

建议策略：

1. preset 提供默认阈值。
2. 可基于图像直方图做小范围自适应偏移。
3. 对轮廓、五官、文字、小图标提供黑白保护逻辑，避免全部落入抖动区域。

输出：

1. `quantized/001_levels.png`
2. 更新 `quantize` stage 状态

这一步的核心结果本质上是一个像素级 label map。

### 6.5 pattern

职责：

1. 将 5 档 label map 映射为固定黑白纹理。
2. 生成实际的 1-bit 视觉结果。

默认纹理建议：

1. 白：全白
2. 浅灰：25% 点阵
3. 中灰：50% 棋盘格
4. 深灰：75% 点阵
5. 黑：全黑

实现要求：

1. 使用规则纹理，不使用随机噪声。
2. 纹理锚点基于全局坐标。
3. 不允许不同区域各自起相位。

输出：

1. `patterned/001_bw.png`
2. 更新 `pattern` stage 状态

### 6.6 cleanup

职责：

1. 清理杂点。
2. 保护小结构和边缘。
3. 压制“花”和“脏”的局部结果。

建议处理：

1. 删除孤立单像素噪点。
2. 过滤过小连通域。
3. 细线和轮廓优先保黑。
4. 对小图标和五官区域减弱抖动。

输出：

1. `final_png/001_final.png`
2. 更新 `cleanup` stage 状态

### 6.7 preview

职责：

1. 输出方便人工和 Codex 一眼对比的联系图。

建议一张联系图包含：

1. 原图
2. 构图图
3. 灰度图
4. 5 档图
5. 纹理图
6. 最终图

输出：

1. `preview/001_contact.png`
2. 更新 `preview` stage 状态

### 6.8 export_lvgl

职责：

1. 将最终黑白 PNG 转成 LVGL/ZMK 所需的 C 资源。
2. 取代手工网页转换。

导出要求：

1. 输出尺寸为旋转后的 `140x68`。
2. 资源格式与仓库现有图片资源一致。
3. 导出 `*.c` 和 `*.h`。

输出：

1. `lvgl/<asset_name>.c`
2. `lvgl/<asset_name>.h`
3. 更新 `export_lvgl` stage 状态

## 7. 动画流水线

动画复用静态图的大部分阶段，但需要额外增加抽帧和时序稳定。

### 7.1 extract_frames

职责：

1. 从 GIF、视频或帧目录中提取原始帧。
2. 统一编号和时间顺序。

建议支持：

1. 指定 FPS。
2. 最大帧数限制。
3. 重复帧去除。

输出：

1. `frames_raw/frame_000.png ...`
2. 更新动画输入 stage 状态

### 7.2 stabilize

职责：

1. 降低动画帧间的灰度跳变。
2. 锁定纹理相位。
3. 避免伪灰面闪烁。

最重要的三项稳定约束：

1. 所有帧共享同一组 5 档阈值。
2. 所有帧共享同一个纹理模板。
3. 所有帧共享同一个全局 pattern anchor。

第一版建议做轻量实现：

1. 对相邻帧量化结果做局部多数投票。
2. 对差异很小但频繁跳档的区域做时间平滑。
3. 避免整块中灰区域因微小亮度抖动而在相邻帧切换纹理。

不建议第一版就引入复杂光流。

输出：

1. 稳定后的 `quantized` 或 `patterned` 结果
2. 更新 `stabilize` stage 状态

## 8. Preset 设计

第一版建议使用简单配置，不必一开始就引入复杂配置系统。

可以是 Python 字典，也可以是 YAML。

示例：

```yaml
name: anime
crop: center
contrast: 1.15
gamma: 0.92
sharpen: 0.2
thresholds: [42, 96, 150, 208]
pattern_set: default_2x2
cleanup:
  despeckle: 1
  min_component: 2
edge_protect: true
```

建议首批提供：

1. `portrait`
2. `anime`
3. `icon`
4. `photo`

这些 preset 不是最终答案，而是 Codex 调参时的起点。

## 9. Codex 视觉回路

本方案的关键不是完全黑盒自动化，而是让 Codex 能快速做“跑一步、看结果、改参数、再跑当前步或前一步”的闭环。

Codex 典型工作方式：

1. 初始化一个 job。
2. 执行当前 stage。
3. 查看该 stage 的产物或联系图。
4. 判断问题位于哪一阶段。
5. 调整 preset 或阶段参数。
6. 重跑当前 stage，或回退到更早 stage 重跑。
7. 结果满意后，再执行 `stage next` 进入下一步。

典型问题分类：

1. 构图不对。
2. 主体太灰或背景过重。
3. 轮廓被抖动吃掉。
4. 阴影太花。
5. 动画帧间闪烁。

因此工具必须满足：

1. 中间结果全部落盘。
2. 支持逐步执行、复跑和续跑。
3. 参数来源清晰可追踪。
4. 每个 stage 的成功/失败/过期状态明确。

## 10. ZMK 接入设计

为了降低风险，不建议第一版直接覆盖现有手写资源文件。

建议新增：

```text
boards/shields/nice_view_custom/widgets/generated_art.c
boards/shields/nice_view_custom/widgets/generated_art.h
```

接入方式：

1. 静态图：生成 `lv_img_dsc_t`，在 widget 中切换引用。
2. 动画：生成每帧 `lv_img_dsc_t` 和帧指针数组，后续接 `lv_animimg_set_src(...)`。

这样可以保留当前仓库中的手工资源，降低调试和回滚成本。

## 11. MVP 建议

第一阶段仅做以下能力：

1. 单张 PNG/JPG 输入。
2. 以 stage 为单位执行和重跑。
2. 中心裁切。
3. 灰度增强。
4. 5 档量化。
5. 2x2 规则纹理映射。
6. 自动导出最终 PNG。
7. 本地导出 LVGL C 数组。
8. 生成联系图预览。

第二阶段再增加：

1. GIF/MP4 抽帧。
2. 动画时序稳定。
3. 多 preset。
4. 生成 `generated_art.c`。
5. 在显示代码中接入 `lv_animimg`。

## 12. 风险与应对

### 12.1 输入图复杂度过高

问题：

1. 68x140 的分辨率承载不了高信息密度照片。

应对：

1. 优先约束输入风格。
2. 用 preset 和构图规则减少背景干扰。
3. 接受某些输入天然需要人工挑图，而不是无限追加算法。

### 12.2 动画闪烁

问题：

1. 伪灰度最容易在动画中出现相位跳动和大面闪烁。

应对：

1. 锁定阈值。
2. 锁定纹理模板。
3. 锁定纹理锚点。
4. 增加轻量帧间平滑。

### 12.3 自动化结果发脏

问题：

1. 规则纹理在小区域内容易让轮廓和细节发脏。

应对：

1. 增加边缘保护和小结构黑白直出逻辑。
2. 保留中间图和续跑能力，方便快速调参。

## 13. 建议实施顺序

1. 先实现静态图 MVP，优先实现 `job` / `stage` 两层命令。
2. 跑通 `输入图片 -> 分阶段产物 -> 最终 PNG -> LVGL C array`。
3. 再将生成结果接入仓库显示逻辑。
4. 最后增加动画抽帧和时序稳定模块。

## 14. 最终判断

这条流水线是可落地的，且适合在本仓库中逐步演进为一套顺手工具。

最合理的产品形态不是“万能一键图像美化器”，而是：

“一套由 Codex 驱动、由本地确定性脚本执行、能持续迭代调参并最终产出适用于 ZMK nice!view 的静态图和动画资源的自动化工具链。”
