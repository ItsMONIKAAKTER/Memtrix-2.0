"""Isolated real Pygame event dispatch, native rendering and scoped measurements."""
import argparse
import json
import os
from pathlib import Path
import statistics
import sys
import tempfile
import time
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame
from memtrix.app import Game
from memtrix.model import MODES


def click(game,action):
    game.render()
    button=next(b for b in game.ui.buttons if b.action==action)
    x,y,w,h=game.viewport
    point=(round(x+button.rect.centerx*w/1440),round(y+button.rect.centery*h/900))
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN,pos=point,button=1))
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP,pos=point,button=1))
    for event in pygame.event.get():game.handle(event)


def solve(game):
    game.update(game.session.preview_duration-game.session.phase_elapsed)
    assert game.session.phase=='recall'
    answer=list(game.session.expected)
    if game.session.style=='pattern':answer.reverse()
    for tile in answer:
        game.update(.16)
        click(game,('tile',tile))
    assert game.session.phase=='feedback' and game.session.rounds_correct>0


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--screenshots',type=Path)
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    if args.screenshots:args.screenshots.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as directory:
        game=Game(directory)
        def screenshot(label):
            game.render()
            if args.screenshots:pygame.image.save(game.ui.surface,str(args.screenshots/(label+'.png')))
        screenshot('home');click(game,'settings');screenshot('settings')
        click(game,'profiles');click(game,'edit')
        game.handle(pygame.event.Event(pygame.TEXTINPUT,text='QA Profile'))
        game.handle(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN,mod=0))
        assert game.store.active=='QA Profile';screenshot('profiles')
        for mode in MODES:
            game.show('home');game.mode=mode;click(game,'start')
            assert game.screen=='countdown';game.update(3.01);assert game.screen=='play'
            game.update(.5);screenshot(mode+'-preview')
            if mode=='practice':
                game.update(game.session.preview_duration-game.session.phase_elapsed)
                pattern=list(game.session.pattern);click(game,'hint')
                assert game.session.pattern==pattern and game.session.hints==1
            solve(game);screenshot(mode+'-feedback')
            click(game,'pause');before=game.session.summary(),game.session.phase_elapsed
            game.update(10);assert before==(game.session.summary(),game.session.phase_elapsed)
            screenshot('paused');click(game,'resume');assert game.screen=='play'
            click(game,'pause');click(game,'end');assert game.screen=='results'
            screenshot('results');click(game,'restart');assert game.screen=='countdown' and game.session.score==0
        game.show('home');click(game,'daily');assert game.session.daily
        game.update(3.01);solve(game);game.update(60)
        assert game.screen=='results' and game.result['reason']=='Time is up'
        screenshot('daily-results')
        game.show('statistics');screenshot('history')
        game.act(('tab','Personal bests'));screenshot('bests')
        game.act(('tab','Achievements'));screenshot('achievements')
        game.act(('tab','Legacy v1'));click(game,'import')
        assert game.store.current['legacy_scores']=={'Hard':3,'Medium':2,'Easy':1}
        screenshot('legacy');click(game,'export');assert list((Path(directory)/'exports').glob('*.csv'))
        game.show('help');screenshot('help')
        game.toggle_fullscreen();assert game.fullscreen;game.toggle_fullscreen();assert not game.fullscreen
        game.handle(pygame.event.Event(pygame.VIDEORESIZE,w=1000,h=800))
        x,y,w,h=game.viewport
        assert game.map_point((x+w/2,y+h/2))==(720,450)
        assert game.map_point((500,10)) is None
        # Measure CPU simulation/drawing/scaling without frame-cap waiting.
        game.mode='practice';game.settings.grid=8;game.settings.length=12
        game.start();game.update(3.01)
        times=[]
        for i in range(360):
            start=time.perf_counter();game.update(1/120);game.render()
            if i>=60:times.append((time.perf_counter()-start)*1000)
        times.sort()
        result={'status':'passed','python':sys.version.split()[0],'pygame':pygame.version.ver,
                'sdl':'.'.join(map(str,pygame.get_sdl_version())),'video_driver':pygame.display.get_driver(),
                'modes':list(MODES),'saved_sessions':len(game.store.sessions),
                'checks':['real posted menu/tile events','five modes solved','hint replay','pause freeze',
                          'restart','daily completion','profiles','history','bests','achievements','legacy import',
                          'CSV export','fullscreen roundtrip','letterboxed input','public run-loop quit'],
                'audio_backend_available':bool(game.audio and game.audio.available),
                'renderer':{'samples':len(times),'grid':[8,8],'logical_canvas':[1440,900],'window':[1000,800],
                            'median_update_render_ms':round(statistics.median(times),3),
                            'p95_update_render_ms':round(times[int(.95*len(times))-1],3),
                            'scope':'SDL dummy backend; excludes frame-cap sleep. Not physical-display FPS or input latency.'}}
        pygame.event.post(pygame.event.Event(pygame.QUIT));game.run()
        assert not game.running
        print(json.dumps(result,indent=2))
        if args.report:args.report.write_text(json.dumps(result,indent=2))


if __name__=='__main__':main()
