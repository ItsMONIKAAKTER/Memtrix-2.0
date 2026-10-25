import pygame
import asyncio
import random
import time
import math
from settings import (
    WIDTH, HEIGHT, SHOWTIME, SHRINKAGE, TIMER, NEON_RED, NEON_GREEN, NEON_YELLOW,
    DARK_BG, GREY, DIFFICULTY_LEVELS, WHITE
)

class Screen:
    def __init__(self, game):
        self.game = game

    def draw(self):
        pass

    async def handle_event(self, event):
        pass

    async def update(self):
        pass

class DifficultyScreen(Screen):
    def draw(self):
        self.game.drawAnimatedBackground()
        self.game.drawText('Memtrix', WIDTH//2, 50, NEON_GREEN, True)
        self.game.drawText("Choose Difficulty", WIDTH//2, 120, WHITE)
        mouse_pos = pygame.mouse.get_pos()
        for diff in ['easy', 'medium', 'hard']:
            hover = self.game.buttons[diff].collidepoint(mouse_pos)
            self.game.drawButton(diff.capitalize(), self.game.buttons[diff], hover)

    async def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONUP:
            current_time = time.time()
            if (current_time - self.game.last_click) > 0.2:
                self.game.last_click = current_time
                for diff in ['easy', 'medium', 'hard']:
                    if self.game.buttons[diff].collidepoint(event.pos):
                        self.game.difficulty = diff
                        self.game.state = 'playing'
                        self.game.level = DIFFICULTY_LEVELS[self.game.difficulty]['initial_level']
                        self.game.timestamp['past'] = time.time()
                        self.game.resetGame()

class PlayingScreen(Screen):
    def __init__(self, game):
        super().__init__(game)
        self.pattern_start_time = 0

    def draw(self):
        self.game.drawAnimatedBackground()
        self.game.drawText(f'Score: {self.game.score}', 30, 20, NEON_GREEN)
        self.game.drawText(f'Level: {self.game.level - 1}', WIDTH//2 - 30, 20, NEON_GREEN)
        self.game.drawText(f'Best: {self.game.high_scores.get(self.game.difficulty, 0)}', WIDTH - 130, 20, NEON_GREEN)
        board_size = self.game.tile_size * self.game.level
        left, top = self.game.getLeftTop(0, 0)
        for row in range(self.game.level):
            for col in range(self.game.level):
                tile_left, tile_top = self.game.getLeftTop(row, col)
                size = self.game.tile_size - 6
                anim_key = (row, col)
                if anim_key in self.game.tile_animations:
                    scale = self.game.tile_animations[anim_key]['scale']
                    alpha = self.game.tile_animations[anim_key]['alpha']
                    color = self.game.tile_animations[anim_key]['color']
                    size *= 1 + 0.1 * (1 - scale)
                    offset = (self.game.tile_size - size) / 2
                    surface = pygame.Surface((size, size), pygame.SRCALPHA)
                    pygame.draw.rect(surface, (*color[:3], int(alpha)), (0, 0, size, size), border_radius=5)
                    self.game.win.blit(surface, (tile_left + offset, tile_top + offset))
                    if self.game.difficulty != 'easy':
                        self.game.tile_animations[anim_key]['scale'] -= 0.05
                        self.game.tile_animations[anim_key]['alpha'] -= 15
                        if self.game.tile_animations[anim_key]['scale'] <= 0 or self.game.tile_animations[anim_key]['alpha'] <= 0:
                            del self.game.tile_animations[anim_key]
                else:
                    surface = pygame.Surface((size, size), pygame.SRCALPHA)
                    color = GREY
                    pygame.draw.rect(surface, (*color[:3], 50), (0, 0, size, size), border_radius=5)
                    pygame.draw.rect(surface, color, (0, 0, size, size), border_radius=2)
                    self.game.win.blit(surface, (tile_left, tile_top))
        border_width = 4 + math.sin(time.time())
        pygame.draw.rect(self.game.win, NEON_RED, (left - 5, top - 5, board_size + 10, board_size + 10), int(border_width // 2), border_radius=5)
        time_ratio = max(0, self.game.timestamp['timer'] / (TIMER * DIFFICULTY_LEVELS[self.game.difficulty]['timer_modifier']))
        timer_width = int((WIDTH - 40) * time_ratio)
        pygame.draw.rect(self.game.win, DARK_BG, (20, HEIGHT - 50, WIDTH - 40, 10), border_radius=5)
        pygame.draw.rect(self.game.win, NEON_GREEN, (20, HEIGHT - 50, timer_width, 10), border_radius=5)
        pygame.draw.rect(self.game.win, NEON_GREEN, (20, HEIGHT - 50, WIDTH - 40, 10), 2, border_radius=5)
        if self.game.showing_pattern:
            self.game.drawText('Memorize this pattern.', WIDTH//2, HEIGHT - 70, WHITE)
        if self.game.show_level_message:
            if self.game.level <= DIFFICULTY_LEVELS[self.game.difficulty]['max_level']:
                self.game.drawText('Level Up!', WIDTH//2, HEIGHT//2, NEON_GREEN, True)
            else:
                self.game.drawText('Max Level! Keep Going!', WIDTH//2, HEIGHT//2, NEON_GREEN, True)
            if time.time() >= self.game.level_transition_time:
                self.game.show_level_message = False

    async def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONUP and self.game.waiting_input and not self.game.timer_up:
            current_time = time.time()
            if current_time - self.game.last_click >= 0.2:
                self.game.last_click = current_time
                row, col = self.game.getClickedTile(*event.pos)
                if row is not None and (row, col) not in self.game.input_pattern:
                    self.game.input_pattern.append((row, col))
                    self.game.tile_animations.clear()
                    for (r, c) in self.game.input_pattern:
                        color = NEON_GREEN if (r, c) in self.game.new_pattern else NEON_RED
                        self.game.lightUp(r, c, color)
                    if len(self.game.input_pattern) == len(self.game.new_pattern):
                        self.game.waiting_input = False
                        self.game.tile_animations.clear()
                        if self.game.input_pattern == self.game.new_pattern:
                            self.game.score += 10
                            self.game.high_scores[self.game.difficulty] = max(self.game.score, self.game.high_scores.get(self.game.difficulty, 0))
                            self.game.timestamp['timer'] = TIMER * DIFFICULTY_LEVELS[self.game.difficulty]['timer_modifier']
                            self.game.timestamp['past'] = current_time
                            for (r, c) in self.game.new_pattern:
                                self.game.lightUp(r, c, NEON_GREEN)
                            self.game.show_level_message = True
                            self.game.level_transition_time = current_time + 1.0
                            self.game.level += 1
                            self.game.tile_size = max(50, self.game.tile_size - 10)
                            self.game.new_pattern = []
                            self.game.input_pattern = []
                            self.game.pattern_index = 0
                            self.game.showing_pattern = True
                            self.game.next_tile_time = current_time + self.game.tile_show_interval
                            self.game.pattern_show_end_time = 0
                            self.game.new_pattern = self.generatePattern()
                            self.pattern_start_time = current_time
                            self.game.tile_animations.clear()
                            self.game.timestamp['past'] = current_time
                        else:
                            self.game.high_scores[self.game.difficulty] = max(self.game.score, self.game.high_scores.get(self.game.difficulty, 0))
                            self.game.state = 'gameover'
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.game.state = 'paused'

    async def update(self):
        self.game.runTimer()
        if self.game.timer_up:
            self.game.high_scores[self.game.difficulty] = max(self.game.score, self.game.high_scores.get(self.game.difficulty, 0))
            self.game.state = 'gameover'
            self.game.waiting_input = False
            self.game.tile_animations.clear()
        elif not self.game.waiting_input and not self.game.timer_up:
            current_time = time.time()
            tile_show_duration = 1.0 if self.game.difficulty == 'easy' else self.game.tile_show_interval
            if not self.game.new_pattern or len(self.game.new_pattern) != self.game.level:
                self.game.new_pattern = self.generatePattern()
                self.game.pattern_index = 0
                self.game.showing_pattern = True
                self.game.next_tile_time = current_time + tile_show_duration
                self.game.pattern_show_end_time = 0
                self.pattern_start_time = current_time
            elif self.game.showing_pattern:
                if current_time - self.pattern_start_time > 5:
                    self.game.showing_pattern = False
                    self.game.waiting_input = True
                    self.game.tile_animations.clear()
                    self.game.pattern_index = 0
                elif self.game.pattern_index >= len(self.game.new_pattern):
                    if current_time >= self.game.pattern_show_end_time:
                        self.game.showing_pattern = False
                        self.game.waiting_input = True
                        self.game.timestamp['past'] = current_time
                        self.game.tile_animations.clear()
                        self.game.pattern_index = 0
                elif current_time >= self.game.next_tile_time:
                    row, col = self.game.new_pattern[self.game.pattern_index]
                    if (row, col) not in self.game.tile_animations:
                        self.game.lightUp(row, col, NEON_GREEN)
                        self.game.tile_animations[(row, col)] = {'scale': 1.0, 'alpha': 255, 'color': NEON_GREEN}
                    self.game.pattern_index += 1
                    if self.game.pattern_index < len(self.game.new_pattern):
                        self.game.next_tile_time = current_time + tile_show_duration
                    else:
                        self.game.pattern_show_end_time = current_time + self.game.memorize_time
                        if self.game.difficulty == 'easy':
                            self.game.pattern_show_end_time += tile_show_duration

    def generatePattern(self):
        pattern = []
        while len(pattern) < self.game.level:
            row = random.randrange(self.game.level)
            col = random.randrange(self.game.level)
            if (row, col) not in pattern:
                pattern.append((row, col))
        return pattern

class GameOverScreen(Screen):
    def draw(self):
        self.game.drawAnimatedBackground()
        self.game.drawText('Game Over!', WIDTH//2, 100, NEON_RED, True)
        self.game.drawText(f'Score: {self.game.score}', WIDTH//2, 180, WHITE, shadow=True)
        self.game.drawText(f'Best: {self.game.high_scores.get(self.game.difficulty, 0)}', WIDTH//2, 220, WHITE, shadow=True)
        if self.game.score > 0:
            self.game.drawText('Good Effort!', WIDTH//2, 260, NEON_GREEN, shadow=True)
        mouse_pos = pygame.mouse.get_pos()
        hover_restart = self.game.buttons['restart'].collidepoint(mouse_pos)
        hover_leaderboard = self.game.buttons['leaderboard'].collidepoint(mouse_pos)
        self.game.drawButton('Play Again', self.game.buttons['restart'], hover_restart)
        self.game.drawButton('Leaderboard', self.game.buttons['leaderboard'], hover_leaderboard)

    async def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONUP:
            current_time = time.time()
            if (current_time - self.game.last_click) > 0.2:
                self.game.last_click = current_time
                if self.game.buttons['leaderboard'].collidepoint(event.pos):
                    self.game.state = 'leaderboard'
                elif self.game.buttons['restart'].collidepoint(event.pos):
                    self.game.resetGame()
                    self.game.state = 'playing'

class LeaderboardScreen(Screen):
    def draw(self):
        self.game.drawAnimatedBackground()
        self.game.drawText('Leaderboard', WIDTH//2, 50, NEON_GREEN, True)
        y = 150
        for diff, score in sorted(self.game.high_scores.items(), key=lambda x: x[1], reverse=True):
            self.game.drawText(f'{diff.capitalize()}: {score}', WIDTH//2, y, WHITE)
            y += 50
        mouse_pos = pygame.mouse.get_pos()
        hover = self.game.buttons['restart'].collidepoint(mouse_pos)
        self.game.drawButton('Play Again', self.game.buttons['restart'], hover)

    async def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONUP:
            current_time = time.time()
            if (current_time - self.game.last_click) > 0.2:
                self.game.last_click = current_time
                if self.game.buttons['restart'].collidepoint(event.pos):
                    self.game.resetGame()
                    self.game.state = 'playing'

class PauseScreen(Screen):
    def draw(self):
        self.game.drawAnimatedBackground()
        self.game.drawText('Paused', WIDTH//2, HEIGHT//4, NEON_YELLOW, True)
        mouse_pos = pygame.mouse.get_pos()
        hover_back = self.game.buttons['back_to_menu'].collidepoint(mouse_pos)
        self.game.drawButton('Back to Menu', self.game.buttons['back_to_menu'], hover_back)

    async def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONUP:
            current_time = time.time()
            if (current_time - self.game.last_click) > 0.2:
                self.game.last_click = current_time
                if self.game.buttons['back_to_menu'].collidepoint(event.pos):
                    self.game.state = 'difficulty'
                    self.game.resetGame()
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.game.state = 'playing'