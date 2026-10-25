import pygame
import asyncio
import platform
import time
from settings import (
    WIDTH, HEIGHT, FONTSIZE, TIMER, FPS, DIFFICULTY_LEVELS, CURRENT_DIFFICULTY,
    BG_COLOR1, BG_COLOR2, BUTTON_COLOR, BUTTON_HOVER_COLOR, NEON_GREEN, WHITE, SHOWTIME
)
from screens import DifficultyScreen, PlayingScreen, GameOverScreen, LeaderboardScreen, PauseScreen

class MemtrixGame:
    def __init__(self):
        pygame.init()
        self.clock = pygame.time.Clock()
        self.win = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption('Memtrix')

        # Fonts
        self.normal_font = pygame.font.SysFont('arial', FONTSIZE, bold=True)
        self.big_font = pygame.font.SysFont('arial', FONTSIZE + 40, bold=True)
        self.button_font = pygame.font.SysFont('arial', FONTSIZE - 5)

        # Game state
        self.state = 'difficulty'
        self.timestamp = {'past': 0, 'now': 0, 'timer': TIMER * DIFFICULTY_LEVELS[CURRENT_DIFFICULTY]['timer_modifier']}
        self.timer_up = False
        self.level = DIFFICULTY_LEVELS[CURRENT_DIFFICULTY]['initial_level']
        self.tile_size = 100
        self.new_pattern = []
        self.input_pattern = []
        self.score = 0
        self.high_scores = {'easy': 0, 'medium': 0, 'hard': 0}
        self.difficulty = CURRENT_DIFFICULTY
        self.running = True
        self.waiting_input = False
        self.tile_animations = {}
        self.bg_offset = 0
        self.last_click = 0
        self.fade_alpha = 0
        self.pattern_index = 0

        # Timing variables
        self.tile_show_interval = 0.8  # Balanced for slower tile display
        self.memorize_time = SHOWTIME * 0.75 / 1000
        self.next_tile_time = 0
        self.pattern_show_end_time = 0
        self.showing_pattern = False
        self.level_transition_time = 0
        self.show_level_message = False

        # Buttons
        self.buttons = {
            'easy': pygame.Rect(WIDTH//2 - 120, 180, 240, 60),
            'medium': pygame.Rect(WIDTH//2 - 120, 260, 240, 60),
            'hard': pygame.Rect(WIDTH//2 - 120, 340, 240, 60),
            'start': pygame.Rect(WIDTH//2 - 120, 420, 240, 60),
            'restart': pygame.Rect(WIDTH//2 - 150, 320, 300, 70),
            'leaderboard': pygame.Rect(WIDTH//2 - 150, 400, 300, 70),
            'quit': pygame.Rect(WIDTH//2 - 120, HEIGHT//2 + 140, 240, 60),
            'back_to_menu': pygame.Rect(WIDTH//2 - 150, HEIGHT//2, 300, 70)
        }

        # Screen instances
        self.screens = {
            'difficulty': DifficultyScreen(self),
            'playing': PlayingScreen(self),
            'gameover': GameOverScreen(self),
            'leaderboard': LeaderboardScreen(self),
            'paused': PauseScreen(self)
        }
        self.current_screen = self.screens[self.state]

    def getLeftTop(self, row, col):
        board_size = self.tile_size * self.level
        left = (self.tile_size * col) + (WIDTH - board_size) // 2
        top = (self.tile_size * row) + (HEIGHT - board_size) // 2
        return left, top

    def getClickedTile(self, x, y):
        for row in range(self.level):
            for col in range(self.level):
                left, top = self.getLeftTop(row, col)
                area = pygame.Rect(left, top, self.tile_size, self.tile_size)
                if area.collidepoint(x, y):
                    return row, col
        return None, None

    def drawText(self, msg, x, y, color, title=False, shadow=True):
        font = self.big_font if title else self.normal_font
        if shadow:
            shadow_text = font.render(msg, True, (0, 0, 0))
            shadow_rect = shadow_text.get_rect(center=(x + 2, y + 2))
            self.win.blit(shadow_text, shadow_rect)
        text = font.render(msg, True, color)
        rect = text.get_rect(center=(x, y))
        self.win.blit(text, rect)

    def drawButton(self, text, rect, hover=False):
        color = BUTTON_HOVER_COLOR if hover else BUTTON_COLOR
        surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        for i in range(rect.height):
            alpha = int(255 * (1 - i / rect.height) ** 2)
            pygame.draw.line(surface, (*color[:3], alpha), (0, i), (rect.width, i))
        self.win.blit(surface, rect.topleft)
        pygame.draw.rect(self.win, NEON_GREEN, rect, 4, border_radius=15)
        if hover:
            pygame.draw.rect(self.win, (0, 200, 0), rect, 2, border_radius=15)
            rect = pygame.Rect(rect.left - 5, rect.top - 5, rect.width * 1.05, rect.height * 1.05)
        text_surf = self.button_font.render(text, True, WHITE)
        text_rect = text_surf.get_rect(center=rect.center)
        self.win.blit(text_surf, text_rect)

    def drawAnimatedBackground(self):
        self.bg_offset = (self.bg_offset + 1) % HEIGHT
        for y in range(HEIGHT):
            ratio = ((y + self.bg_offset) % HEIGHT) / HEIGHT
            color = (
                int(BG_COLOR1[0] * (1 - ratio) + BG_COLOR2[0] * ratio),
                int(BG_COLOR1[1] * (1 - ratio) + BG_COLOR2[1] * ratio),
                int(BG_COLOR1[2] * (1 - ratio) + BG_COLOR2[2] * ratio)
            )
            pygame.draw.line(self.win, color, (0, y), (WIDTH, y))

    def lightUp(self, row, col, color):
        left, top = self.getLeftTop(row, col)
        surface = pygame.Surface((self.tile_size - 6, self.tile_size - 6), pygame.SRCALPHA)
        pygame.draw.rect(surface, color, (0, 0, self.tile_size - 6, self.tile_size - 6), border_radius=15)
        self.win.blit(surface, (left, top))
        self.tile_animations[(row, col)] = {'scale': 1.0, 'alpha': 255, 'color': color}

    def runTimer(self):
        if self.timestamp['past']:
            self.timestamp['now'] = time.time()
            self.timestamp['timer'] -= (self.timestamp['now'] - self.timestamp['past'])
            self.timestamp['past'] = self.timestamp['now']
            if self.timestamp['timer'] <= 0:
                self.timer_up = True
                self.timestamp['past'] = 0

    def resetGame(self):
        self.timer_up = False
        self.waiting_input = False
        self.score = 0
        self.level = DIFFICULTY_LEVELS[self.difficulty]['initial_level']
        self.tile_size = 100
        self.timestamp = {'past': 0, 'now': 0, 'timer': TIMER * DIFFICULTY_LEVELS[self.difficulty]['timer_modifier']}
        self.new_pattern = []
        self.input_pattern = []
        self.tile_animations = {}
        self.fade_alpha = 0
        self.pattern_index = 0
        self.next_tile_time = 0
        self.pattern_show_end_time = 0
        self.showing_pattern = False
        self.show_level_message = False
        self.level_transition_time = 0

    async def run(self):
        last_frame_time = time.time()
        while self.running:
            current_time = time.time()
            frame_time = current_time - last_frame_time
            last_frame_time = current_time

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                else:
                    await self.current_screen.handle_event(event)

            await self.current_screen.update()
            self.current_screen.draw()
            self.current_screen = self.screens.get(self.state, self.screens['difficulty'])
            pygame.display.flip()
            self.clock.tick(FPS)
            if platform.system() == "Emscripten":
                await asyncio.sleep(1.0 / FPS)

        pygame.quit()