from dataclasses import asdict
from datetime import date
import pytest
from memtrix.model import Session, Settings, MODES, RULES, daily_seed, board_key, eligible, achievements


def recall(session):
    session.update(session.preview_duration-session.phase_elapsed)
    assert session.phase=='recall'


def solve(session):
    recall(session)
    for tile in list(session.expected):
        session.update(.05);assert session.select(tile)
    assert session.phase=='feedback'


@pytest.mark.parametrize('mode',MODES)
def test_modes_create_and_round_can_be_solved(mode):
    s=Session(mode,seed=1);solve(s)
    assert s.rounds_correct==1 and s.accuracy==100 and s.score>=s.length*100


def test_reverse_demands_reverse_order():
    s=Session('reverse',seed=1);recall(s)
    assert s.expected==s.pattern[::-1]
    assert s.select(s.pattern[0]) is False
    assert s.mistakes==1 and s.phase=='feedback'


def test_pattern_recall_accepts_any_order():
    s=Session('pattern',seed=3);recall(s)
    for tile in s.pattern[::-1]:assert s.select(tile)
    assert s.rounds_correct==1


def test_wrong_order_correct_location_is_immediately_wrong():
    s=Session(seed=2);recall(s)
    assert s.select(s.pattern[1]) is False
    assert s.wrong_tile==s.pattern[1] and s.correct_selections==0


def test_wrong_location_is_rejected():
    s=Session('pattern',seed=4);recall(s)
    wrong=next(i for i in range(s.grid*s.grid) if i not in s.pattern)
    assert s.select(wrong) is False and s.lives==1


def test_preview_nonleft_outside_and_duplicate_selections_are_ignored():
    s=Session(seed=1)
    assert s.select(s.pattern[0]) is None
    recall(s)
    for tile,button in [(None,1),(-1,1),(999,1),(True,1),(s.pattern[0],3)]:assert s.select(tile,button) is None
    first=s.expected[0];assert s.select(first)
    assert s.select(first) is None and s.selections==1


def test_fast_legitimate_clicks_have_no_global_debounce():
    s=Session(seed=1);recall(s)
    for tile in list(s.expected):assert s.select(tile)
    assert s.rounds_correct==1


@pytest.mark.parametrize('difficulty',RULES)
def test_life_limits_and_gameover_after_feedback(difficulty):
    s=Session(settings=Settings(difficulty=difficulty),seed=2)
    for _ in range(RULES[difficulty]['lives']):
        recall(s);s.select(s.pattern[1]);assert s.phase=='feedback';s.update(.9)
    assert s.finished and s.lives==0 and s.reason=='Out of lives'


def test_timeouts_are_separate_from_wrong_clicks():
    s=Session(seed=1);recall(s);s.update(s.recall_limit)
    assert s.timeouts==1 and s.mistakes==0 and s.rounds_failed==1 and s.lives==1


def test_practice_is_untimed_and_replay_preserves_pattern():
    s=Session('practice',seed=1);recall(s);s.update(1000)
    original=list(s.pattern);assert s.select(original[0])
    assert s.hint() and s.pattern==original and s.selected==[] and s.hints==1
    recall(s);assert not s.finished and s.lives is None and s.assisted


@pytest.mark.parametrize('mode',['classic','pattern','reverse','time_attack'])
def test_competitive_modes_cannot_use_hint(mode):
    s=Session(mode,seed=1);recall(s);assert not s.hint() and not s.assisted


def test_long_sequence_has_no_five_second_cutoff():
    s=Session('practice',Settings(grid=6,length=12,playback='Slow'),seed=3)
    observed=set()
    for _ in range(int(s.preview_duration*100)):
        observed|=s.lit_tiles();s.update(.01)
    assert observed==set(s.pattern)
    s.update(.02);assert s.phase=='recall'


def test_pattern_preview_blanks_before_recall():
    s=Session('pattern',seed=1);s.update(.5)
    assert s.lit_tiles()==set(s.pattern)
    recall(s);assert s.lit_tiles()==set()


def test_grid_and_sequence_caps_are_enforced():
    s=Session(seed=1)
    for _ in range(35):solve(s);s.update(.9)
    assert s.grid==6 and s.length==20 and not s.finished
    assert len(set(s.pattern))==20 and all(0<=x<36 for x in s.pattern)


def test_practice_length_clamps_to_board_capacity():
    s=Session('practice',Settings(grid=3,length=12),seed=2)
    assert s.length==9


def test_progressive_grid_grows_every_three_rounds():
    s=Session(settings=Settings(difficulty='Easy'),seed=1)
    for _ in range(3):solve(s);s.update(.9)
    assert s.grid==4 and s.length==6


def test_seed_is_repeatable():
    a,b=Session(seed=8),Session(seed=8)
    assert a.pattern==b.pattern
    solve(a);solve(b);a.update(.9);b.update(.9)
    assert a.pattern==b.pattern


@pytest.mark.parametrize('fps',[30,60,120,144,240])
def test_playback_and_timing_are_frame_rate_independent(fps):
    a,b=Session('practice',seed=7),Session('practice',seed=7)
    for _ in range(fps*8):a.update(1/fps)
    b.update(8)
    assert a.phase==b.phase and a.elapsed==pytest.approx(b.elapsed) and a.phase_elapsed==pytest.approx(b.phase_elapsed)


@pytest.mark.parametrize('duration',[60,90,120])
def test_time_attack_counts_all_active_phases(duration):
    s=Session('time_attack',Settings(duration=duration),seed=1)
    s.update(duration+10)
    assert s.finished and s.elapsed==duration and s.reason=='Time is up' and s.lives is None


def test_daily_fixes_gameplay_settings_and_date_seed():
    s=Session('practice',Settings(difficulty='Hard',duration=120),daily=True,seed=4)
    assert (s.mode,s.settings.difficulty,s.duration,s.seed)==('time_attack','Medium',60,4)
    assert daily_seed(date(2026,10,25))==daily_seed(date(2026,10,25))
    assert daily_seed(date(2026,10,25))!=daily_seed(date(2026,10,26))


def test_scoring_only_rewards_completed_rounds_and_resets_streak():
    s=Session(seed=1);recall(s);s.update(1);s.select(s.expected[0])
    assert s.score==0
    for tile in list(s.expected)[1:]:s.select(tile)
    assert s.score==400+round(100*(1-1/(14+4*1.2)))
    assert s.streak==1 and s.summary()['average_recall_ms']==1000
    s.update(.9);recall(s);s.select(s.pattern[1]);assert s.streak==0


def test_practice_settings_do_not_modify_competitive_playback():
    a=Session(settings=Settings(playback='Slow',grid=8,length=12),seed=1)
    b=Session(settings=Settings(),seed=1)
    assert (a.grid,a.length,a.flash,a.gap)==(b.grid,b.length,b.flash,b.gap)


@pytest.mark.parametrize('dt',[-1,float('nan'),float('inf')])
def test_bad_dt_is_ignored(dt):
    s=Session(seed=1);s.update(dt);assert s.elapsed==0


@pytest.mark.parametrize('data',[None,[],{'grid':True},{'volume':'50'},{'difficulty':'Bad'}])
def test_invalid_settings_fall_back(data):
    assert Settings.from_dict(data)==Settings()


def test_settings_roundtrip():
    s=Settings(grid=8,length=12,playback='Fast',theme='High contrast',volume=0)
    assert Settings.from_dict(asdict(s))==s


def test_bests_require_unassisted_natural_finish():
    r=Session().summary();r.update(score=100,reason='Out of lives')
    assert eligible(r)
    assert not eligible({**r,'assisted':True}) and not eligible({**r,'reason':'Ended early'})
    assert board_key(r)!=board_key({**r,'difficulty':'Hard'})
    assert board_key(r)!=board_key({**r,'daily':True,'challenge_date':'2026-10-25'})


def test_achievement_evidence():
    row={'rounds_correct':5,'longest':7,'selections':30,'accuracy':95,'mode':'reverse','best_streak':5,'daily':True,'reason':'Time is up'}
    assert set(['first','sequence','accurate','reverse','daily','streak'])<=achievements([row])
    assert 'regular' in achievements([row]*10)
