"""Locally synthesized optional feedback tones; no downloaded audio assets."""
from array import array
import math
import pygame


class Audio:
    def __init__(self):
        self.available = False
        self.sounds = {}
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            for name, pitch, duration in [("correct", 740, .06), ("mistake", 160, .13), ("ready", 520, .09), ("round", 950, .12), ("click", 450, .03), ("finish", 620, .2), ("hint", 390, .09)]:
                buffer = array("h", (int(6000 * math.sin(2 * math.pi * pitch * i / 22050) * (1-i/(22050*duration))**2) for i in range(int(22050*duration))))
                self.sounds[name] = pygame.mixer.Sound(buffer=buffer)
            self.available = True
        except (pygame.error, OSError, ValueError): pass

    def play(self, name, volume):
        if self.available and volume and name in self.sounds:
            self.sounds[name].set_volume(volume/100); self.sounds[name].play()
