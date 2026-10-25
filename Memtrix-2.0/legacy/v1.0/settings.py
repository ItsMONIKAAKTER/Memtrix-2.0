import pygame

# Screen Constants
WIDTH = 600
HEIGHT = 600

# Font and Gameplay constants
FONTSIZE = 30
SHOWTIME = 1000
SHRINKAGE = 9
TIMER = 60  # Base timer, adjusted by difficulty
FPS = 60  # Increased for smoother animations

# Difficulty settings
DIFFICULTY_LEVELS = {
    'easy': {'initial_level': 2, 'timer_modifier': 1.5, 'max_level': 4},
    'medium': {'initial_level': 4, 'timer_modifier': 1.0, 'max_level': 8},
    'hard': {'initial_level': 5, 'timer_modifier': 0.8, 'max_level': 10}
}
CURRENT_DIFFICULTY = 'medium'  # Default difficulty

# Colors
WHITE = (255, 255, 255)
NEON_RED = (255, 50, 50)
NEON_YELLOW = (255, 255, 50)
DARK_BG = (15, 15, 30)
GREY = (100, 120, 140)
NEON_GREEN = (50, 255, 50)
BG_COLOR1 = (20, 30, 50)  # Gradient start
BG_COLOR2 = (10, 50, 70)  # Gradient end
BUTTON_COLOR = (50, 70, 90)
BUTTON_HOVER_COLOR = (70, 90, 110)
SHADOW_COLOR = (10, 10, 10)

# Initialize pygame fonts
pygame.font.init()