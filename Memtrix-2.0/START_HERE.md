# Start Memtrix 2.0

This is a **Python/Pygame desktop game**, not a website.

## Windows

1. Install Python 3.11 or newer.
2. Extract the ZIP completely.
3. Open the `Memtrix-2.0` folder.
4. Double-click `start_windows.bat`.
5. Select a mode and click Start training. Watch the pattern before selecting tiles.

Manual commands from the extracted folder:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

## Linux / macOS

```bash
sh start_unix.sh
```

Initial installation needs internet. Installed gameplay is offline. ESC pauses, F11 changes fullscreen, and Tab/Enter navigates controls. Practice offers an H/replay hint. End a session through the pause menu to save it.

The root `README.md` explains all rules, scoring, settings, architecture, v1/v2 changes and troubleshooting. `docs/original_v1.0` contains the original reports; `legacy/v1.0` contains the original source and old score JSON. Those archived modules are not imported by the new game.

Progress saves outside the project folder; How to play inside the game shows the exact location. Import old scores explicitly through Progress > Legacy v1. They remain separate from v2 personal bests.
