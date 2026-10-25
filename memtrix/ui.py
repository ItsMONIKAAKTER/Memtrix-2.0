"""Pygame drawing helpers. Cached text and a fixed logical canvas keep UI predictable."""
from collections import OrderedDict
from dataclasses import dataclass
import math
import pygame

WIDTH, HEIGHT = 1440, 900
BG = (245, 246, 251)
SIDE = (235, 237, 246)
PANEL = (255, 255, 255)
RAISED = (233, 234, 248)
LINE = (217, 222, 235)
TEXT = (35, 43, 63)
MUTED = (107, 119, 140)
ACCENT = (104, 81, 202)
CYAN = (30, 132, 151)
CORAL = (185, 65, 89)
GOLD = (146, 103, 29)
THEMES = {
    'Iris': ((104,81,202),(238,234,255)),
    'Ocean': ((18,123,149),(225,243,249)),
    'Amber': ((154,95,14),(254,241,211)),
    'High contrast': ((247,246,255),(18,23,35)),
}


@dataclass
class Button:
    rect: pygame.Rect
    label: str
    action: object
    primary: bool = False


class Painter:
    def __init__(self):
        self.fonts = {}
        self.cache = OrderedDict()
        self.buttons = []
        self.pointer = (0, 0)
        self.focus = -1
        self.dt = 1 / 60
        self.hover = {}
        self.surface = pygame.Surface((WIDTH, HEIGHT))
        self.backdrop = pygame.Surface((WIDTH, HEIGHT))
        for y in range(HEIGHT):
            t = y / HEIGHT
            pygame.draw.line(self.backdrop, (int(246 - t * 4), int(247 - t * 3), int(252 - t * 2)), (0, y), (WIDTH, y))

    def text(self, text, pos, size=18, color=TEXT, bold=False, align="left"):
        text = str(text)
        key = (text, size, color, bold)
        rendered = self.cache.get(key)
        if rendered is None:
            font_key = (size, bold)
            if font_key not in self.fonts:
                self.fonts[font_key] = pygame.font.SysFont("segoeui,dejavusans,arial", size, bold=bold)
            rendered = self.fonts[font_key].render(text, True, color)
            self.cache[key] = rendered
            if len(self.cache) > 768:
                self.cache.popitem(last=False)
        rect = rendered.get_rect()
        if align == "center":
            rect.midtop = pos
        elif align == "right":
            rect.topright = pos
        else:
            rect.topleft = pos
        self.surface.blit(rendered, rect)
        return rect

    def fit(self, text, pos, max_width, size=18, color=TEXT, bold=False):
        font = self.fonts.get((size, bold)) or pygame.font.SysFont("segoeui,dejavusans,arial", size, bold=bold)
        value = str(text)
        while len(value) > 1 and font.size(value)[0] > max_width:
            value = value[:-2].rstrip() + "…"
        return self.text(value, pos, size, color, bold)

    def panel(self, rect, color=PANEL, border=True, radius=18):
        rect = pygame.Rect(rect)
        pygame.draw.rect(self.surface, color, rect, border_radius=radius)
        if border:
            pygame.draw.rect(self.surface, LINE, rect, 1, border_radius=radius)
        return rect

    def button(self, rect, label, action, primary=False, small=False):
        rect = pygame.Rect(rect)
        index = len(self.buttons)
        hovered = self.pointer is not None and rect.collidepoint(self.pointer)
        focused = index == self.focus
        hover_key = (rect.x, rect.y, rect.w, rect.h)
        amount = self.hover.get(hover_key, 0)
        amount += ((1 if hovered else 0) - amount) * (1 - math.exp(-12 * min(self.dt, .1)))
        self.hover[hover_key] = amount
        color = ACCENT if primary else tuple(round(a + (b - a) * amount) for a, b in zip(PANEL, RAISED))
        if primary and hovered:
            color = (120, 97, 215)
        self.panel(rect, color, not primary, 11)
        if focused:
            pygame.draw.rect(self.surface, CYAN, rect.inflate(6, 6), 2, border_radius=13)
        size = 16 if small else 18
        font = self.fonts.get((size, True)) or pygame.font.SysFont("segoeui,dejavusans,arial", size, bold=True)
        display_label = label
        while len(display_label) > 1 and font.size(display_label)[0] > rect.width - 16:
            display_label = display_label[:-2].rstrip() + "…"
        self.text(display_label, (rect.centerx, rect.y + (rect.height - size) // 2 - 2), size, (255, 255, 255) if primary else TEXT, True, "center")
        self.buttons.append(Button(rect, label, action, primary))

    def begin(self, pointer, focus):
        self.surface.blit(self.backdrop, (0, 0))
        self.buttons = []
        self.pointer, self.focus = pointer, focus

