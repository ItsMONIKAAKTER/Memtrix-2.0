# Play and presentation guide

1. Install the dependency and run root `main.py`, or use the startup script.
2. Optionally create a profile. Its settings, history and legacy scores stay separate.
3. Choose a mode. Classic follows the shown order, Reverse inverts it, Pattern Recall remembers locations, Time Attack uses a session clock, and Practice offers flexible settings/hints.
4. Wait through the countdown and Preview. Input begins only when the screen says Your turn / Recall.
5. Select tiles with left click, or Tab/Enter. Repeated selections are ignored. Wrong order/location gets immediate feedback.
6. Pause with ESC. Playback and deadlines freeze; resume continues from the same position. End session & save retains an early result.
7. Review results and open Progress for history, accuracy trends, bests and achievements.
8. Export CSV if needed. The data folder is displayed in How to play.

## Suggested final-project demonstration

- Show the original v1 source/reports and the README's comparison table.
- Start a sequence; pause in the middle of playback and demonstrate that it resumes without skipping a tile.
- Deliberately choose a correct location in the wrong order and explain immediate rule-aware feedback.
- Demonstrate unordered Pattern Recall and reversed input in Reverse Sequence.
- Open Practice, choose an eight-by-eight grid and a longer sequence, then use Replay hint. Explain why assisted Practice is not ranked.
- End/save a run, show statistics and export CSV. Import the original high-score JSON and show it only in Legacy v1.
- Explain the pure Python Session model, active-time phases, capped progression and atomic save/recovery design.

The archived reports retain their original v1 scope. Current architecture, rules, scoring and limitations belong to the v2 README/guides. Memory-game results are not clinical measurements or a guarantee of broad cognitive improvement.
