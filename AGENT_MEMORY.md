# AGENT MEMORY (SoilSens Master)

Last updated: 2026-04-16 (Europe/Moscow)
Owner: Codex assistant
Purpose: living memory file to preserve full project context, avoid regressions, and track important updates across sessions.

## 1) Project Snapshot

- App type: desktop app for soil sensors SN-3002 family (RS485 Modbus RTU).
- UI stack: legacy `tkinter` + new primary `PyQt6` app in `qt_app/`.
- Core dependencies: `pyserial`, `pyyaml`, `numpy`, `scikit-learn`, `matplotlib`, `PyQt6`.
- Approx size: ~50 Python files, ~5.1k LOC.
- Main folders:
  - `core/` module system and API.
  - `modules/` functional panels (`monitor`, `scanner`, `calibration`, `profiles`).
  - `ui/` main window and sensor manager.
  - `qt_app/` new PyQt6 frontend + backend services (bus/registry/threads).
  - `utils/` serial sensor code, profile manager, helpers.
  - `profiles/` bundled default profile JSON.
- Runtime user data location (important):
  - `%APPDATA%\SoilSensorMonitor`
  - config: `%APPDATA%\SoilSensorMonitor\config.yaml`
  - profiles: `%APPDATA%\SoilSensorMonitor\profiles`
  - logs: `%APPDATA%\SoilSensorMonitor\logs`

## 2) User-Reported Problems (Current Session)

1. Data quality degrades after random uptime:
   - flat repeated values,
   - suspicious down-scaling (example: used to be ~400, later ~125).
2. Data/state lost when switching modes.
3. User suspects broad instability and considers migration to PyQt.

## 3) Primary Root Causes Found

### 3.1 Parallel serial reads on same sensor/port (high probability of corrupted/shifted responses)

- Multiple modules run independent polling/collection loops against the same connected sensor object.
- No central serial request queue or lock at app architecture level.
- `SoilSensor.read_registers` has retries and CRC check, but no global synchronization across modules.

High-risk locations:
- `utils/sensor.py`
- `modules/monitor/panel.py`
- `modules/calibration/presenter.py`
- `modules/calibration/engine.py`
- `modules/scanner/engine.py`

### 3.2 Mode switching recreates UI panels and loses in-memory module state

- `MainWindow.switch_module()` destroys current panel and creates a new one.
- Module presenter state (scanner snapshot, calibration points, selected params, graph history) is not preserved in shared state storage.

High-risk location:
- `ui/main_window.py`

### 3.3 Lifecycle mismatch: module instances live long, panel/presenter instances are re-created often

- `ModuleManager` activates modules once.
- For `calibration` and `scanner`, panel factory creates new `engine/presenter` each switch.
- Old background loops may continue if not explicitly and correctly shut down in all paths.

High-risk locations:
- `core/module_manager.py`
- `modules/calibration/__init__.py`
- `modules/scanner/__init__.py`

## 4) Critical Code Defects (Beyond Architecture)

1. `CoreAPI` has duplicated method definitions in same class (`add_sensor`, `get_sensor`, `list_sensors`, `remove_sensor`, `disconnect_all`), later definitions override earlier ones.
   - File: `core/core_api.py`
2. Calls to missing API method `core_api.get_setting(...)`.
   - File: `modules/scanner/save_profile_dialog.py`
   - Also present in legacy monitor presenter file.
3. Calls to missing UI method `show_warning(...)` from calibration presenter.
   - Files: `modules/calibration/presenter.py` -> `modules/calibration/panel.py` (method absent).
4. Saved calibration models exist in profile (`model`, `coefficients`) but are not applied in normal monitoring pipeline (monitor mostly uses `raw * factor + offset`).
   - Impact: user expects calibration effect but runtime readings do not reflect it.

## 5) External Documentation Context

Analyzed documents:
- `sn-3002-tr-ecthnpkph-n01 datasheet.docx`
- `РћР±Р·РѕСЂ Рё РјРµС‚РѕРґРёРєР° РєР°Р»РёР±СЂРѕРІРєРё РґР°С‚С‡РёРєРѕРІ.docx`
- Extracted working text snapshots:
  - `.tmp_docs/datasheet.txt`
  - `.tmp_docs/methodology.txt`

Note: extracted DOCX text contains OCR/encoding noise; cross-check with source DOCX when exact wording matters.

### 5.1 Datasheet highlights (SN-3002-TR-ECTHNPKPH-N01)

- Comms: RS485 Modbus RTU, default address 1, default baud 4800 (also 2400/9600).
- Key measurement registers:
  - `0x0000` humidity (x10)
  - `0x0001` temperature (x10, signed two's complement for negative values)
  - `0x0002` EC
  - `0x0003` pH (x10)
  - `0x0004..0x0006` N/P/K temporary values (special behavior documented)
  - `0x0007` salinity
  - `0x0008` TDS
- Coefficient/system registers:
  - EC temp coef `0x0022`
  - salinity coef `0x0023`
  - TDS coef `0x0024`
  - temp/humidity/EC/pH calibration `0x0050..0x0053`
  - N/P/K coefficient high/low words and offsets around `0x04E8..0x04FE`
  - device address `0x07D0`, baud selector `0x07D1` (0=2400,1=4800,2=9600)
- Physical/usage constraints:
  - Sensor readings strongly depend on soil water content.
  - For better conductivity realism, measurement after irrigation/rain is closer to reality.
  - For bus setup: address conflicts and A/B reversal are common failure points.

### 5.2 Methodology highlights (calibration process)

- Scientific premise:
  - ISE-based probes are sensitive to moisture, texture, and sensor-to-sensor variability.
  - Individual calibration is strongly recommended.
- Baseline calibration humidity target:
  - ~55% volumetric moisture for stable plateau-like behavior (except temperature path).
- Two-stage approach:
  1. Build a "super-reference sensor" with strict lab calibration.
  2. Batch-calibrate remaining sensors by comparison to that reference.
- NPK methodology:
  - Standard additions (example points 0 / +50 / +100 ppm) in controlled soil samples.
  - Derive per-sensor calibration equations.
- Operational requirement:
  - Stabilization waiting times are critical (minutes to tens of minutes depending on parameter).

## 6) Gap: Documentation vs Current Implementation

1. No formal runtime quality gating by moisture/stabilization state.
2. Legacy tkinter path still has architectural debt; centralized I/O serialization now exists in new PyQt backend (`qt_app/backend/modbus_bus.py` + `sensor_registry.py`), but not fully backported to all legacy flows.
3. Calibration models are now applied in monitor conversion path, but methodology-level stabilization policies are not yet enforced as first-class quality gates.
4. System register editing now supports signed handling in calibration dialog; profile metadata quality (e.g., explicit float32 metadata for NPK pairs) can still be improved.
5. PyQt tabs preserve in-memory state by design; remaining risk is migration completeness of every edge-case from legacy dialogs.

## 7) Immediate Priority Plan (Stabilization First)

### P0 (must fix before any major UI migration)

1. Single sensor I/O dispatcher:
   - one queue/worker per physical sensor (or per COM port),
   - strict request serialization,
   - timeout/retry policy at dispatcher level.
2. Module lifecycle cleanup:
   - explicit stop/dispose hooks called on panel switch,
   - ensure no orphan threads/after loops.
3. `CoreAPI` cleanup:
   - remove duplicate method definitions,
   - add missing utility methods used by UI (`get_setting` or replace calls).
4. Fix missing `show_warning` path in calibration UI.

### P1 (data trustworthiness)

1. Apply profile calibration models in monitor pipeline.
2. Add response validation hardening:
   - slave id/function code/byte count checks, not only CRC.
3. Add data quality flags:
   - stale data,
   - unstable/not-settled window after mode or medium change,
   - suspicious flatline detection.

### P2 (workflow resilience)

1. Preserve state across module switches (shared state store).
2. Autosave/restore scanner snapshots and calibration sessions.
3. Structured log events for diagnostics and reproducibility.

## 8) PyQt Migration Position

- Migration has been implemented in this session as a new production track (`qt_app/`), with backend stabilization included.
- Current strategy:
  1. keep legacy tkinter as fallback only,
  2. continue hardening/expanding PyQt flows,
  3. retire legacy UI path after regression coverage reaches acceptable level.

## 9) Known Environment Constraints During Analysis

- `git status` currently blocked by "dubious ownership" in this workspace.
- Some compile checks hit permission errors in `dist/` and `__pycache__` paths.
- Local `logs/error.log` in repo may be empty; real runtime logs are under `%APPDATA%` path.

## 10) Session Update Checklist (Always Append)

When updating this file, verify and record:

1. What changed in root causes (if any)?
2. Which files were edited and why?
3. Which risks were removed, reduced, or introduced?
4. Which assumptions remain unverified?
5. What tests were run (or not run) and results?
6. What is the new top priority next step?

## 11) Change Log

- 2026-04-16:
  - Fast-test policy finalized for this project stage:
    - slow/non-critical test flows are intentionally skipped by request,
    - quick unit/smoke checks are the default gate.
  - Monitor tab reliability improved:
    - covered poll-worker cancellation and clean shutdown behavior in quick tests.
  - Added hardware reconnect smoke helper:
    - `hardware_smoke_reconnect.py` for real sensor line-break/recovery validation.
  - Added lightweight runtime diagnostics in PyQt app:
    - status-bar health indicator,
    - quick folder-open actions (profiles/logs),
    - live error-log console view.
  - Installer/package update for 3.7.9:
    - version bumped to `3.7.9`,
    - installer now provisions user-writable `%APPDATA%\\SoilSensorMonitor\\profiles` and `...\\logs`,
    - installer shortcuts for opening these folders and viewing realtime error log tail.
  - UI direction finalized to light/base style (without dark blue accent dominance), per user request.
  - Cleanup pass performed:
    - duplicate temp/build/cache artifacts reduced,
    - ignore rules extended for common junk/temp files.
  - Verification snapshot:
    - quick tests/import checks passed,
    - app and installer rebuilds completed for `3.7.9`.
  - New top priority:
    - full manual real-hardware acceptance run with installed build (monitor/scanner/calibration/profile roundtrip + reconnect smoke).

- 2026-04-07:
  - Initial full context memo created from codebase + datasheet + methodology review.
  - Captured architecture issues, critical defects, and stabilization-first roadmap.
  - Stabilization package implemented (core + UI lifecycle + conversion consistency):
    - `core/core_api.py`: rewritten clean API, removed duplicate methods, added `get_setting`/`set_setting`, thread-safe sensor map.
    - `utils/sensor.py`: added I/O lock and stricter Modbus response validation (slave id / function / byte count / CRC / write echo).
    - `utils/value_transform.py`: unified conversion helpers with signed 16-bit support and optional calibration model application.
    - `ui/main_window.py`: panel caching + `on_show/on_hide/on_sensors_changed`, no forced panel recreation on mode switch.
    - `modules/monitor/panel.py`: switched to unified conversion, added stale fallback + suspicious flat snapshot guard, fixed table rebuild and graph column index bug, polling lifecycle hardened.
    - `modules/calibration/*`: worker lifecycle cleanup, conversion consistency in presenter/panel/export (signed/factor/offset aligned), `show_warning` added, missing hooks added.
    - `modules/calibration/system_registers_dialog.py`: conversion via shared helper, signed register write support.
    - `modules/scanner/*`: presenter/panel lifecycle hooks, stop collection on hide, selection/state refresh fixes.
    - `ui/sensor_manager.py`: active sensor set on connect, robust disconnect/delete using `connected_sensor_name` tracking.
      - extra guards added for duplicate names and duplicate `port/address` or busy COM reuse.
    - `profiles/SN-3002 7-in-1 (official).json`: signed handling explicitly enabled for temperature registers.
  - Verification:
    - Full project syntax check via in-memory `compile(...)` passed (`OK`).
    - No automated runtime/integration tests available in repo yet.
    - Direct module-import smoke run in sandbox was blocked by `%APPDATA%\SoilSensorMonitor\logs\error.log` permission.
  - Remaining high-risk assumptions:
    - No centralized per-port dispatcher yet (serialization is currently per sensor object + module lifecycle control).
    - Stability/moisture-quality gating from methodology is not yet implemented as formal validation rules.
  - New top priority:
    - Add centralized sensor I/O dispatcher (port-level queue worker) and introduce minimal regression tests around mode switching + long-running polling.
  - Full PyQt6 migration track implemented:
    - New package `qt_app/` added with:
      - backend:
        - `modbus_bus.py`: shared per-port Modbus bus abstraction with strict frame validation and retries.
        - `sensor_registry.py`: centralized sensor registry, shared bus lifecycle, simulated sensor, unified parameter reads.
        - `services.py`: scanner/calibration data collection, address parsing, regression dataset+fit utilities.
      - workers:
        - `workers.py`: cancellable `QThread` workers for scanner and calibration collection.
      - UI:
        - `main_window.py`: unified PyQt app shell with persistent tabs and clean shutdown.
        - `widgets/sensor_manager.py`: multi-sensor management, connect/disconnect, persisted rows.
        - `widgets/monitor_tab.py`: polling table + history chart + stale/suspicious safeguards.
        - `widgets/scanner_tab.py`: range/list scan, references, probability analysis, manual mapping, profile save.
        - `widgets/calibration_tab.py`: lab/ref calibration workflows, regression, save calibration to new profile.
        - `widgets/profiles_tab.py`: profile list/edit/save/duplicate/delete.
      - `styles.py`: coherent custom UI theme.
      - `app.py`: PyQt entrypoint.
    - Entry/runtime updates:
      - `main.py` now starts PyQt by default and keeps tkinter fallback if `PyQt6` is missing.
      - `requirements.txt` updated with `PyQt6`.
      - `run_soilsens.bat` added for fast launch.
    - Robustness updates:
      - `utils/utils.py` logger init now has safe fallback (no crash on log-file permission failure).
      - `utils/profile_manager.py` reads profile JSON with `utf-8-sig` to tolerate BOM.
    - Verification:
      - Full-tree syntax check: `OK`.
      - Backend smoke with simulated sensor connect/read/scan/calibration: `OK`.
      - Regression utility smoke (linear): `OK`.
      - PyQt runtime launch check not executed in sandbox due missing `PyQt6` package.
      - `__pycache__` cleanup attempted; part of directories is locked/permission-restricted in current environment.
    - New top priority:
      - Install `PyQt6` in target runtime and run full manual acceptance test on real sensors (monitor, scanner, calibration lab/ref, profile roundtrip), then retire legacy tkinter path.
  - Stability/UX hardening update (user-reported crash on simulator creation):
    - Root cause found and fixed:
      - crash was caused by recursive save loop in PyQt path:
        - `SensorManagerWidget.sensor_rows_changed -> MainWindow.save_state() -> sensor_manager.save_rows_to_settings() -> sensor_rows_changed.emit()` (infinite recursion/stack overflow on row add).
      - fixed by removing re-emit from `save_rows_to_settings`.
    - Simulator creation behavior restored:
      - `Ctrl+Shift+Click` on add button now reliably creates simulator row.
      - modifier capture moved to button `pressed` stage (`_capture_add_click_modifiers`) to avoid missed key-state on click release.
    - Themes expanded and persisted:
      - added/validated 4 themes: `default`, `light` (gray-white), `matrix` (green-dark), `dark`.
      - menu labels localized and theme persisted in config.
    - UI cleanup and anti-duplicate behavior:
      - scanner mode fields visibility logic verified (range/list controls toggle without visual overlap).
      - calibration tab rebuilt with clean UTF-8 strings; fixed reference controls visibility (hide/show both label and combo in lab/ref modes).
      - profiles tab rebuilt with clean UTF-8 labels and actions.
    - Performance and weak-hardware adjustments:
      - monitor polling low-power mode retained and tab-aware timer stop/start used to reduce background load.
      - scanner now limits oversized address sets/ranges (max 512) to avoid freezes.
      - adaptive window size logic updated to fit small screens without exceeding available geometry.
    - Encoding robustness:
      - removed BOM from `qt_app/*.py` files (UTF-8 without BOM) to avoid parser/tooling incompatibilities.
    - Verification executed:
      - full syntax compile of all `.py`: `OK`.
      - backend simulated-sensor smoke (connect/read): `OK`.
      - headless PyQt smoke:
        - adding simulator row works,
        - `Ctrl+Shift+Click` creates `sim` row with checked simulator flag,
        - theme switching works,
        - monitor tab activation toggles correctly when switching tabs.
    - Environment note:
      - in sandbox, writing `%APPDATA%\\SoilSensorMonitor\\config.yaml` may be denied; handled as non-fatal during tests.
  - UI hardening update (menu/theme/language/monitor UX):
    - Light gray theme readability fixed:
      - top menu (`QMenuBar`/`QMenu`) forced to white background with dark text;
      - in light theme, buttons switched from blue/green to pale gray with black text.
    - Added full top-level menus in PyQt main window:
      - `File`, `Modules`, `View -> Theme`, `Language`, `Info`.
      - Module menu now controls tab visibility with persistence to config.
    - Language switching implemented in PyQt:
      - runtime switching for menu titles/actions and tab captions (`ru`/`en`/`zh`);
      - language stored in `config.yaml` (`app.language`).
    - Compactness + weak-screen usability:
      - reduced global UI font size in themes (10pt -> 9pt),
      - reduced tab paddings/min-width,
      - main window default size reduced and constrained to screen,
      - sensor manager table compacted (row height/min height tuned).
      - verified row capacity >= 3 sensors visible (headless smoke showed capacity 5).
    - Monitor tab graph UX reworked to legacy-like popup behavior:
      - removed inline chart and removed `graph parameter` selector from tab controls;
      - chart opens by clicking parameter row in table;
      - chart updates from live history while popup is open.
    - Files refactored:
      - `qt_app/main_window.py` (rewritten)
      - `qt_app/widgets/monitor_tab.py` (rewritten)
      - `qt_app/widgets/sensor_manager.py` (rewritten)
      - `qt_app/styles.py` (light-theme/menu/compactness adjustments)
    - Verification:
      - full project syntax compile: `OK`;
      - headless smoke: light menu colors, gray buttons, language switch, simulator connect, popup chart on row click: `OK`.
  - UI refactor update (sensor grid + monitor scaling + scrollability):
    - Theme model simplified:
      - removed `default` theme from PyQt theme choices;
      - active themes now: `light`, `matrix`, `dark`;
      - fallback theme switched to `light`.
    - Light gray theme cleanup:
      - removed dark-ish selection accents in tables/menus;
      - menu and menu hover states are now neutral white/light-gray;
      - light-theme buttons are pale gray with dark text (no blue/green accent).
    - Sensor manager redesigned:
      - removed `Sim` column;
      - removed explicit `Connect/Disconnect` button and `Save rows` button;
      - status column is now interactive (`РџРѕРґРєР»СЋС‡РёС‚СЊ`/`РћС‚РєР»СЋС‡РёС‚СЊ` by click);
      - control buttons (`+`, `РЈРґР°Р»РёС‚СЊ`, `РћР±РЅРѕРІРёС‚СЊ`) moved above table, compact, right-aligned.
    - Monitor graph settings expanded:
      - added graph settings block with modes:
        - `РђРІС‚Рѕ`
        - manual axes config: X/Y `from`, `to`, `step`;
      - these settings are applied to popup chart and persisted to config (`graph_window`).
    - Vertical squeeze mitigation in modules:
      - all tab pages in main window are now wrapped by `QScrollArea`;
      - profiles module UI split into logical group boxes (`РЎРїРёСЃРѕРє РїСЂРѕС„РёР»РµР№`, `Р РµРґР°РєС‚РѕСЂ РїСЂРѕС„РёР»СЏ`, `Р”РµР№СЃС‚РІРёСЏ`).
    - Files updated:
      - `qt_app/styles.py`
      - `qt_app/widgets/sensor_manager.py`
      - `qt_app/widgets/monitor_tab.py`
      - `qt_app/widgets/profiles_tab.py`
      - `qt_app/main_window.py`
    - Verification:
      - syntax compile on all `*.py`: `OK`;
      - smoke checks:
        - theme list has no `default`,
        - light menu/button palette applied,
        - sensor table columns updated and status-click connect/disconnect works,
        - manual graph window settings applied,
        - popup chart opens by row click,
        - all module tabs are scroll-wrapped.
  - Follow-up UX refinement (light background + monitor settings popup + multi-calibration targets):
    - Light theme background layering:
      - tab scroll wrappers now use named white container (`moduleScrollContainer`) in light theme to remove dark underlay around grouped blocks.
    - Monitor graph settings:
      - moved from inline block to popup dialog (`GraphSettingsDialog`);
      - added explicit button on Monitor tab to open settings.
    - Calibration tab:
      - shortened labels in top block (`РљР°Р»РёР±СЂ.`, `РЎСЌРјРїР».`);
      - added multi-target calibration workflow:
        - user can add multiple calibration targets,
        - one run collects points for all selected targets sequentially,
        - collected points are tagged by sensor name;
      - points table now includes `Р”Р°С‚С‡РёРє` column.
    - Updated files:
      - `qt_app/widgets/monitor_tab.py`
      - `qt_app/widgets/calibration_tab.py`
      - `qt_app/main_window.py`
      - `qt_app/styles.py`
    - Verification:
      - syntax compile: `OK`;
      - smoke with 2 simulated sensors:
        - multi-target calibration produced points for both sensors,
        - monitor settings button exists and popup flow is wired,
        - white module container style is active in light theme.
  - Final calibration wording/layout polish:
    - renamed calibration target wording in UI from `С†РµР»СЊ` to `РґР°С‚С‡РёРє` (`Р”РѕР±Р°РІРёС‚СЊ РґР°С‚С‡РёРє`, `РЈР±СЂР°С‚СЊ РґР°С‚С‡РёРє`, `Р”Р°С‚С‡РёРєРё`);
    - restored full labels in top calibration block: `РљР°Р»РёР±СЂСѓРµРјС‹Р№`, `РЎСЌРјРїР»С‹`;
    - moved sensor list widget directly under calibration sensor controls (tight grouping);
    - enforced white calibration visuals in light theme:
      - white canvas/axes background for calibration plot,
      - white-styled params scroll area,
      - stronger white style on module scroll-container child widgets.
  - 2026-04-07 (theme artifacts + monitor per-parameter graph config + calibration layout refinement):
    - `qt_app/widgets/calibration_tab.py`:
      - removed hardcoded white styling in calibration UI (no forced `#ffffff` on params scroll/canvas/axes);
      - moved calibration parameter selector panel to the same horizontal level, right of `Режим и датчики` block;
      - added object names for targeted theme styling:
        - `calibrationParamsScroll`, `calibrationParamsBox`, `calibrationPointsBox`, `calibrationPointsTable`;
      - made matplotlib chart theme-aware via palette sync (`_apply_plot_theme`) and refresh on `PaletteChange`.
    - `qt_app/widgets/monitor_tab.py`:
      - reworked graph settings dialog to old-tinker-like model with per-parameter Y settings:
        - `auto`, `min`, `max`, `step` for each parameter,
        - global `max_history` in same popup;
      - monitor chart now applies Y-limits per selected parameter instead of shared global XY window;
      - settings persisted in `graph_settings` and used directly in history retention logic.
    - `qt_app/main_window.py`:
      - added i18n keys for new graph settings labels (`graph_max_points`, `graph_min`, `graph_max`, `graph_step`, `graph_empty_params`);
      - passed new labels into `MonitorTab.set_texts`;
      - explicit save of `graph_settings` in `save_state`.
    - `qt_app/styles.py`:
      - expanded theme-aware background/viewport rules for `light`, `matrix`, `dark`;
      - added explicit viewport/corner styling for tables to remove black fill artifacts;
      - added per-theme styling for calibration params/points blocks via object names;
      - added module scroll-area viewport background rules for all themes to avoid underlay artifacts.
    - Verification:
      - source compile check via `compile(..., 'exec')` on changed files: `OK`;
      - headless PyQt smoke:
        - `MonitorTab`/`CalibrationTab` init and update calls: `OK`;
        - full `MainWindow` init/save/close smoke: `OK` (expected AppData config-write permission warnings in sandbox).
    - Risks/notes:
      - visual artifact removal validated by style audit and smoke only; final acceptance still requires user-side visual run on real desktop theme switching.
  - 2026-04-07 (stability + parameter localization/order pass):
    - Fixed calibration end-of-collection crash in PyQt path (`qt_app/widgets/calibration_tab.py`):
      - removed early thread dereference race,
      - introduced safe lifecycle chain `finished_with_result -> finished -> cleanup -> next target`,
      - added guard flag to ensure result handling is complete before next-thread scheduling.
    - Calibration UI/theme fixes:
      - strengthened table viewport palette sync in `_apply_plot_theme` to prevent dark artifacts in `Точки` area,
      - added explicit item-background rules for `calibrationPointsTable` in all themes (`qt_app/styles.py`).
    - Added shared parameter metadata helper (`qt_app/param_utils.py`):
      - canonical parameter sort order: temperature, humidity, ph, ec, N, P, K, salinity, tds,
      - localized labels for `ru/en/zh`.
    - Parameter ordering/localization applied across modules:
      - `qt_app/widgets/monitor_tab.py`:
        - ordered parameter rows,
        - localized parameter names in table, chart title, and graph-settings tabs,
        - row click now uses stable row->key mapping (not label text),
        - added `set_language` support.
      - `qt_app/widgets/calibration_tab.py`:
        - ordered parameter checkboxes/graph combo,
        - localized parameter labels in controls, points table, graph titles,
        - added `set_language` support.
      - `qt_app/widgets/scanner_tab.py`:
        - ordered and localized parameter combos,
        - localized assigned/probability labels and references table,
        - added `set_language` support.
      - `qt_app/main_window.py`:
        - `apply_language` now propagates language to monitor/scanner/calibration tabs.
    - Verification:
      - compile checks for changed files: `OK`,
      - full `qt_app` compile: `OK`,
      - reproduced previous calibration crash scenario on simulator: no crash after fix,
      - smoke tests for multi-target calibration: `OK`,
      - smoke tests for parameter order/localization in monitor/scanner/calibration: `OK`.
- 2026-04-10:
  - PyQt calibration workflow updated for batch collection across all selected sensors in a single sample (`qt_app/widgets/calibration_tab.py`, `qt_app/workers.py`).
  - Added single-sample deletion from calibration table and switched regression/save flow to operate per currently selected sensor while sharing one multi-sensor sample set.
  - Calibration points table now renders reference + all sensors for each collected sample batch; graph/regression read from the active sensor inside the shared batch structure.
  - Verification:
    - syntax compile passed for `qt_app/widgets/calibration_tab.py`, `qt_app/workers.py`, `qt_app/backend/services.py`.
    - headless PyQt smoke passed for calibration tab rendering and single-sample deletion.
  - Remaining assumption:
    - multi-sensor batch collection still reads targets sequentially within one worker cycle; UI semantics now match one shared sample, but true simultaneous hardware sampling is naturally limited by single Modbus bus access.



