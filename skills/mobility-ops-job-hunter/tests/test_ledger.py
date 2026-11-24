"""ledger.py v1.2.1 회귀 테스트 (임시 데이터만 사용, 실제 채용시장 조사 없음).

실행: python -m unittest discover -s tests   (스킬 폴더에서)
"""
import contextlib
import copy
import datetime as dt
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'scripts'))
import ledger as LG  # noqa: E402

C = LG.find_contract()
KST = dt.timezone(dt.timedelta(hours=9))
COMPANY = [c['id'] for c in C['channels'] if c['scope'] == 'company']


class Clock:
    def __init__(self, start=dt.datetime(2026, 11, 23, 9, 0, tzinfo=KST)):
        self.t = start

    def tick(self, minutes=1):
        self.t += dt.timedelta(minutes=minutes)
        os.environ['MOJH_NOW'] = self.t.isoformat()


def run(*args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = LG.main(list(args))
        except SystemExit as e:
            code = e.code
    return code, out.getvalue() + err.getvalue()


EV = {'method': 'browser', 'evidence': '화면 문구: 채용 공고 목록 3건', 'classified_by': 'manual'}
BASELINE = [
    {'target_id': 'T0001', 'type_id': '01', 'candidate_id': '01-01', 'url': 'https://old.example.com/careers',
     'kind': 'company_page', 'source_sheets': ['t'], 'assign_reason': '', 'assigned_by': 'candidate_id'},
    {'target_id': 'T0002', 'type_id': '02', 'candidate_id': '02-01', 'url': 'https://old.example.com/job/1',
     'kind': 'job_posting', 'source_sheets': ['t'], 'assign_reason': '', 'assigned_by': 'candidate_id'},
    {'target_id': 'T0003', 'type_id': '00', 'candidate_id': None, 'url': 'https://other.example.com/job/9',
     'kind': 'job_posting', 'source_sheets': ['t'], 'assign_reason': '비모빌리티 공고', 'assigned_by': 'manual'},
]


def job(**k):
    d = {'job_key': 'J-02-1', 'title': '운영 데이터 분석', 'hiring_entity': '쏘카', 'poster_entity': '쏘카',
         'poster_relation': 'direct', 'location': '서울', 'career': '신입~3년', 'employment_type': '정규직',
         'deadline': '2026-12-10', 'fit_score': 82, 'fit_reason': '운영 KPI 분석 수행', 'condition_fit': 'match',
         'url': 'https://old.example.com/job/1', 'status': 'open_verified',
         'sources': [{'url': 'https://old.example.com/job/1', 'platform': 'official', 'status_seen': 'open'}],
         'open_evidence': {'url': 'https://old.example.com/job/1', 'kind': 'deadline_date', 'quote': '접수기간 ~ 2026.12.10'}}
    d.update(k)
    return d


def write(tmp, name, recs):
    f = Path(tmp) / name
    f.write_text('\n'.join(json.dumps(r, ensure_ascii=False) for r in recs), encoding='utf-8')
    return str(f)


def run_types(path, tmp, clock, stop_before=None):
    """유형 01→10을 정상 절차(5분 이상, 기록 3회 이상)로 진행한다."""
    for t in C['types']:
        tid = t['type_id']
        clock.tick()
        code, out = run('start-type', path, tid)
        assert code == 0, out
        L = LG.load(path)
        cands = [c for c in L['candidates'] if c['type_id'] == tid]
        b1 = [{'kind': 'candidate', 'id': c['id'], 'relation_status': 'verified', 'resolved_company_id': 'CO-' + c['id'],
               'relation_evidence_url': 'https://example.com/r/' + c['id']}
              for c in cands if c['relation_status'] != 'verified_cached']
        synthetic = L['baseline']['source_file'] is None
        if synthetic and tid == '01':
            b1.append(dict(EV, kind='revisit', target_id='T0001', result='ok', final_url='https://old.example.com/careers',
                           relevant_found=0))
        if synthetic and tid == '02':
            b1 += [dict(EV, kind='revisit', target_id='T0002', result='ok', final_url='https://old.example.com/job/1',
                        relevant_found=1),
                   {'kind': 'discovered', 'disc_id': 'D-1', 'url': 'https://old.example.com/job/1', 'title': '운영 데이터 분석',
                    'relevant': True, 'found_via': 'revisit:T0002'},
                   dict(job(), kind='job'),
                   {'kind': 'decision', 'disc_id': 'D-1', 'outcome': 'job', 'job_key': 'J-02-1', 'classified_by': 'manual'}]
        for tg in L['baseline']['targets']:
            if tg['type_id'] != tid or (synthetic and tg['target_id'] in ('T0001', 'T0002')):
                continue
            if tg['kind'] != 'job_posting':
                b1.append(dict(EV, kind='revisit', target_id=tg['target_id'], result='ok', final_url=tg['url'],
                               relevant_found=0))
                continue
            b1.append(dict(EV, kind='revisit', target_id=tg['target_id'], result='closed', final_url=tg['url'],
                           relevant_found=0))
            b1 += [{'kind': 'discovered', 'disc_id': 'D-' + tg['target_id'], 'url': tg['url'], 'title': 'x',
                    'relevant': True, 'found_via': 'revisit:' + tg['target_id']},
                   {'kind': 'decision', 'disc_id': 'D-' + tg['target_id'], 'outcome': 'excluded',
                    'reason_code': 'closed', 'reason': '접수 마감 표시', 'classified_by': 'manual'}]
        bs = [dict(EV, kind='search', search_id='S-' + p['task_id'], task_id=p['task_id'], candidate_id=p['candidate_id'],
                   channel_id=p['channel_id'], query=p['suggested_query'], results_reviewed=10, relevant_found=0)
              for p in L['discovery_plan'] if p['type_id'] == tid]
        b3 = [dict(EV, kind='channel', candidate_id=c['id'], channel_id=ch, status='searched_no_match',
                   query=f'{c["brand_name"]} {ch}', note='관련 공고 없음')
              for c in cands if c['origin'] == 'contract' for ch in COMPANY]
        b2, b2b = bs[:len(bs) // 2], bs[len(bs) // 2:]
        for i, b in enumerate((b1, b2, b2b, b3)):
            clock.tick(2)
            if b:
                code, out = run('add', path, '--file', write(tmp, f'{tid}-{i}.jsonl', b))
                assert code == 0, out
        if stop_before and stop_before(tid):
            return path
        clock.tick()
        code, out = run('finish-type', path, tid)
        assert code == 0, out
    return path


def build_complete(tmp, clock, **kw):
    path = str(Path(tmp) / 'ledger.json')
    clock.tick()
    assert run('init', path)[0] == 0
    L = LG.load(path)
    L['baseline']['targets'] = copy.deepcopy(BASELINE)
    LG.save(path, L)
    return run_types(path, tmp, clock, **kw)


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.clock = Clock()
        cls.path = build_complete(cls.tmp, cls.clock)
        cls.L = LG.load(cls.path)

    def ev(self, L):
        return LG.evaluate(L, C, at_time=self.clock.t)

    def start(self, L, tid):
        return next(t for t in L['types'] if t['type_id'] == tid)['started_at']

    def ch(self, L, cid, ch):
        return next(x for x in L['channels'] if x['candidate_id'] == cid and x['channel_id'] == ch)

    def assertType(self, rep, tid, status, contains=None):
        r = rep['types'][tid]
        self.assertEqual(r['status'], status, r['not_done'][:5] + r['partial'][:5])
        if contains:
            self.assertTrue(any(contains in x for x in r['not_done'] + r['partial'] + r['unresolved']),
                            r['not_done'][:8] + r['partial'] + r['unresolved'])


class TestScenarios(Base):
    def test_0_complete(self):
        rep = self.ev(self.L)
        self.assertEqual(rep['verdict'], 'COMPLETE', rep['errors'] + [x for r in rep['types'].values() for x in r['not_done'][:3]])
        self.assertEqual(run('audit', self.path)[0], 0)

    def test_768_cells_filled_by_scope(self):
        from collections import Counter
        st = Counter(x['status'] for x in self.L['channels'])
        self.assertEqual(sum(st.values()), 768)
        self.assertEqual(st['covered_by_type_search'], 64 * 6)
        self.assertEqual(st['covered_by_entity_search'], 64 * 2)
        self.assertEqual(st['searched_no_match'], 64 * 4)

    def test_A_no_revisit(self):
        L = copy.deepcopy(self.L); L['revisits'] = []
        rep = self.ev(L)
        self.assertType(rep, '01', 'not_done', '재방문 누락 T0001')
        self.assertType(rep, '02', 'not_done', '재방문 누락 T0002')

    def test_A_stale_dates(self):
        L = copy.deepcopy(self.L)
        self.ch(L, '01-01', 'official')['at'] = '2026-11-17T21:00:00+09:00'
        self.assertType(self.ev(L), '01', 'not_done', '작업 구간 밖')

    def test_B_skip_keyword_search(self):
        L = copy.deepcopy(self.L)
        L['searches'] = [s for s in L['searches'] if not s['task_id'].startswith('U-03-')]
        for x in L['channels']:
            if x['type_id'] == '03' and x['status'] == 'covered_by_type_search':
                x['status'] = 'unsearched'
        rep = self.ev(L)
        self.assertType(rep, '03', 'not_done', '발굴 검색 미실시 U-03-1-web')
        self.assertType(rep, '03', 'not_done', '채널 미실시 03-01/linkedin')
        self.assertEqual(rep['types']['04']['status'], 'complete')

    def test_B_skip_entity(self):
        L = copy.deepcopy(self.L)
        L['searches'] = [s for s in L['searches'] if s['task_id'] != 'E-03-02']
        self.assertType(self.ev(L), '03', 'not_done', 'E-03-02')

    def test_C_agency_as_hiring_entity(self):
        L = copy.deepcopy(self.L)
        L['jobs'][0].update(poster_relation='agency', poster_entity='OO아웃소싱', hiring_entity='OO아웃소싱')
        self.assertType(self.ev(L), '02', 'not_done', '위탁·대행')

    def test_C_shallow_results(self):
        L = copy.deepcopy(self.L)
        next(s for s in L['searches'] if s['task_id'] == 'E-02-01')['results_reviewed'] = 3
        self.assertIn('유형 02: complete로 기록됐으나 산정 결과 partial', self.ev(L)['errors'])

    def test_D_seen_but_not_registered(self):
        L = copy.deepcopy(self.L)
        self.ch(L, '02-01', 'official').update(status='page_checked', url='https://socar.example.com/careers', relevant_found=1)
        self.assertType(self.ev(L), '02', 'not_done', '관련 공고 1건 확인했으나 발견 목록 등록 0건')

    def test_D_registered_not_decided(self):
        L = copy.deepcopy(self.L)
        L['discovered'].append({'disc_id': 'D-9', 'type_id': '02', 'url': 'https://x.example.com/9', 'relevant': True,
                                'found_via': 'search:S-E-02-01', 'at': self.start(L, '02')})
        self.assertType(self.ev(L), '02', 'not_done', '최종 판정 0건')

    def test_D_revisited_posting_not_judged(self):
        L = copy.deepcopy(self.L)
        L['discovered'] = [d for d in L['discovered'] if d['disc_id'] != 'D-1']
        L['decisions'] = [d for d in L['decisions'] if d['disc_id'] != 'D-1']
        self.assertType(self.ev(L), '02', 'not_done', '재확인 대상 공고 T0002')

    def test_E_duplicate_rows(self):
        L = copy.deepcopy(self.L)
        L['jobs'].append(copy.deepcopy(L['jobs'][0]))
        self.assertIn('job_key 중복 J-02-1', self.ev(L)['errors'])

    def test_E_conflict(self):
        L = copy.deepcopy(self.L)
        L['jobs'][0]['sources'] = [{'url': 'https://old.example.com/job/1', 'status_seen': 'closed'},
                                   {'url': 'https://wanted.example.com/1', 'status_seen': 'always_open'}]
        L['jobs'][0]['open_evidence'] = {'url': 'https://wanted.example.com/1', 'kind': 'always_open_label', 'quote': '상시채용'}
        self.assertType(self.ev(L), '02', 'not_done', '충돌')
        L['jobs'][0].update(status='unknown_conflict', open_evidence=None)
        self.assertType(self.ev(L), '02', 'complete', '접수 불명')

    def test_E_open_without_evidence_or_past_deadline(self):
        L = copy.deepcopy(self.L)
        L['jobs'][0]['open_evidence'] = None
        self.assertType(self.ev(L), '02', 'not_done', '모집 중 근거')
        L = copy.deepcopy(self.L)
        L['jobs'][0]['deadline'] = '2026-11-20'
        self.assertType(self.ev(L), '02', 'not_done', '지남')

    def test_F_blocked(self):
        L = copy.deepcopy(self.L)
        x = self.ch(L, '02-01', 'wanted')
        x.update(status='access_blocked', evidence='(403) Forbidden 오류 화면', alternative_url='https://saramin.example.com/1')
        self.assertType(self.ev(L), '02', 'complete')
        x['alternative_url'] = ''
        self.assertEqual(self.ev(L)['verdict'], 'FAIL')  # complete로 기록돼 있으므로 과대보고
        next(t for t in L['types'] if t['type_id'] == '02').update(status='partial', partial_reason='원티드 403, 대체 원문 없음')
        rep = self.ev(L)
        self.assertEqual(rep['verdict'], 'PARTIAL')

    def test_G_zero_found(self):
        r = self.ev(self.L)['types']['03']
        self.assertTrue(r['zero_found'])
        self.assertEqual(r['status'], 'complete')

    def test_H_one_channel_unsearched(self):
        L = copy.deepcopy(self.L)
        self.ch(L, '05-01', 'official')['status'] = 'unsearched'
        rep = self.ev(L)
        self.assertType(rep, '05', 'not_done', '채널 미실시 05-01/official')
        self.assertEqual(sum(r['status'] == 'complete' for r in rep['types'].values()), 9)

    def test_I_overlap_order(self):
        L = copy.deepcopy(self.L)
        t1 = next(t for t in L['types'] if t['type_id'] == '01')
        t2 = next(t for t in L['types'] if t['type_id'] == '02')
        t1['finished_at'] = (LG.ts(t2['started_at']) + dt.timedelta(minutes=1)).isoformat()
        self.assertTrue(any('순서 위반' in e for e in self.ev(L)['errors']))

    # ---- v1.2.1 신규
    def test_batch_recording_detected(self):
        L = copy.deepcopy(self.L)
        t = next(t for t in L['types'] if t['type_id'] == '04')
        s = LG.ts(t['started_at'])
        t['finished_at'] = (s + dt.timedelta(seconds=30)).isoformat()
        for k in ('candidates', 'channels', 'searches'):
            for r in L[k]:
                if r.get('type_id') == '04' and r.get('at'):
                    r['at'] = (s + dt.timedelta(seconds=5)).isoformat()
        self.assertType(self.ev(L), '04', 'not_done', '사후 일괄 기록 의심')

    def test_evidence_required(self):
        L = copy.deepcopy(self.L)
        self.ch(L, '06-01', 'saramin').pop('method')
        self.assertType(self.ev(L), '06', 'not_done', 'method')
        L = copy.deepcopy(self.L)
        self.ch(L, '06-01', 'saramin')['evidence'] = ''
        self.assertType(self.ev(L), '06', 'not_done', 'evidence')

    def test_code_decisions_need_spotcheck(self):
        L = copy.deepcopy(self.L)
        L['decisions'][0]['classified_by'] = 'code'
        self.assertType(self.ev(L), '02', 'not_done', '표본 대조 0/1')
        L['spotchecks'].append({'type_id': '02', 'disc_id': 'D-1', 'agrees': True, 'evidence': '원문 접수기간 12/10 확인',
                                'at': self.start(L, '02')})
        self.assertType(self.ev(L), '02', 'complete')
        L['spotchecks'][-1]['agrees'] = False
        self.assertType(self.ev(L), '02', 'complete', '표본 대조 불일치')

    def test_shared_channel(self):
        L = copy.deepcopy(self.L)
        for cid in ('03-01', '04-03'):
            next(c for c in L['candidates'] if c['id'] == cid)['resolved_company_id'] = 'kakaomobility'
        self.ch(L, '04-03', 'wanted').update(status='shared', shared_from='03-01')
        self.assertType(self.ev(L), '04', 'complete')
        next(c for c in L['candidates'] if c['id'] == '04-03')['resolved_company_id'] = 'other'
        self.assertType(self.ev(L), '04', 'not_done', 'shared_from')

    def test_new_company_without_route(self):
        L = copy.deepcopy(self.L)
        L['candidates'].append({'id': 'N-02-1', 'type_id': '02', 'brand_name': '신규카셰어', 'origin': 'discovered',
                                'relation_status': 'verified', 'resolved_company_id': 'CO-N', 'discovered_by': 'S-U-02-1-web',
                                'relation_evidence_url': 'https://n.example.com', 'at': self.start(L, '02')})
        self.assertType(self.ev(L), '02', 'not_done', '신규 후보 N-02-1: 채용 경로 기록 없음')

    def test_names_keep_short(self):
        L = self.L
        names = {c['id']: LG.match_names(c) for c in L['candidates']}
        self.assertIn('쏘카', names['02-01'])
        self.assertIn('모빈', names['10-04'])
        self.assertIn('타다', names['03-03'])
        self.assertIn('GCOO', names['01-02'])

    def test_report(self):
        out = Path(self.tmp) / 'report.md'
        self.assertEqual(run('report', self.path, str(out))[0], 0)
        text = out.read_text(encoding='utf-8')
        for s in ('휴대폰 요약', '유형별 상태', '공고 목록', '쏘카', '확인 방법', '법인 등록부', '(0건)'):
            self.assertIn(s, text)

    def test_registry_written(self):
        reg = self.L['registry']
        self.assertEqual(len(reg), 64)
        self.assertEqual(reg['02-01']['verified_at'], '2026-11-23')


class TestRegistryAndCarryover(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.clock = Clock()
        cls.first = build_complete(cls.tmp, cls.clock)

    def test_second_run_reuses_registry(self):
        tmp = tempfile.mkdtemp()
        clock = Clock(dt.datetime(2026, 12, 1, 9, 0, tzinfo=KST))
        path = str(Path(tmp) / 'run2.json')
        clock.tick()
        code, out = run('init', path, '--baseline', self.first)
        self.assertEqual(code, 0, out)
        L = LG.load(path)
        self.assertEqual(sum(c['relation_status'] == 'verified_cached' for c in L['candidates']), 64)
        self.assertFalse([p for p in L['discovery_plan'] if p['kind'] == 'entity'])
        run_types(path, tmp, clock)
        L = LG.load(path)
        rep = LG.evaluate(L, C, at_time=clock.t)
        self.assertEqual(rep['verdict'], 'COMPLETE', [x for r in rep['types'].values() for x in r['not_done'][:3]])
        self.assertTrue(all(x['status'] != 'covered_by_entity_search' for x in L['channels']))
        self.assertEqual(sum(x['status'] == 'covered_by_registry' for x in L['channels']), 128)
        # 등록 경로가 사라지면 재확인 필요
        x = next(x for x in L['channels'] if x['candidate_id'] == '05-02' and x['channel_id'] == 'official')
        x.update(status='page_checked', url='https://gone.example.com', relevant_found=0, route_status='gone')
        rep = LG.evaluate(L, C, at_time=clock.t)
        self.assertTrue(any('법인 재확인 필요' in m for m in rep['types']['05']['not_done']))

    def test_registry_expiry(self):
        P = LG.load(self.first)
        for e in P['registry'].values():
            e['verified_at'] = '2026-04-01'
        p = Path(tempfile.mkdtemp()) / 'old.json'
        LG.save(p, P)
        path = str(p.parent / 'run.json')
        Clock().tick()
        self.assertEqual(run('init', path, '--baseline', str(p))[0], 0)
        L = LG.load(path)
        self.assertEqual(sum(c['relation_status'] == 'verified_cached' for c in L['candidates']), 0)
        self.assertEqual(len([p for p in L['discovery_plan'] if p['kind'] == 'entity']), 64)

    def test_carryover_from_v12_ledger(self):
        prev = {'candidates': [{'id': '02-01', 'type_id': '02', 'brand_name': '쏘카', 'origin': 'contract',
                                'relation_status': 'verified', 'resolved_company_id': 'socar',
                                'relation_evidence_url': 'https://socar.example.com/about', 'at': '2026-11-24T00:07:11+09:00'}],
                'channels': [{'candidate_id': '02-01', 'channel_id': 'saramin', 'status': 'page_checked',
                              'url': 'https://saramin.example.com/company/socar'}],
                'baseline': {'targets': [{'target_id': 'T0001', 'type_id': '02', 'url': 'https://a.example.com/blocked', 'kind': 'job_posting'},
                                         {'target_id': 'T0002', 'type_id': '02', 'url': 'https://a.example.com/closed', 'kind': 'job_posting'}]},
                'revisits': [{'target_id': 'T0001', 'result': 'blocked'}, {'target_id': 'T0002', 'result': 'closed'}],
                'discovered': [{'disc_id': 'D1', 'type_id': '02', 'url': 'https://a.example.com/undecided', 'relevant': True},
                               {'disc_id': 'D2', 'type_id': '02', 'url': 'https://a.example.com/dblock', 'relevant': True},
                               {'disc_id': 'D3', 'type_id': '02', 'url': 'https://a.example.com/excl', 'relevant': True}],
                'decisions': [{'disc_id': 'D2', 'outcome': 'excluded', 'reason_code': 'detail_blocked'},
                              {'disc_id': 'D3', 'outcome': 'excluded', 'reason_code': 'closed'}],
                'jobs': []}
        p = Path(tempfile.mkdtemp()) / 'prev.json'
        p.write_text(json.dumps(prev, ensure_ascii=False), encoding='utf-8')
        targets, _, reg, _ = LG.from_ledger(p, C)
        urls = {t['url'] for t in targets}
        self.assertEqual(urls, {'https://a.example.com/undecided', 'https://a.example.com/dblock', 'https://a.example.com/blocked'})
        self.assertEqual(reg['02-01']['routes']['saramin'], 'https://saramin.example.com/company/socar')
        self.assertEqual(reg['02-01']['verified_at'], '2026-11-24')


class TestFlow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.clock = Clock()
        self.path = str(Path(self.tmp) / 'l.json')
        self.clock.tick()
        run('init', self.path)

    def test_plan_turns(self):
        L = LG.load(self.path)
        flat = [t for turn in L['turn_plan'] for t in turn['types']]
        self.assertEqual(flat, [t['type_id'] for t in sorted(C['types'], key=lambda x: x['seq'])])
        self.assertGreater(len(L['turn_plan']), 1)
        code, out = run('plan', self.path, '--budget', '2000')
        self.assertEqual(len(LG.load(self.path)['turn_plan']), 1, out)

    def test_next_and_turn_stop_message(self):
        code, out = run('next', self.path)
        self.assertIn('start-type 01', out)
        tmp = tempfile.mkdtemp()
        clock = Clock()
        path = build_complete(tmp, clock, stop_before=lambda t: t == '01')
        L = LG.load(path)
        last = L['turn_plan'][0]['types'][-1]
        self.assertIn('현재 턴 1', run('next', path)[1])
        if last == '01':
            clock.tick()
            self.assertIn('턴 1 종료', run('finish-type', path, '01')[1])

    def test_order_enforced(self):
        self.clock.tick()
        code, out = run('start-type', self.path, '02')
        self.assertEqual(code, 2)
        self.assertIn('다음 순서 유형은 01', out)

    def test_wrong_type_record_refused(self):
        self.clock.tick(); run('start-type', self.path, '01')
        self.clock.tick()
        code, out = run('add', self.path, 'channel', '--json',
                        json.dumps({'candidate_id': '02-01', 'channel_id': 'official', 'status': 'searched_no_match'}))
        self.assertEqual(code, 2)
        self.assertIn('현재 진행 유형 01', out)

    def test_finish_refused_then_abandon(self):
        self.clock.tick(); run('start-type', self.path, '01')
        self.clock.tick()
        code, out = run('finish-type', self.path, '01')
        self.assertEqual(code, 2)
        self.assertIn('미실시 항목', out)
        self.clock.tick()
        self.assertEqual(run('finish-type', self.path, '01', '--abandon', '시간 부족')[0], 0)
        self.clock.tick()
        self.assertEqual(run('start-type', self.path, '02')[0], 0)
        self.assertEqual(run('audit', self.path)[0], 2)

    def test_partial_requires_reason(self):
        tmp = tempfile.mkdtemp()
        clock = Clock()
        path = build_complete(tmp, clock, stop_before=lambda t: t == '01')
        clock.tick()
        run('add', path, 'channel', '--json', json.dumps(dict(EV, candidate_id='01-01', channel_id='wanted',
                                                              status='access_blocked', query='q', note='403',
                                                              evidence='(403) Forbidden')))
        clock.tick()
        code, out = run('finish-type', path, '01')
        self.assertEqual(code, 2)
        self.assertIn('--partial-reason', out)
        clock.tick()
        self.assertEqual(run('finish-type', path, '01', '--partial-reason', '원티드 403')[0], 0)

    def test_refuses_overwrite(self):
        self.assertEqual(run('init', self.path)[0], 2)


class TestBaselineImport(unittest.TestCase):
    def test_xlsx_import(self):
        try:
            import openpyxl
        except ImportError:
            self.skipTest('openpyxl 없음')
        tmp = tempfile.mkdtemp()
        x = Path(tmp) / 'prev.xlsx'
        wb = openpyxl.Workbook()
        ws = wb.active; ws.title = '64후보_검증'
        ws.append(['후보ID', '브랜드·서비스', '확인 URL'])
        ws.append(['BR-001', '일레클', 'https://a.example.com/careers'])
        ws.append(['BR-007', '쏘카', 'https://a.example.com/recruit/view/1'])
        ws2 = wb.create_sheet('공고')
        ws2.append(['기업/법인', '공고', '대표 상세URL'])
        ws2.append(['테크타카', '운영', 'https://career.example.com/job/posting/1'])
        ws2.append(['세스코', 'RPA', 'https://m.saramin.co.kr/job-search/view?rec_idx=1'])
        wb.save(x)
        path = str(Path(tmp) / 'l.json')
        code, out = run('init', path, '--baseline', str(x))
        self.assertEqual(code, 0, out)
        t = {u['url']: u for u in LG.load(path)['baseline']['targets']}
        self.assertEqual(t['https://a.example.com/careers']['candidate_id'], '01-01')
        self.assertEqual(t['https://career.example.com/job/posting/1']['candidate_id'], '08-03')
        self.assertIsNone(t['https://m.saramin.co.kr/job-search/view?rec_idx=1']['type_id'])
        self.assertEqual(run('start-type', path, '01')[0], 2)
        tid = t['https://m.saramin.co.kr/job-search/view?rec_idx=1']['target_id']
        self.assertEqual(run('assign-baseline', path, f'{tid}=00')[0], 2)
        self.assertEqual(run('assign-baseline', path, f'{tid}=00:비모빌리티')[0], 0)
        self.assertEqual(run('start-type', path, '01')[0], 0)


if __name__ == '__main__':
    unittest.main()
