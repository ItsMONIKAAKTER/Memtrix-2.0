# Version 2.0 validation

Verified on **25 October 2026** in Linux using **Python 3.12.14**, **pygame-ce 2.5.8** and **SDL 2.32.10**. The environment has no physical display/speaker device; native game rendering/events were checked using SDL dummy drivers.

## Executed checks

| Check | Observed result |
|---|---|
| `python -m pytest -q` | **97 passed** |
| Game rules | All five modes, forward/reverse/unordered recall, immediate wrong-order response, duplicate/input-phase bounds, scoring, life limits, timeouts and assistance rules |
| Long playback | A 12-tile slow sequence displays its full set without a five-second cutoff |
| Timing | Phase/active timing matches at 30, 60, 120, 144 and 240 update rates; Time Attack clips to its duration |
| Progression | Competitive caps at 6 × 6 / 20 tiles, unique patterns and practice length clamping verified |
| Pause/focus | Preview, Recall and Feedback clocks freeze; focus loss pauses or requires countdown restart |
| Input/display | Real click-event position after resize, letterbox rejection, right-click rejection, fullscreen/windowed roundtrip and all supported Practice board bounds |
| Persistence | Profile/settings/history restart, isolation, name/limit checks, atomic-write failure, recovery copies, malformed-row handling, bounded retention and CSV formula protection |
| Legacy import | `Hard`/`hard` normalization, nonnegative integer validation, maximum retention and strict separation from v2 history/bests |
| Audio | Forced initialization failure is nonfatal; generated tones initialize on dummy audio |
| SDL smoke | Real posted menu/tile events solved all five modes; hint replay, pause/resume, restart, profiles, daily completion, progress tabs, legacy import, CSV export and queued-quit public run loop passed |
| Rendered screens | Dashboard, settings, board preview/recall/feedback, pause, results, profiles, history, bests, achievements and legacy area rendered; main layouts visually reviewed |
| Launcher | `python main.py --help` succeeded |
| Packaging | A 2.0.0 wheel built successfully; source ZIP excludes the old environment, player saves, caches and temporary outputs |
| Preservation | Five original Python modules, original score JSON and both original PDFs preserved byte for byte |

The original report/play guide are archived unchanged and retain their original v1 scope. The game does not import those old source modules. The documentation screenshots show local test sessions; those test progress files are not distributed as player history.

## Scoped renderer measurement

The smoke script measured **300 frames after 60 warm-up frames**, with an **8 × 8 Practice board**, a **1440 × 900 logical canvas** and **1000 × 800 window**. The observed CPU update/drawing/scaling/display-call durations were:

- Median: **2.861 ms**.
- p95: **4.373 ms**.

This used SDL's dummy video backend and excludes frame-cap sleeping. It does not measure physical-display FPS, input-to-display latency or performance improvement relative to v1.0. Actual desktop results depend on the machine, window size, fonts, compositor and driver. Repeating the method can produce different timing numbers.

## Reproduce

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python tools/smoke_check.py --screenshots ./qa-screens --report ./qa-result.json
```

The smoke check uses temporary profile data and does not alter normal player saves. CI is configured for Windows/Linux and Python 3.11–3.13, but was not observed running in the user's GitHub repository during this delivery.

## Environment limits

Physical Windows/macOS play, actual speakers, high-DPI scaling, physical mouse latency and physical fullscreen transitions were not tested here. The Windows batch launcher was not executed on Windows. Check the intended presentation computer before demonstrating.

The game is not a clinical assessment, online platform, anti-cheat system or packaged executable. Local profiles are editable and not password-protected. Run one instance per save directory. Headless tests validate defined behavior, not the absence of every possible defect.
