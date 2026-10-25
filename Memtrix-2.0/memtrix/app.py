"""Native Pygame interface, one event loop and explicit game/menu states."""
import argparse
from datetime import date
import math
from pathlib import Path
import time
import pygame
from .audio import Audio
from .model import Session, Settings, MODES, RULES, ACHIEVEMENTS, achievements
from .storage import Store
from .ui import Painter, Button, WIDTH, HEIGHT, BG, SIDE, PANEL, RAISED, LINE, TEXT, MUTED, ACCENT, CYAN, CORAL, GOLD, THEMES


class Game:
    def __init__(self, directory=None, size=(1280, 800), silent=False):
        pygame.display.init(); pygame.font.init()
        self.window = pygame.display.set_mode(size, pygame.RESIZABLE)
        pygame.display.set_caption("Memtrix 2.0 — a little focus, a stronger pattern")
        icon = pygame.Surface((64, 64)); icon.fill(BG)
        for i in range(9):
            pygame.draw.rect(icon, ACCENT if i in (0,4,5,7) else LINE, (7+i%3*18,7+i//3*18,14,14), border_radius=3)
        pygame.display.set_icon(icon)
        self.ui = Painter()
        self.store = Store(directory)
        self.settings = self.store.settings
        self.audio = None if silent else Audio()
        self.screen = "home"
        self.mode = "classic"
        self.session = None
        self.result = None
        self.saved = False
        self.personal_best = False
        self.new_achievements = set()
        self.fullscreen = False
        self.windowed_size = size
        self.viewport = (0, 0, WIDTH, HEIGHT)
        self.pointer = (0, 0)
        self.focus = -1
        self.countdown = 0
        self.running = True
        self.uptime = 0
        self.message = self.store.notice
        self.message_until = 10 if self.message else 0
        self.profile_input = ""
        self.editing = False
        self.tab = "History"
        self.page = 0
        self.filter = "all"
        self.grid_cache = {}
        self.render()

    def sound(self, name):
        if self.audio: self.audio.play(name, self.settings.volume)

    def notify(self, message, seconds=6):
        self.message = str(message); self.message_until = self.uptime + seconds

    def show(self, screen):
        self.screen = screen; self.focus = -1; self.editing = False
        pygame.key.stop_text_input()

    def start(self, daily=False):
        self.session = Session(self.mode, self.settings, daily=daily)
        self.countdown = 3.0
        self.saved = False
        self.show("countdown")

    def finish(self):
        if self.saved: return
        previous = achievements(self.store.sessions)
        self.result, self.personal_best, saved = self.store.add(self.session.summary())
        self.new_achievements = achievements(self.store.sessions) - previous
        self.saved = True
        self.show("results"); self.sound("finish")
        if not saved: self.notify(self.store.notice, 12)

    def map_point(self, point):
        x,y,w,h = self.viewport
        if not (x <= point[0] < x+w and y <= point[1] < y+h): return None
        return ((point[0]-x)*WIDTH/w, (point[1]-y)*HEIGHT/h)

    def board_rects(self):
        n = self.session.grid
        if n not in self.grid_cache:
            gap = 12
            size = (600 - (n-1)*gap)//n
            span = n*size+(n-1)*gap
            left, top = 70+(890-span)//2, 187+(615-span)//2
            self.grid_cache[n] = [pygame.Rect(left+(i%n)*(size+gap), top+(i//n)*(size+gap), size, size) for i in range(n*n)]
        return self.grid_cache[n]

    def toggle_fullscreen(self):
        try:
            if not self.fullscreen:
                self.windowed_size = self.window.get_size()
                self.window = pygame.display.set_mode((0,0), pygame.FULLSCREEN)
            else: self.window = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
            self.fullscreen = not self.fullscreen
            self.render()
        except pygame.error: self.notify("Fullscreen is unavailable. Windowed mode is still ready.")

    def act(self, action):
        self.sound("click")
        if isinstance(action, tuple):
            kind, value = action
            if kind == "mode": self.mode = value
            elif kind == "tile":
                if self.screen == "play": self.session.select(value)
            elif kind == "setting":
                name, choices = value
                current = getattr(self.settings, name)
                setattr(self.settings, name, choices[(choices.index(current)+1)%len(choices)])
                if not self.store.set_settings(self.settings): self.notify(self.store.notice)
            elif kind == "profile":
                saved = self.store.select(value); self.settings = self.store.settings
                self.notify("Profile switched." if saved else self.store.notice)
            elif kind == "tab": self.tab = value; self.page = 0
            elif kind == "page": self.page = max(0,self.page+value)
            return
        if action in ("home","statistics","profiles","settings","help"): self.show(action)
        elif action == "start": self.start()
        elif action == "daily": self.start(True)
        elif action == "pause": self.show("paused")
        elif action == "resume": self.show("play")
        elif action == "restart": self.start(self.session.daily)
        elif action == "end": self.session.finish("Practice ended" if self.session.mode == "practice" else "Ended early"); self.finish()
        elif action == "hint": self.session.hint()
        elif action == "quit": self.running = False
        elif action == "edit": self.editing = True; pygame.key.start_text_input()
        elif action == "create":
            try:
                saved = self.store.create(self.profile_input)
                self.profile_input = ""; self.settings = self.store.settings; self.editing = False
                self.notify("New profile ready." if saved else self.store.notice)
            except ValueError as exc: self.notify(exc)
        elif action == "filter":
            values = ["all",*MODES]; self.filter = values[(values.index(self.filter)+1)%len(values)]; self.page = 0
        elif action == "export":
            try: self.store.export(); self.notify("CSV saved in your data folder / exports. See How to play for the folder path.", 9)
            except OSError: self.notify("Export failed: check data-folder write permission.")
        elif action == "import":
            path = Path(__file__).resolve().parents[1]/"legacy/v1.0/highscores.json"
            try:
                saved = self.store.import_legacy(path)
                self.notify("Archived v1 scores imported. View Statistics > Legacy v1." if saved else self.store.notice)
            except (OSError,ValueError): self.notify("Use --import-v1 with a valid old highscores.json file. See README.")

    def handle(self, event):
        if event.type == pygame.QUIT: self.running = False
        elif event.type == pygame.VIDEORESIZE and not self.fullscreen:
            self.window = pygame.display.set_mode((max(640,event.w),max(400,event.h)), pygame.RESIZABLE)
            self.windowed_size = self.window.get_size(); self.render()
        elif event.type == pygame.WINDOWFOCUSLOST:
            if self.screen == "play": self.show("paused")
            elif self.screen == "countdown": self.show("ready")
        elif event.type == pygame.MOUSEMOTION: self.pointer = self.map_point(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.pointer = self.map_point(event.pos)
            for button in self.ui.buttons:
                if self.pointer and button.rect.collidepoint(self.pointer):
                    self.act(button.action); break
        elif event.type == pygame.TEXTINPUT and self.editing:
            self.profile_input = (self.profile_input + "".join(c for c in event.text if c.isprintable()))[:24]
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F11: self.toggle_fullscreen()
            elif self.editing:
                if event.key == pygame.K_BACKSPACE: self.profile_input = self.profile_input[:-1]
                elif event.key == pygame.K_RETURN: self.act("create")
                elif event.key == pygame.K_ESCAPE: self.editing = False
            elif event.key == pygame.K_ESCAPE:
                if self.screen == "play": self.show("paused")
                elif self.screen == "paused": self.show("play")
                else: self.show("home")
            elif event.key == pygame.K_TAB and self.ui.buttons:
                self.focus = (self.focus + (-1 if event.mod & pygame.KMOD_SHIFT else 1))%len(self.ui.buttons)
            elif event.key in (pygame.K_RETURN,pygame.K_SPACE):
                if self.screen == "ready": self.countdown = 3; self.show("countdown")
                elif 0 <= self.focus < len(self.ui.buttons): self.act(self.ui.buttons[self.focus].action)
            elif event.key == pygame.K_r and self.screen == "results": self.act("restart")
            elif event.key == pygame.K_h and self.screen == "play": self.act("hint")

    def update(self, dt):
        self.uptime += dt; self.ui.dt = dt
        if self.screen == "countdown":
            self.countdown -= dt
            if self.countdown <= 0: self.show("play")
        elif self.screen == "play":
            self.session.update(dt)
            for name,_ in self.session.events: self.sound(name)
            self.session.events.clear()
            if self.session.finished: self.finish()

    def motif(self, x, y, cell=22, active=(0,4,5,7), phase=False):
        for i in range(9):
            lit = i in active
            if phase and not self.settings.reduced_motion:
                lit = i == int(self.uptime*1.2)%9 or lit
            pygame.draw.rect(self.ui.surface, ACCENT if lit else (211,210,235), (x+i%3*(cell+5),y+i//3*(cell+5),cell,cell), border_radius=max(3,cell//5))

    def workspace(self, title, subtitle):
        u=self.ui
        pygame.draw.rect(u.surface,SIDE,(0,0,226,HEIGHT)); pygame.draw.line(u.surface,LINE,(226,0),(226,HEIGHT))
        self.motif(25,31,11)
        u.text("memtrix",(78,28),26,TEXT,True); u.text("MEMORY STUDIO / 2.0",(79,62),9,MUTED,True)
        u.text("YOUR WORKSPACE",(24,124),11,MUTED,True)
        for i,(key,label) in enumerate([("home","Play"),("statistics","Progress"),("profiles","Profiles"),("settings","Settings"),("help","How to play")]):
            y=158+i*60
            u.button((20,y,185,44),label,key,self.screen==key,True)
        u.panel((19,692,188,111))
        u.text("CURRENT PROFILE",(34,709),10,MUTED,True)
        u.fit(self.store.active,(34,733),160,20,TEXT,True)
        u.text(f"{len(self.store.sessions)} saved sessions",(34,771),12,MUTED)
        u.text("OFFLINE, BY DESIGN",(27,851),10,MUTED,True)
        u.text("MEMORY / "+self.screen.upper(),(274,32),11,MUTED,True)
        u.text(title,(274,75),36,TEXT,True); u.text(subtitle,(277,129),16,MUTED)
        pygame.draw.line(u.surface,LINE,(274,169),(1392,169))

    def home(self):
        u=self.ui
        self.workspace("A little focus. A stronger pattern.","Observe, remember, replay. Find a challenge that fits your rhythm.")
        u.panel((274,192,1118,179),(232,229,250),False)
        u.text("MAKE ROOM FOR A MOMENT OF FOCUS",(302,215),11,ACCENT,True)
        u.text("One pattern at a time.",(302,249),32,TEXT,True)
        u.text("Five ways to practice spatial memory and sequence recall.",(303,299),16,MUTED)
        u.text("Choose a mode below. Your progress stays on this device.",(303,332),13,MUTED)
        self.motif(1215,225,31,phase=True)
        u.text("CHOOSE YOUR CHALLENGE",(278,393),11,MUTED,True)
        for i,(key,(name,desc,hint)) in enumerate(MODES.items()):
            x,y=274+i%2*568,419+i//2*109
            u.panel((x,y,550,95),(242,239,255) if self.mode==key else PANEL)
            if self.mode==key: pygame.draw.rect(u.surface,ACCENT,(x,y,550,95),1,border_radius=18)
            u.text(f"0{i+1}",(x+17,y+16),12,ACCENT,True)
            u.text(name,(x+52,y+12),21,TEXT,True)
            u.text(desc,(x+52,y+46),13,MUTED)
            u.text(hint,(x+52,y+70),10,CYAN)
            u.button((x+430,y+28,101,39),"Selected" if self.mode==key else "Select",("mode",key),self.mode==key,True)
        u.panel((842,637,550,95),(252,245,227))
        u.text("THE DAILY PATTERN",(860,650),10,GOLD,True)
        u.text(date.today().strftime("%d %B %Y"),(860,672),20,TEXT,True)
        u.text("Time Attack / Medium / 60 seconds",(860,706),11,MUTED)
        u.button((1243,660,130,44),"Play daily","daily",small=True)
        u.text(self.settings.difficulty.upper()+"  /  "+("NO TIMER" if self.mode=="practice" else f"{self.settings.duration} SECONDS" if self.mode=="time_attack" else "ROUND-BASED"),(278,785),13,MUTED,True)
        u.button((1062,764,330,64),"Start training   >","start",True)
        u.text("ESC pauses  /  F11 fullscreen  /  Tab + Enter navigates",(278,849),12,MUTED)

    def play(self):
        u,s=self.ui,self.session
        u.text("memtrix",(39,25),25,TEXT,True)
        u.text("DAILY TIME ATTACK" if s.daily else MODES[s.mode][0].upper(),(40,66),11,ACCENT,True)
        title={"preview":"Watch. Let the pattern settle.","recall":"Your turn. Trust your memory.","feedback":s.feedback}[s.phase]
        u.text(title,(300,27),29,TEXT,True)
        u.text("Recall backward" if s.style=="reverse" else "Any order" if s.style=="pattern" else "Repeat in order",(303,72),14,MUTED)
        u.button((1254,28,145,47),"Pause","pause",small=True)
        pygame.draw.line(u.surface,LINE,(40,109),(1400,109))
        u.text(f"{s.grid} × {s.grid} GRID",(82,139),11,MUTED,True)
        u.text(f"{s.length} TILES TO REMEMBER",(956,139),11,MUTED,True,"right")
        u.panel((60,171,922,649),(237,239,247),False,22)
        lit=s.lit_tiles(); accent,tint=THEMES[self.settings.theme]
        for i,rect in enumerate(self.board_rects()):
            selected=i in s.selected
            on=i in lit
            wrong=i==s.wrong_tile and s.phase=="feedback"
            color=CORAL if wrong else accent if on else (211,238,230) if selected and s.phase=="recall" else tint if self.settings.theme=="High contrast" else PANEL
            u.panel(rect,color,not on and not wrong,max(8,rect.w//9))
            glyph=None; text_color=(255,255,255) if wrong or (on and self.settings.theme!="High contrast") else TEXT
            if wrong: glyph="×"
            elif on and s.style!="pattern": glyph=str(s.expected.index(i)+1) if s.phase=="feedback" else str(s.pattern.index(i)+1)
            elif on: glyph="•"
            elif selected and s.phase=="recall": glyph=str(s.selected.index(i)+1) if s.style!="pattern" else "✓"
            if glyph: u.text(glyph,(rect.centerx,rect.centery-16),max(18,min(30,rect.w//4)),text_color,True,"center")
            if self.pointer and rect.collidepoint(self.pointer) and s.phase=="recall": pygame.draw.rect(u.surface,ACCENT,rect.inflate(-4,-4),2,border_radius=10)
            index=len(u.buttons)
            if index==self.focus: pygame.draw.rect(u.surface,CYAN,rect.inflate(6,6),2,border_radius=12)
            u.buttons.append(Button(rect,"Tile "+str(i+1),("tile",i)))
        u.panel((1008,171,392,649))
        u.text("SESSION AT A GLANCE",(1033,193),11,MUTED,True)
        u.text(f"{s.score:,}",(1032,226),52,TEXT,True)
        u.text("POINTS",(1035,293),11,ACCENT,True)
        for i,(label,value) in enumerate([("Difficulty",s.settings.difficulty),("Rounds cleared",str(s.rounds_correct)),("Longest recalled",f"{s.longest} tiles"),("Selection accuracy",f"{s.accuracy:.1f}%"),("Lives",str(s.lives) if s.lives is not None else "Unlimited")]):
            y=339+i*42
            u.text(label,(1033,y),14,MUTED); u.text(value,(1373,y),16,TEXT,True,"right")
        if s.duration is not None:
            remaining=max(0,s.duration-s.elapsed); label="SESSION TIME LEFT"; ratio=remaining/s.duration
        elif s.phase=="recall" and s.recall_limit:
            remaining=max(0,s.recall_limit-s.phase_elapsed); label="RECALL TIME LEFT"; ratio=remaining/s.recall_limit
        elif s.phase=="preview":
            remaining=max(0,s.preview_duration-s.phase_elapsed); label="PLAYBACK"; ratio=remaining/s.preview_duration
        else: remaining=None; label="TAKE YOUR TIME" if s.mode=="practice" else "NEXT ROUND"; ratio=1
        u.text(label,(1033,574),10,MUTED,True)
        u.text(f"{remaining:.1f} s" if remaining is not None else "No rush",(1033,600),27,ACCENT,True)
        pygame.draw.rect(u.surface,LINE,(1034,646,338,6),border_radius=3)
        pygame.draw.rect(u.surface,ACCENT,(1034,646,int(338*max(0,min(1,ratio))),6),border_radius=3)
        u.text(f"{len(s.selected)} / {s.length} tiles entered",(1033,678),14,MUTED)
        u.text("WATCH" if s.phase=="preview" else "RECALL" if s.phase=="recall" else "REVIEW",(1033,716),11,CYAN,True)
        if s.mode=="practice": u.button((1030,754,346,44),"Replay hint [H]","hint",small=True)
        else: u.text("Hints are available in Practice.",(1033,768),12,MUTED)
        u.text("Left click or Tab + Enter to select. Duplicate selections are ignored.",(67,845),13,MUTED)
        u.text("ESC pauses playback and timers",(1397,845),13,ACCENT,False,"right")

    def overlay(self):
        u=self.ui
        overlay=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA); overlay.fill((35,43,63,165)); u.surface.blit(overlay,(0,0)); u.buttons=[]
        u.panel((452,211,536,468),PANEL)
        if self.screen in ("countdown","ready"):
            u.text("A MOMENT TO FOCUS",(720,261),12,ACCENT,True,"center")
            u.text(str(max(1,math.ceil(self.countdown))) if self.screen=="countdown" else "Ready?",(720,326),92,TEXT,True,"center")
            u.text("Watch first. Your turn comes next.",(720,466),17,MUTED,False,"center")
            u.text("ESC returns to Play" if self.screen=="countdown" else "Press Enter to restart the countdown.",(720,531),14,MUTED,False,"center")
        else:
            u.text("PAUSED",(720,244),12,ACCENT,True,"center")
            u.text("Hold that thought.",(720,281),36,TEXT,True,"center")
            u.text("Playback and all timers are frozen.",(720,338),16,MUTED,False,"center")
            for y,label,action,primary in [(392,"Resume","resume",True),(460,"Restart run","restart",False),(528,"End session & save","end",False)]:
                u.button((502,y,435,52),label,action,primary)
            u.text("ESC resumes",(720,623),13,MUTED,False,"center")

    def results(self):
        u,r=self.ui,self.result
        self.workspace("A pattern worth remembering.","Keep the learning. Leave the pressure. Try another round when you are ready.")
        u.panel((274,193,1118,176),(232,229,250),False)
        u.text("PERSONAL BEST" if self.personal_best else "SESSION RECORDED",(300,214),11,ACCENT,True)
        u.text(f"{r['score']:,}",(299,245),56,TEXT,True)
        u.text("POINTS",(543,285),11,MUTED,True)
        u.text(MODES[r['mode']][0]+" / "+r['difficulty'],(1364,231),20,TEXT,True,"right")
        u.text(r['reason'],(1364,276),16,MUTED,False,"right")
        u.text("Assisted practice" if r['assisted'] else "Daily challenge" if r['daily'] else "Unassisted run",(1364,318),12,ACCENT,True,"right")
        values=[("Rounds cleared",str(r['rounds_correct'])),("Selection accuracy",f"{r['accuracy']:.1f}%"),("Longest recalled",f"{r['longest']} tiles"),("Mistakes / timeouts",f"{r['mistakes']} / {r['timeouts']}"),("Average round recall",f"{r['average_recall_ms']/1000:.2f} s" if r['average_recall_ms'] is not None else "—"),("Active time",f"{r['elapsed']:.1f} s")]
        for i,(label,value) in enumerate(values):
            x,y=274+i%3*379,395+i//3*116
            u.panel((x,y,360,99)); u.text(label,(x+20,y+16),13,MUTED); u.text(value,(x+20,y+46),29,TEXT,True)
        names=", ".join(ACHIEVEMENTS[a][0] for a in sorted(self.new_achievements))
        u.fit("Unlocked: "+names if names else "Progress saved to "+self.store.active+".",(279,656),1100,17,ACCENT)
        u.text("Recall time measures a complete successful response, not clinical memory ability.",(279,696),13,MUTED)
        u.button((274,758,260,60),"Play again [R]","restart",True)
        u.button((554,758,260,60),"See progress","statistics")
        u.button((834,758,260,60),"Choose another mode","home")

    def chart(self, rows):
        u=self.ui; u.panel((274,300,1118,202))
        u.text("SELECTION ACCURACY / LAST 12 FILTERED RUNS",(296,317),11,MUTED,True)
        for value in (0,50,100):
            y=471-value*1.08
            pygame.draw.line(u.surface,LINE,(326,y),(1365,y)); u.text(str(value),(292,y-8),10,MUTED)
        points=[(round(334+i/max(1,len(rows)-1)*1020),round(471-r['accuracy']*1.08)) for i,r in enumerate(rows)]
        if len(points)>1: pygame.draw.lines(u.surface,ACCENT,False,points,3)
        for point in points: pygame.draw.circle(u.surface,CYAN,point,4)
        if not rows: u.text("Your first session starts the story.",(831,397),18,MUTED,False,"center")

    def statistics(self):
        u=self.ui
        self.workspace("See what is taking shape.","History, personal bests and milestones for the active local profile.")
        for i,tab in enumerate(("History","Personal bests","Achievements","Legacy v1")):
            u.button((274+i*207,190,194,42),tab,("tab",tab),self.tab==tab,True)
        u.button((1160,190,232,42),"Export CSV","export",small=True)
        if self.tab=="Achievements":
            earned=achievements(self.store.sessions)
            for i,(key,(name,desc)) in enumerate(ACHIEVEMENTS.items()):
                x,y=274+i%2*568,258+i//2*134
                u.panel((x,y,550,115),(230,241,235) if key in earned else PANEL)
                u.text("UNLOCKED" if key in earned else "IN PROGRESS",(x+22,y+14),10,CYAN if key in earned else MUTED,True)
                u.text(name,(x+22,y+40),22,TEXT,True); u.text(desc,(x+22,y+79),14,MUTED)
            return
        if self.tab=="Legacy v1":
            u.panel((274,260,1118,418)); u.text("YOUR ORIGINAL CHAPTER",(300,287),12,ACCENT,True)
            u.text("Archived scores, kept in context.",(300,327),29,TEXT,True)
            u.text("Imported v1 values use their original scoring. They never enter the v2 best tables.",(300,382),16,MUTED)
            for i,diff in enumerate(RULES):
                x=301+i*355; u.panel((x,440,326,112),RAISED,False)
                u.text(diff,(x+20,455),15,MUTED); u.text(str(self.store.current['legacy_scores'].get(diff,"—")),(x+20,486),32,TEXT,True)
            u.button((300,594,405,52),"Import archived v1 scores","import",True)
            return
        if self.tab=="History":
            rows=[r for r in self.store.sessions if self.filter=="all" or r['mode']==self.filter]
            u.text(f"{len(rows)} sessions / newest first below",(279,263),13,MUTED)
            u.button((1077,251,315,36),"Mode: "+("All" if self.filter=="all" else MODES[self.filter][0]),"filter",small=True)
            self.chart(rows[-12:]); rows=list(reversed(rows)); top=529; count=4
        else:
            rows=self.store.bests(); top=278; count=8
            u.text("Grouped by mode, difficulty and duration. Assisted / unfinished runs are excluded.",(279,252),13,MUTED)
        maximum=max(0,(len(rows)-1)//count); self.page=min(self.page,maximum)
        u.panel((274,top,1118,40),RAISED,False,8)
        for label,x in [("MODE / DATE",294),("DIFFICULTY",682),("SCORE",850),("ACCURACY",1000),("ROUNDS",1245)]: u.text(label,(x,top+12),10,MUTED,True)
        visible=rows[self.page*count:(self.page+1)*count]
        for i,r in enumerate(visible):
            y=top+48+i*54
            u.text(("Daily " if r['daily'] else "")+MODES[r['mode']][0],(294,y),15,TEXT,True)
            u.text(r['date'][:16].replace('T',' ')+" UTC"+(" / assisted" if r['assisted'] else ""),(294,y+23),10,MUTED)
            for text,x in [(r['difficulty'],682),(f"{r['score']:,}",850),(f"{r['accuracy']:.1f}%",1000),(str(r['rounds_correct']),1245)]: u.text(text,(x,y+9),16,ACCENT if x==850 else TEXT)
            pygame.draw.line(u.surface,LINE,(292,y+48),(1372,y+48))
        if not visible: u.text("Complete a run to add your first result.",(829,top+115),19,MUTED,False,"center")
        u.button((1032,826,116,39),"Previous",("page",-1),small=True)
        u.text(f"{self.page+1} / {maximum+1}",(1191,837),13,MUTED,False,"center")
        u.button((1249,826,143,39),"Next",("page",1),small=True)

    def settings_screen(self):
        u=self.ui
        self.workspace("Set your own rhythm.","Settings save automatically for each profile. Click a value to cycle its choices.")
        groups=[("COMPETITIVE",[("difficulty","Difficulty",list(RULES)),("duration","Time Attack duration",[60,90,120])]),
                ("PRACTICE STUDIO",[("grid","Grid dimension",[3,4,5,6,8]),("length","Tiles to remember",[3,4,6,8,12]),("playback","Playback speed",["Slow","Normal","Fast"]),("practice_style","Recall style",["Sequence","Pattern","Reverse"])]),
                ("COMFORT & DISPLAY",[("theme","Tile theme",list(THEMES)),("volume","Sound volume (%)",[0,25,50,75,100]),("reduced_motion","Reduced motion",[False,True]),("fps","Frame cap",[60,120,144])])]
        for col,(title,items) in enumerate(groups):
            x=274+col*379; u.panel((x,195,360,455)); u.text(title,(x+20,218),12,ACCENT,True)
            for i,(key,label,choices) in enumerate(items):
                y=265+i*85; u.text(label,(x+20,y),13,MUTED)
                value=getattr(self.settings,key); value=("On" if value else "Off") if type(value) is bool else str(value)
                u.button((x+20,y+27,320,40),value,("setting",(key,choices)),small=True)
        u.panel((274,676,1118,149),(232,229,250),False)
        self.motif(300,706,20)
        u.text("A theme changes the look, not the rules.",(423,704),22,TEXT,True)
        u.text("Practice settings never change competitive playback or daily challenge difficulty.",(425,748),15,MUTED)
        u.text("Reduced motion stops decorative animation. Tile flashes remain essential gameplay.",(425,783),13,MUTED)
        if self.audio is None or not self.audio.available: u.text("Sound is unavailable on this device. The game remains fully playable.",(280,850),13,GOLD)

    def profiles(self):
        u=self.ui
        self.workspace("A small space of your own.","Separate settings, sessions and legacy scores for up to 20 local profiles.")
        u.panel((274,194,1118,169)); u.text("CREATE A PROFILE",(299,214),12,ACCENT,True)
        u.button((295,260,659,57),self.profile_input+("|" if self.editing and int(self.uptime*2)%2==0 else "") if self.profile_input else "Click here and type a name (24 characters)","edit",small=True)
        u.button((978,260,390,57),"Create profile","create",True)
        u.text("Local profiles organize progress; they are not password-protected accounts.",(299,335),12,MUTED)
        for i,name in enumerate(self.store.data['profiles']):
            x,y=274+i%3*379,391+i//3*64
            u.button((x,y,360,49),("Active: " if name==self.store.active else "")+name,("profile",name),name==self.store.active,True)

    def help_screen(self):
        u=self.ui
        self.workspace("Give your memory a moment.","A native Python game. Offline play, clear rules and progress you can inspect.")
        items=[("01 / WATCH, THEN RECALL","Classic repeats the sequence; Reverse repeats it backward. Pattern Recall accepts any order.","Tiles are hidden before input starts. Numbered selections and an X make feedback clear."),
               ("02 / CONTROLS","Left click or Tab + Enter selects tiles. ESC pauses. F11 toggles fullscreen. R restarts results.","Practice only: H or Replay hint shows the same pattern again. Repeated tile selections are ignored."),
               ("03 / CHALLENGE","Correct rounds grow the sequence and, every three rounds, the grid up to 6 × 6.","Classic / Pattern / Reverse: 3, 2 or 1 lives by difficulty. Time Attack counts all active phases."),
               ("04 / SCORES","Only completed rounds earn points: 100 per tile, plus bounded speed and streak bonuses.","Practice and early endings stay in history but do not enter competitive personal-best tables."),
               ("05 / YOUR DATA","Progress is local; history retains 1,000 runs per profile. CSV exports use the exports subfolder.","Original v1 scores can be imported separately under Progress > Legacy v1. They are not v2 scores.")]
        for i,(title,line1,line2) in enumerate(items):
            y=194+i*107; u.panel((274,y,1118,94)); u.text(title,(296,y+12),11,ACCENT,True)
            u.text(line1,(296,y+39),14,TEXT); u.text(line2,(296,y+66),13,MUTED)
        u.text("DATA FOLDER",(280,756),11,MUTED,True); u.fit(str(self.store.directory),(280,782),1100,15,CYAN)
        u.fit("Original source and coursework documents are preserved in legacy/ and docs/original_v1.0/.",(280,840),875,12,MUTED)
        u.button((1200,828,192,45),"Quit application","quit",small=True)

    def render(self):
        self.ui.begin(self.pointer,self.focus)
        if self.screen in ("play","paused","countdown","ready"):
            self.play()
            if self.screen!="play": self.overlay()
        elif self.screen=="home": self.home()
        elif self.screen=="statistics": self.statistics()
        elif self.screen=="settings": self.settings_screen()
        elif self.screen=="profiles": self.profiles()
        elif self.screen=="help": self.help_screen()
        elif self.screen=="results": self.results()
        if self.message and self.uptime<self.message_until:
            self.ui.panel((274,7,1118,43),(224,239,231),False)
            self.ui.fit(self.message,(291,19),1080,14,CYAN)
        ww,wh=self.window.get_size(); scale=min(ww/WIDTH,wh/HEIGHT)
        w,h=max(1,round(WIDTH*scale)),max(1,round(HEIGHT*scale)); x,y=(ww-w)//2,(wh-h)//2
        self.viewport=(x,y,w,h); self.window.fill((23,29,43))
        scaled=pygame.transform.smoothscale(self.ui.surface,(w,h)) if (w,h)!=(WIDTH,HEIGHT) else self.ui.surface
        self.window.blit(scaled,(x,y)); pygame.display.flip()

    def run(self):
        clock=pygame.time.Clock()
        try:
            while self.running:
                dt=clock.tick(self.settings.fps)/1000
                for event in pygame.event.get(): self.handle(event)
                self.update(dt); self.render()
        finally: pygame.quit()


def main():
    parser=argparse.ArgumentParser(description="Memtrix 2.0 — offline Python memory studio")
    parser.add_argument('--data-dir',type=Path,help='Use a different local progress folder')
    parser.add_argument('--no-audio',action='store_true',help='Skip audio-device initialization')
    parser.add_argument('--import-v1',type=Path,help='Import old highscores.json into a separate legacy area')
    args=parser.parse_args()
    try:
        game=Game(args.data_dir,silent=args.no_audio)
        if args.import_v1:
            try:
                saved=game.store.import_legacy(args.import_v1)
                game.notify('v1 scores imported separately.' if saved else game.store.notice)
            except (OSError,ValueError) as exc: game.notify(f'Could not import v1 scores: {exc}',12)
        game.run()
    except pygame.error as exc:
        raise SystemExit(f'The game could not open its display: {exc}\nStart it in a desktop session.') from exc


if __name__=='__main__': main()
