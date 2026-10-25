import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame
import pytest
from memtrix.app import Game


@pytest.fixture
def game(tmp_path):
    g=Game(tmp_path,silent=True)
    yield g
    pygame.quit()


def key(g,value):g.handle(pygame.event.Event(pygame.KEYDOWN,key=value,mod=0))


def begin(g,mode='classic'):
    g.mode=mode;g.start();g.update(3.1);assert g.screen=='play';g.render()


@pytest.mark.parametrize('phase',['preview','recall','feedback'])
def test_pause_freezes_every_phase_and_timer(game,phase):
    begin(game)
    if phase in ('recall','feedback'):game.session.update(game.session.preview_duration)
    if phase=='feedback':
        for tile in list(game.session.expected):game.session.select(tile)
    key(game,pygame.K_ESCAPE);before=game.session.summary(),game.session.phase,game.session.phase_elapsed
    game.update(100)
    assert (game.session.summary(),game.session.phase,game.session.phase_elapsed)==before
    key(game,pygame.K_ESCAPE);assert game.screen=='play'


def test_focus_loss_and_countdown_require_explicit_resume(game):
    game.start();game.handle(pygame.event.Event(pygame.WINDOWFOCUSLOST));assert game.screen=='ready'
    key(game,pygame.K_RETURN);game.update(3.1);assert game.screen=='play'
    game.handle(pygame.event.Event(pygame.WINDOWFOCUSLOST));assert game.screen=='paused'


@pytest.mark.parametrize('grid',[3,4,5,6,8])
def test_all_practice_boards_fit_without_overlap(game,grid):
    game.settings.grid=grid;begin(game,'practice');rects=game.board_rects()
    bounds=pygame.Rect(60,171,922,649)
    assert all(bounds.contains(r) for r in rects)
    for i,r in enumerate(rects):assert not any(r.colliderect(o) for o in rects[i+1:])


def test_resized_click_uses_event_position_and_ignores_right_button(game):
    game.handle(pygame.event.Event(pygame.VIDEORESIZE,w=1000,h=800));begin(game)
    game.session.update(game.session.preview_duration);game.render()
    tile=game.session.expected[0];rect=game.board_rects()[tile];x,y,w,h=game.viewport
    pos=(round(x+rect.centerx*w/1440),round(y+rect.centery*h/900))
    game.pointer=(0,0)
    game.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN,pos=pos,button=3));assert game.session.selections==0
    game.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN,pos=pos,button=1));assert game.session.correct_selections==1
    assert game.map_point((500,10)) is None


def test_results_saved_once_and_restart_resets(game):
    begin(game);game.session.finish();game.update(.01)
    assert game.screen=='results' and len(game.store.sessions)==1
    game.finish();assert len(game.store.sessions)==1
    game.render();assert any(b.action=='restart' for b in game.ui.buttons)
    key(game,pygame.K_r);assert game.screen=='countdown' and game.session.elapsed==0


def test_keyboard_profiles_and_back_do_not_start_game(game):
    game.show('settings');key(game,pygame.K_ESCAPE);assert game.screen=='home' and game.session is None
    key(game,pygame.K_TAB);assert game.focus==0
    game.show('profiles');game.act('edit');game.handle(pygame.event.Event(pygame.TEXTINPUT,text='Monika'))
    key(game,pygame.K_RETURN);assert game.store.active=='Monika'


@pytest.mark.parametrize('screen',['home','settings','profiles','statistics','help'])
def test_menu_buttons_in_bounds(game,screen):
    game.show(screen);game.render();assert game.ui.buttons
    assert all(pygame.Rect(0,0,1440,900).contains(b.rect) for b in game.ui.buttons)


def test_fullscreen_roundtrip(game):
    before=game.window.get_size();game.toggle_fullscreen();assert game.fullscreen
    game.toggle_fullscreen();assert not game.fullscreen and game.window.get_size()==before


def test_audio_failure_nonfatal(tmp_path,monkeypatch):
    def fail(*a,**k):raise pygame.error('no device')
    monkeypatch.setattr(pygame.mixer,'init',fail);g=Game(tmp_path)
    assert not g.audio.available and g.running;pygame.quit()


def test_practice_hint_is_marked_assisted(game):
    begin(game,'practice');game.session.update(game.session.preview_duration);key(game,pygame.K_h)
    assert game.session.hints==1 and game.session.phase=='preview' and game.session.assisted


def test_quit_event_exits_instead_of_starting(game):
    game.show('settings');game.handle(pygame.event.Event(pygame.QUIT))
    assert not game.running and game.session is None
