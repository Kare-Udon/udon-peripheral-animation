# Pipeline Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在本仓库实现一套按 stage 逐步执行的图像/动画处理工具，使 Codex 可以逐步查看每一步产物、决定继续还是调参重跑，并最终导出适用于 ZMK nice!view 的 LVGL 资源。

**Architecture:** 工具以 job/stage 双层模型组织。`job` 负责任务目录、状态和参数快照，`stage` 负责单步执行、校验、产物落盘和失效传播。静态图先作为 MVP 跑通，动画在同一框架上增加抽帧与稳定化阶段。

**Tech Stack:** Python 3、uv、Pillow、NumPy、pytest、标准库 argparse/json/pathlib

---

## 需求理解与边界

### 需求来源

- 规格文档：[docs/pipeline_design.md](/Users/udon/Documents/code/self/C/udon-peripheral-animation/docs/pipeline_design.md:1)
- 相关背景：[docs/animation_design.md](/Users/udon/Documents/code/self/C/udon-peripheral-animation/docs/animation_design.md:1)
- 现有接入点：
  - [boards/shields/nice_view_custom/widgets/art.c](/Users/udon/Documents/code/self/C/udon-peripheral-animation/boards/shields/nice_view_custom/widgets/art.c:1)
  - [boards/shields/nice_view_custom/widgets/peripheral_status.c](/Users/udon/Documents/code/self/C/udon-peripheral-animation/boards/shields/nice_view_custom/widgets/peripheral_status.c:110)

### 范围边界

- 第一阶段只要求静态图 MVP 跑通。
- 工具必须以 stage 为默认执行单位，不做强制一键到底。
- 每个 stage 都要有明确输入、输出、状态和参数快照。
- 所有中间产物必须落盘，方便 Codex 逐步分析。
- 最终必须能导出本地 LVGL C 数组，不依赖在线 converter。

### 完成定义（MVP）

满足以下条件视为 MVP 完成：

1. 能用 `job init` 创建任务并写入 manifest。
2. 能用 `stage next` / `stage run` / `stage rerun` 逐步执行静态图流程。
3. 能生成 `compose`、`grayscale`、`quantize`、`pattern`、`cleanup`、`preview` 的产物。
4. 能将最终结果导出为与当前仓库图片资源兼容的 LVGL C 数组。
5. 能通过 `job status` 明确看到当前阶段、阶段状态、参数快照和产物路径。

## 复杂度判断

- 复杂度等级：中
- 依据：
  - 图像处理算法本身不复杂，重点在工具形态和状态管理。
  - 真正的难点是“逐步执行 + 可复跑 + 产物可追踪 + 失效传播”。
  - 动画稳定化比静态图复杂，适合作为第二阶段。

## 外部约束与调研结论

### 关键结论

1. LVGL v8 支持 `LV_IMG_CF_INDEXED_1BIT` 等索引色格式，说明本地生成等价 C 数组是可行的。来源：LVGL Images 文档。
2. LVGL 官方常见路径是用在线 converter 生成 `lv_img_dsc_t`，但本质只是把像素和 palette 打包进 C 数组，因此可以在本地实现等价导出。来源：LVGL `lv_img` 文档。
3. Pillow 官方支持 `convert()`、`resize()` 等基础操作，足以支撑静态图 MVP 的构图、灰度和导出前处理。来源：Pillow 官方文档。

### 调研关键词

- `LVGL image indexed 1 bit`
- `LVGL image converter c array`
- `Pillow convert resize`

### 参考来源

- https://docs.lvgl.io/8.0/overview/image.html
- https://docs.lvgl.io/8/widgets/core/img.html
- https://pillow.readthedocs.io/

## 文件结构与职责

### 新增目录

- Create: `tools/pipeline/`
- Create: `tools/pipeline/stages/`
- Create: `tools/pipeline/patterns/`
- Create: `artifacts/jobs/.gitkeep`

### 核心文件

- Create: `tools/pipeline/main.py`
  - CLI 入口
  - 解析 `job` / `stage` / `emit-zmk`
- Create: `tools/pipeline/models.py`
  - 定义 job manifest、stage 状态、上下文对象
- Create: `tools/pipeline/config.py`
  - 默认尺寸、阶段顺序、路径规则
- Create: `tools/pipeline/presets.py`
  - MVP preset：`portrait`、`anime`、`icon`、`photo`
- Create: `tools/pipeline/stages/ingest.py`
  - 初始化任务、复制输入、写 manifest 初值
- Create: `tools/pipeline/stages/compose.py`
  - 中心裁切、缩放到 68x140
- Create: `tools/pipeline/stages/grayscale.py`
  - 灰度转换、对比度/gamma 调整
- Create: `tools/pipeline/stages/quantize.py`
  - 5 档量化、生成 label map
- Create: `tools/pipeline/stages/pattern.py`
  - 规则纹理映射
- Create: `tools/pipeline/stages/cleanup.py`
  - 去噪、简单边缘保护
- Create: `tools/pipeline/stages/preview.py`
  - 生成联系图
- Create: `tools/pipeline/stages/export_lvgl.py`
  - 输出 `.c` / `.h`
- Create: `tools/pipeline/patterns/default_2x2.json`
  - 默认 2x2 纹理定义
- Create: `tests/pipeline/`
  - 工具测试根目录

### 后续阶段文件

- Create: `tools/pipeline/stages/extract_frames.py`
- Create: `tools/pipeline/stages/stabilize.py`
- Create: `boards/shields/nice_view_custom/widgets/generated_art.c`
- Create: `boards/shields/nice_view_custom/widgets/generated_art.h`

## 里程碑

### 里程碑 1：任务模型与 CLI 骨架

- 目标：建立 job/stage 执行框架，哪怕暂时没有完整图像处理，也能初始化任务、记录状态并逐步调用 stage。
- 成功标准：
  - `job init` 可创建任务目录和 manifest
  - `job status` 可输出阶段状态
  - `stage run/next/rerun` 可运行占位 stage 并正确更新状态
- 测试/验收：
  - `pytest tests/pipeline/test_manifest.py -v`
  - `pytest tests/pipeline/test_cli_flow.py -v`
- 依赖/风险：
  - 风险在于 manifest 结构和状态流转一旦设计差，后续阶段会不断返工

### 里程碑 2：静态图前半段处理链

- 目标：跑通 `compose -> grayscale -> quantize`
- 成功标准：
  - 输入单张图后可逐步得到 3 份中间产物
  - 各 stage 参数可落盘和重跑
  - 上游重跑后，下游标记为 `stale`
- 测试/验收：
  - `pytest tests/pipeline/test_stage_dependencies.py -v`
  - `pytest tests/pipeline/test_static_stages_basic.py -v`
- 依赖/风险：
  - 风险在于输出文件命名、尺寸、模式不稳定，导致后续 stage 接不上

### 里程碑 3：静态图后半段处理链与预览

- 目标：跑通 `pattern -> cleanup -> preview`
- 成功标准：
  - 规则纹理映射输出可读
  - 最终 PNG 为纯黑白图
  - 联系图可用于 Codex 快速判断问题
- 测试/验收：
  - `pytest tests/pipeline/test_pattern_mapping.py -v`
  - `pytest tests/pipeline/test_preview_outputs.py -v`
- 依赖/风险：
  - 风险在于结果“太花”或联系图信息不足，影响后续调参效率

### 里程碑 4：LVGL 导出与仓库接入验证

- 目标：本地导出 `.c/.h`，验证格式可被当前仓库使用
- 成功标准：
  - 生成的 `lv_img_dsc_t` 与当前 `art.c` 风格兼容
  - 可生成独立资源文件而不覆盖现有手工资源
- 测试/验收：
  - `pytest tests/pipeline/test_export_lvgl.py -v`
  - 对生成文件做人工比对现有资源头部格式
- 依赖/风险：
  - 风险在于位打包顺序、palette 和尺寸旋转处理错误

### 里程碑 5：动画阶段扩展

- 目标：在同一框架上增加抽帧和轻量稳定化
- 成功标准：
  - 可抽帧、可逐步执行动画阶段
  - 能锁定阈值、纹理模板和纹理锚点
- 测试/验收：
  - `pytest tests/pipeline/test_extract_frames.py -v`
  - `pytest tests/pipeline/test_stabilize.py -v`
- 依赖/风险：
  - 风险在于动画闪烁控制不足，第一版只做轻量稳定化

## Checkpoints

### M1-1：定义 manifest 与 stage 状态模型

- 输入：`docs/pipeline_design.md`
- 输出：
  - `tools/pipeline/models.py`
  - `tests/pipeline/test_manifest.py`
- 验证方式：
  - manifest 能序列化/反序列化
  - stage 状态包含 `pending/ready/completed/failed/stale`

### M1-2：实现 job 初始化

- 输入：本地图片路径
- 输出：
  - `artifacts/jobs/<job_id>/`
  - `manifest.json`
- 验证方式：
  - `job init` 后目录和 manifest 存在
  - `ingest` 初始状态正确

### M1-3：实现 stage 调度与失效传播

- 输入：现有 manifest
- 输出：
  - `main.py` 调度逻辑
  - 状态更新工具函数
- 验证方式：
  - `stage next` 只运行第一个 `ready` stage
  - `stage rerun` 后下游变成 `stale`

### M2-1：实现 compose stage

- 输入：单张图片
- 输出：`frames_work/001_composed.png`
- 验证方式：
  - 输出尺寸固定 `68x140`
  - 重跑后产物覆盖，参数快照更新

### M2-2：实现 grayscale stage

- 输入：`compose` 输出
- 输出：`grayscale/001_gray.png`
- 验证方式：
  - 输出为灰度图
  - 参数如 `contrast`、`gamma` 可从 preset 和 `--set` 覆盖

### M2-3：实现 quantize stage

- 输入：`grayscale` 输出
- 输出：`quantized/001_levels.png`
- 验证方式：
  - 输出只包含 5 个离散等级
  - 可记录 thresholds 参数

### M3-1：实现 pattern stage

- 输入：label map
- 输出：`patterned/001_bw.png`
- 验证方式：
  - 输出只包含黑白两值
  - 默认使用固定 2x2 纹理

### M3-2：实现 cleanup stage

- 输入：pattern 输出
- 输出：`final_png/001_final.png`
- 验证方式：
  - 孤立噪点减少
  - 结果仍保持 1-bit 黑白

### M3-3：实现 preview stage

- 输入：原图与各阶段结果
- 输出：`preview/001_contact.png`
- 验证方式：
  - 联系图包含 spec 指定的核心视图
  - 文件路径被写回 manifest

### M4-1：实现 export_lvgl stage

- 输入：`final_png/001_final.png`
- 输出：
  - `lvgl/<asset_name>.c`
  - `lvgl/<asset_name>.h`
- 验证方式：
  - 头部字段、尺寸、`data_size` 合理
  - 资源名可配置

### M4-2：验证与仓库现有资源兼容

- 输入：生成的 `.c/.h`
- 输出：兼容性结论
- 验证方式：
  - 对照 [art.c](/Users/udon/Documents/code/self/C/udon-peripheral-animation/boards/shields/nice_view_custom/widgets/art.c:19) 资源结构人工检查
  - 如必要，补一个最小集成测试或说明文档

### M5-1：实现动画抽帧

- 输入：GIF 或视频
- 输出：`frames_raw/frame_000.png ...`
- 验证方式：
  - 可限制最大帧数
  - 帧序正确

### M5-2：实现动画稳定化

- 输入：逐帧 quantize 或 pattern 结果
- 输出：稳定后的逐帧结果
- 验证方式：
  - 阈值与纹理锚点在 manifest 中显式记录
  - 相邻帧跳变明显少于未稳定版本

## 推荐执行顺序

### Task 1：搭建基础目录和测试入口

**Files:**
- Create: `tools/pipeline/__init__.py`
- Create: `tools/pipeline/stages/__init__.py`
- Create: `tests/pipeline/__init__.py`

- [ ] 创建目录与空模块，保证后续 import 路径稳定。
- [ ] 建立 `pytest` 最小可执行入口。
- [ ] 运行：`pytest tests/pipeline -q`
- [ ] 预期：测试目录可被发现，即使暂时无测试也不报路径错误。

### Task 2：实现 manifest、stage 状态与路径模型

**Files:**
- Create: `tools/pipeline/models.py`
- Create: `tools/pipeline/config.py`
- Test: `tests/pipeline/test_manifest.py`

- [ ] 先写失败测试，覆盖 manifest 读写和 stage 状态转换。
- [ ] 实现 `JobManifest`、`StageRecord`、路径辅助函数。
- [ ] 运行：`pytest tests/pipeline/test_manifest.py -v`
- [ ] 预期：manifest 序列化、状态读写通过。

### Task 3：实现 CLI 骨架与 `job init`

**Files:**
- Create: `tools/pipeline/main.py`
- Create: `tools/pipeline/stages/ingest.py`
- Test: `tests/pipeline/test_cli_flow.py`

- [ ] 写失败测试，覆盖 `job init` 创建目录与 manifest。
- [ ] 实现 CLI 参数解析和 `job init`。
- [ ] 运行：`pytest tests/pipeline/test_cli_flow.py::test_job_init -v`
- [ ] 预期：PASS，且 `artifacts/jobs/<job_id>/manifest.json` 存在。

### Task 4：实现 stage 调度、`next`、`rerun`

**Files:**
- Modify: `tools/pipeline/main.py`
- Modify: `tools/pipeline/models.py`
- Test: `tests/pipeline/test_stage_dependencies.py`

- [ ] 写失败测试，覆盖依赖检查和 `stale` 传播。
- [ ] 实现 `stage run`、`stage next`、`stage rerun`。
- [ ] 运行：`pytest tests/pipeline/test_stage_dependencies.py -v`
- [ ] 预期：PASS，且下游阶段过期逻辑正确。

### Task 5：实现 `compose`、`grayscale`、`quantize`

**Files:**
- Create: `tools/pipeline/presets.py`
- Create: `tools/pipeline/stages/compose.py`
- Create: `tools/pipeline/stages/grayscale.py`
- Create: `tools/pipeline/stages/quantize.py`
- Test: `tests/pipeline/test_static_stages_basic.py`

- [ ] 先写失败测试，检查输出存在、尺寸正确、离散等级正确。
- [ ] 实现三个 stage 和 preset 覆盖逻辑。
- [ ] 运行：`pytest tests/pipeline/test_static_stages_basic.py -v`
- [ ] 预期：PASS，可生成 3 份中间图。

### Task 6：实现 `pattern`、`cleanup`、`preview`

**Files:**
- Create: `tools/pipeline/stages/pattern.py`
- Create: `tools/pipeline/stages/cleanup.py`
- Create: `tools/pipeline/stages/preview.py`
- Create: `tools/pipeline/patterns/default_2x2.json`
- Test: `tests/pipeline/test_pattern_mapping.py`
- Test: `tests/pipeline/test_preview_outputs.py`

- [ ] 先写失败测试，覆盖黑白输出和联系图生成。
- [ ] 实现规则纹理映射、基础去噪和联系图。
- [ ] 运行：
  - `pytest tests/pipeline/test_pattern_mapping.py -v`
  - `pytest tests/pipeline/test_preview_outputs.py -v`
- [ ] 预期：PASS，可得到最终图和预览图。

### Task 7：实现 `export_lvgl`

**Files:**
- Create: `tools/pipeline/stages/export_lvgl.py`
- Test: `tests/pipeline/test_export_lvgl.py`

- [ ] 先写失败测试，覆盖头部信息、输出文件存在和基础字段。
- [ ] 实现 PNG 到 LVGL C 数组的本地导出。
- [ ] 运行：`pytest tests/pipeline/test_export_lvgl.py -v`
- [ ] 预期：PASS，可得到 `.c/.h`。

### Task 8：做一次端到端静态图试跑

**Files:**
- Modify: 视前述实现结果而定
- Test: 手工 smoke test

- [ ] 选一张样例图建立 job。
- [ ] 用 `stage next` 逐步跑完整链。
- [ ] 每一步检查产物是否符合 spec。
- [ ] 如有偏差，仅回退必要 stage 重跑，不做大范围返工。

### Task 9：动画扩展

**Files:**
- Create: `tools/pipeline/stages/extract_frames.py`
- Create: `tools/pipeline/stages/stabilize.py`
- Test: `tests/pipeline/test_extract_frames.py`
- Test: `tests/pipeline/test_stabilize.py`

- [ ] 先写失败测试，覆盖抽帧数量、顺序和稳定化输出存在。
- [ ] 实现抽帧和轻量稳定化。
- [ ] 运行：
  - `pytest tests/pipeline/test_extract_frames.py -v`
  - `pytest tests/pipeline/test_stabilize.py -v`
- [ ] 预期：PASS，动画阶段接入既有调度框架。

## 测试策略

### 单元测试

- manifest 读写
- stage 状态流转
- 依赖校验与 `stale` 传播
- preset 参数合并
- LVGL 导出头部和数据长度

### 产物测试

- `compose` 输出尺寸固定
- `grayscale` 输出为灰度图
- `quantize` 输出等级数量正确
- `pattern` / `cleanup` 输出为纯黑白
- `preview` 输出联系图存在

### 人工验收

- 用 1 到 2 张真实样例图逐步跑全流程
- 验证 Codex 是否能根据每一步产物清晰判断下一步动作
- 验证 `stage rerun` 是否真的只让必要下游失效

## 风险与应对

- manifest 结构设计不稳：
  - 应对：优先完成 M1 并用测试锁死状态机。
- 本地 LVGL 导出格式不兼容：
  - 应对：先对齐现有 `art.c` 头部结构，再补充测试。
- 图像结果发脏、难以调参：
  - 应对：保证 preview 联系图完整，优先让问题可见。
- 动画闪烁：
  - 应对：动画推迟到第二阶段，先把 stage 框架做稳。

## 提交节奏建议

- M1 完成后提交一次。
- M2 完成后提交一次。
- M3 完成后提交一次。
- M4 完成后提交一次。
- 动画扩展单独提交。

## 计划自检

### Spec 覆盖

- job/stage 双层模型：已覆盖
- 逐步执行和重跑：已覆盖
- 中间产物落盘：已覆盖
- 静态图 MVP：已覆盖
- 动画扩展：已覆盖为第二阶段
- 本地导出 LVGL：已覆盖

### 占位检查

- 无 `TODO` / `TBD`
- 无“后续再说”的空任务
- 各里程碑均包含成功标准和验证方式

### 命名一致性

- CLI 命令统一使用 `job` / `stage`
- stage 名称统一使用 `ingest`、`compose`、`grayscale`、`quantize`、`pattern`、`cleanup`、`preview`、`export_lvgl`
