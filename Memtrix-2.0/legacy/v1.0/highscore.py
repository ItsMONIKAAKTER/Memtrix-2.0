import json
import os

HIGH_SCORE_FILE = 'highscores.json'

def load_high_scores():
    if os.path.exists(HIGH_SCORE_FILE):
        try:
            with open(HIGH_SCORE_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_high_scores(high_scores):
    with open(HIGH_SCORE_FILE, 'w') as f:
        json.dump(high_scores, f, indent=4)