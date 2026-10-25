# Changelog

## 2.0.0 — 25 October 2026

- Rebuilt the desktop game with one event loop and a pure active-time Session model.
- Fixed truncated long-sequence playback, pause-time consumption, misleading order feedback, unlimited grid growth, global click debouncing and disconnected high-score persistence.
- Added Classic Sequence, Pattern Recall, Reverse Sequence, Time Attack and configurable Practice Studio.
- Added countdown, focus-loss pause, restart/end-save flows, full feedback and capped progression.
- Added a distinctive memory-studio UI, responsive logical grid, fullscreen, tile themes, keyboard navigation, generated optional sounds and reduced decorative motion.
- Added profiles, atomic validated saves, damaged-file recovery, session history, accuracy charts, best tables, achievements and CSV export.
- Added a date-seeded daily Time Attack challenge and assistance-aware competitive bests.
- Added explicit, case-normalized legacy high-score import into a separate v1 area.
- Added model/storage/UI regression tests, an SDL event/rendering smoke check, packaging, starter scripts and CI configuration.
- Added the full version comparison README, architecture/play guides, validation record and rendered screenshots.
- Preserved the original five Python modules, score JSON, submission report and play guide without the old virtual environment.

## 1.0 — supplied coursework

- Basic ordered tile-memory game with Easy, Medium and Hard settings.
- Fixed 600 × 600 window, animated gradient, growing grid, score/timer, pause, game-over and in-memory best display.
- Separate high-score helper and JSON supplied, but not connected to the game lifecycle.
- Original source-level bugs are documented in the current README and fixed by the v2 implementation.
