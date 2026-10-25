import csv
import json
import pytest
from memtrix.model import Session, Settings
from memtrix.storage import Store,normalize_legacy


def row():
    s=Session(seed=1);s.score=100;s.finish('Out of lives');return s.summary()


def test_profile_settings_and_history_roundtrip(tmp_path):
    s=Store(tmp_path);s.create('Monika');s.set_settings(Settings(difficulty='Hard'));s.add(row())
    loaded=Store(tmp_path)
    assert loaded.active=='Monika' and loaded.settings.difficulty=='Hard' and len(loaded.sessions)==1
    loaded.select('Player');assert loaded.sessions==[] and loaded.settings.difficulty=='Medium'


@pytest.mark.parametrize('name',['','  ','x'*25,'Player','pLaYeR'])
def test_invalid_or_duplicate_names(tmp_path,name):
    with pytest.raises(ValueError):Store(tmp_path).create(name)


def test_profile_limit(tmp_path):
    s=Store(tmp_path)
    for i in range(19):s.create(f'Player {i}')
    with pytest.raises(ValueError):s.create('Extra')


def test_bests_separate_modes_difficulty_and_early_or_assisted(tmp_path):
    s=Store(tmp_path);s.add(row());s.add({**row(),'score':200})
    s.add({**row(),'mode':'reverse','score':300})
    s.add({**row(),'score':999,'reason':'Ended early'})
    s.add({**row(),'score':9999,'assisted':True})
    assert sorted(r['score'] for r in s.bests())==[200,300]


def test_csv_bom_and_formula_protection(tmp_path):
    s=Store(tmp_path);s.add({**row(),'reason':'=1+1'});path=s.export()
    assert path.read_bytes().startswith(b'\xef\xbb\xbf')
    with path.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    assert rows[0]['reason']=="'=1+1"


@pytest.mark.parametrize('bad',['{broken','[]','{"schema":999}','{"schema":2,"profiles":{}}'])
def test_recovery_preserves_bytes(tmp_path,bad):
    (tmp_path/'progress.json').write_text(bad);s=Store(tmp_path)
    assert s.active=='Player' and s.notice
    assert list(tmp_path.glob('progress-recovery-*.json'))[0].read_text()==bad
    assert s.save() and Store(tmp_path).active=='Player'


@pytest.mark.parametrize('key,value',[('score','bad'),('duration',[]),('difficulty',{}),('mode',[]),('selections',{}),('date','bad'),('average_recall_ms','bad')])
def test_malformed_records_are_skipped(tmp_path,key,value):
    s=Store(tmp_path);s.add(row());data=json.loads(s.path.read_text())
    data['profiles']['Player']['sessions'][0][key]=value;s.path.write_text(json.dumps(data))
    assert Store(tmp_path).sessions==[]


def test_write_failure_keeps_memory_and_cleans_temporary(tmp_path,monkeypatch):
    s=Store(tmp_path)
    def fail(*a):raise PermissionError('denied')
    monkeypatch.setattr('memtrix.storage.os.replace',fail)
    _,_,saved=s.add(row())
    assert not saved and len(s.sessions)==1 and s.notice and not list(tmp_path.glob('*.tmp'))


def test_history_limit(tmp_path):
    s=Store(tmp_path);s.current['sessions']=[row() for _ in range(1000)];s.add(row())
    assert len(s.sessions)==1000


def test_legacy_case_normalization_and_import_is_separate(tmp_path):
    source=tmp_path/'old.json';source.write_text(json.dumps({'Hard':3,'medium':2,'easy':1,'HARD':5,'bad':100}))
    s=Store(tmp_path/'new');assert s.import_legacy(source)
    assert s.current['legacy_scores']=={'Hard':5,'Medium':2,'Easy':1}
    assert s.sessions==[] and s.bests()==[]
    assert Store(tmp_path/'new').current['legacy_scores']['Hard']==5


@pytest.mark.parametrize('raw',[[],{}, {'easy':True},{'easy':-1},{'easy':'100'}])
def test_invalid_legacy_scores_rejected(raw):
    with pytest.raises(ValueError):normalize_legacy(raw)
