# Tasks

## 1. Constructor

- [ ] 1.1 在 `record/Aloha_Learn/screenshot_processor.py` 的 `VideoScreenshotExtractor.__init__` 末尾追加 `icon_crop_size=50` 参数（在 `x_thick=6` 之后）。
- [ ] 1.2 在 `__init__` 函数体末尾追加 `self.icon_crop_size = icon_crop_size` 赋值。

## 2. PNG helper

- [ ] 2.1 在 `record/Aloha_Learn/screenshot_processor.py` 中 `_save_jpg` 之后新增 `_save_png(self, path, img)` 方法，内部先 `os.makedirs(os.path.dirname(path), exist_ok=True)` 再 `cv2.imwrite(path, img)`，返回布尔结果。

## 3. Default-click insertion

- [ ] 3.1 在 `process_actions()` 的默认点击分支（`else:` 块，行 184 起）中定位 `crop_img = self._crop_with_black_padding(draw_frame, cx_raw, cy_raw, crop_size=self.crop_size)` 所在行。
- [ ] 3.2 紧接该行之后、`# 2) Draw semi-transparent X AFTER padding ...` 注释之前，插入 icon 保存段：
  - 调用 `self._crop_with_black_padding(draw_frame, cx_raw, cy_raw, crop_size=self.icon_crop_size)` 取得 `icon_crop`。
  - 设置 `icon_fn = f"record_memory_icon_{base}_crop.png"`。
  - 设置 `icon_path = screenshots_path / "icons" / icon_fn`。
  - 调用 `self._save_png(str(icon_path), icon_crop)` 并将返回值赋给 `icon_ok`。
  - 当 `not icon_ok` 时抛出 `RuntimeError(f"Could not save icon crop for action at {timestamp}s: {act_str}")`。
- [ ] 3.3 确认未触碰 `DragStart at` 分支（行 149-180）、无坐标分支（行 181-183）、`CONFIG` / `Active Window` 跳过项（第 123 行）的现有逻辑。

## 4. JSON schema 不变性

- [ ] 4.1 复核 `process_actions()` 末尾 `ua['screenshot_full']` 与 `ua['screenshot_crop']` 赋值未变；未在 `ua` 上添加 `screenshot_icon` 等新键。
- [ ] 4.2 复核 `process_project()` 中写入 `{project}_processed_log_sc.json` 的逻辑未变。

## 5. Verification

- [ ] 5.1 运行 `python -c "from record.Aloha_Learn.screenshot_processor import VideoScreenshotExtractor; VideoScreenshotExtractor()"` 确认构造器仍可零参调用，无 `TypeError`。
- [ ] 5.2 若有样例项目可用，使用 `python -m record.Aloha_Learn.screenshot_processor <project>` 重跑流水线，确认 `screenshots/icons/record_memory_icon_*.png` 出现，且与既有 `{ts}.jpg` / `{ts}.crop.jpg` 同源（即 `{ts}` 与文件名前缀中的时间戳字符串一致）。
- [ ] 5.3 抽样打开一张生成的 icon PNG，确认尺寸为 50×50（默认情况下），图像中心贴近录制点击坐标，且不含红色 X 标记。
- [ ] 5.4 抽样一个边缘点击（如距帧边缘 < 25 像素）生成的 icon，确认仍为完整 50×50，且缺角区域为黑色。
- [ ] 5.5 运行 `openspec validate add-record-memory-icon-crop --json` 确认四个 artifact 通过校验。

## 6. Documentation

- [ ] 6.1 检查 `record/README.md` 是否枚举每点击产物；如未枚举则保持不动；如已枚举则补充 icon 一项。
- [ ] 6.2 在 `openspec/changes/add-record-memory-icon-crop/` 目录保留 `proposal.md`、`design.md`、`specs/record-click-icon-crop/spec.md`、`tasks.md` 直至本变更走完 apply + archive。