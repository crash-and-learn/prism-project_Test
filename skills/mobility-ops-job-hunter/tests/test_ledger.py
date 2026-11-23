"""ledger.py 회귀 테스트 (임시 데이터만 사용, 실제 채용시장 조사 없음).

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


class Clock:
    def __init__(self):
        self.t = dt.datetime(2026, 11, 23, 9, 0, tzinfo=KST)

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


def build_complete(tmp, clock, skip=None):
    """정상 실행 1회를 CLI로 재현한 장부 경로를 반환. skip(type_id)이 참이면 그 유형은 start만 하고 남겨 둔다."""
    path = str(Path(tmp) / 'ledger.json')
    clock.tick()
    assert run('init', path)[0] == 0
    L = LG.load(path)
    L['baseline']['targets'] = copy.deepcopy(BASELINE)
    LG.save(path, L)
    for t in C['types']:
        tid = t['type_id']
        clock.tick()
        code, out = run('start-type', path, tid)
        assert code == 0, out
        recs = []
        for c in [c for c in C['candidates'] if c['type_id'] == tid]:
            recs.append({'kind': 'candidate', 'id': c['id'], 'relation_status': 'verified',
                         'resolved_company_id': 'CO-' + c['id'], 'relation_evidence_url': 'https://example.com/r/' + c['id']})
            for ch in C['channels']:
                recs.append({'kind': 'channel', 'candidate_id': c['id'], 'channel_id': ch['id'], 'status': 'searched_no_match',
                             'query': f'{c["brand_name"]} {ch["id"]} 운영', 'note': '관련 공고 없음'})
        for p in [p for p in LG.load(path)['discovery_plan'] if p['type_id'] == tid]:
            recs.append({'kind': 'search', 'search_id': 'S-' + p['task_id'], 'task_id': p['task_id'],
                         'candidate_id': p['candidate_id'], 'channel_id': p['channel_id'], 'query': p['suggested_query'],
                         'results_reviewed': 10, 'relevant_found': 0})
        if tid == '01':
            recs.append({'kind': 'revisit', 'target_id': 'T0001', 'result': 'ok',
                         'final_url': 'https://old.example.com/careers', 'relevant_found': 0})
        if tid == '02':
            recs += [{'kind': 'revisit', 'target_id': 'T0002', 'result': 'ok', 'final_url': 'https://old.example.com/job/1',
                      'relevant_found': 1},
                     {'kind': 'discovered', 'disc_id': 'D-1', 'url': 'https://old.example.com/job/1', 'title': '운영 데이터 분석',
                      'relevant': True, 'found_via': 'revisit:T0002'},
                     dict(job(), kind='job'),
                     {'kind': 'decision', 'disc_id': 'D-1', 'outcome': 'job', 'job_key': 'J-02-1'}]
        f = Path(tmp) / f'r{tid}.jsonl'
        f.write_text('\n'.join(json.dumps(r, ensure_ascii=False) for r in recs), encoding='utf-8')
        clock.tick()
        code, out = run('add', path, '--file', str(f))
        assert code == 0, out
        if skip and skip(tid):
            return path
        clock.tick()
        code, out = run('finish-type', path, tid)
        assert code == 0, out
    return path


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.clock = Clock()
        cls.path = build_complete(cls.tmp, cls.clock)
        cls.L = LG.load(cls.path)

    def ev(self, L):
        return LG.evaluate(L, C, at_time=self.clock.t)

    def win(self, L, tid):
        return next(t for t in L['types'] if t['type_id'] == tid)['started_at']

    def assertType(self, rep, tid, status, contains=None):
        r = rep['types'][tid]
        self.assertEqual(r['status'], status, r['not_done'][:5] + r['partial'][:5])
        if contains:
            self.assertTrue(any(contains in x for x in r['not_done'] + r['partial'] + r['unresolved']),
                            r['not_done'] + r['partial'] + r['unresolved'])


class TestScenarios(Base):
    def test_0_complete(self):
        rep = self.ev(self.L)
        self.assertEqual(rep['verdict'], 'COMPLETE', rep['errors'])
        self.assertEqual(run('audit', self.path)[0], 0)

    def test_A_no_revisit(self):
        L = copy.deepcopy(self.L); L['revisits'] = []
        rep = self.ev(L)
        self.assertEqual(rep['verdict'], 'FAIL')
        self.assertType(rep, '01', 'not_done', '재방문 누락 T0001')
        self.assertType(rep, '02', 'not_done', '재방문 누락 T0002')

    def test_A_stale_dates(self):
        L = copy.deepcopy(self.L)
        L['channels'][0]['at'] = '2026-11-17T21:00:00+09:00'
        self.assertType(self.ev(L), '01', 'not_done', '작업 구간 밖')

    def test_B_skip_unanchored(self):
        L = copy.deepcopy(self.L)
        L['searches'] = [s for s in L['searches'] if not s['task_id'].startswith('U-03-')]
        rep = self.ev(L)
        self.assertType(rep, '03', 'not_done', '신규 발굴 미실시 U-03-1-web')
        self.assertEqual(rep['types']['04']['status'], 'complete')

    def test_B_skip_entity(self):
        L = copy.deepcopy(self.L)
        L['searches'] = [s for s in L['searches'] if s['task_id'] != 'E-03-02']
        self.assertType(self.ev(L), '03', 'not_done', 'E-03-02')

    def test_C_agency_as_hiring_entity(self):
        L = copy.deepcopy(self.L)
        L['jobs'][0].update(poster_relation='agency', poster_entity='OO아웃소싱', hiring_entity='OO아웃소싱')
        self.assertType(self.ev(L), '02', 'not_done', '위탁·대행')

    def test_C_agency_resolved(self):
        L = copy.deepcopy(self.L)
        L['jobs'][0].update(poster_relation='agency', poster_entity='OO아웃소싱', hiring_entity='쏘카')
        self.assertType(self.ev(L), '02', 'complete')

    def test_C_shallow_results(self):
        L = copy.deepcopy(self.L)
        next(s for s in L['searches'] if s['task_id'] == 'E-02-01')['results_reviewed'] = 3
        rep = self.ev(L)
        self.assertIn('유형 02: complete로 기록됐으나 산정 결과 partial', rep['errors'])
        self.assertEqual(rep['verdict'], 'FAIL')

    def test_D_seen_but_not_registered(self):
        L = copy.deepcopy(self.L)
        ch = next(x for x in L['channels'] if x['candidate_id'] == '02-01' and x['channel_id'] == 'official')
        ch.update(status='page_checked', url='https://socar.example.com/careers', relevant_found=1)
        self.assertType(self.ev(L), '02', 'not_done', '관련 공고 1건 확인했으나 발견 목록 등록 0건')

    def test_D_registered_not_decided(self):
        L = copy.deepcopy(self.L)
        L['discovered'].append({'disc_id': 'D-9', 'type_id': '02', 'url': 'https://x.example.com/9', 'relevant': True,
                                'found_via': 'search:S-E-02-01', 'at': self.win(L, '02')})
        self.assertType(self.ev(L), '02', 'not_done', '최종 판정 0건')

    def test_D_revisited_posting_not_judged(self):
        L = copy.deepcopy(self.L)
        L['discovered'] = []; L['decisions'] = []
        rep = self.ev(L)
        self.assertType(rep, '02', 'not_done', '재확인 대상 공고 T0002')

    def test_E_duplicate_rows(self):
        L = copy.deepcopy(self.L)
        L['jobs'].append(copy.deepcopy(L['jobs'][0]))
        self.assertIn('job_key 중복 J-02-1', self.ev(L)['errors'])

    def test_E_conflict_marked_open(self):
        L = copy.deepcopy(self.L)
        L['jobs'][0]['sources'] = [{'url': 'https://old.example.com/job/1', 'status_seen': 'closed'},
                                   {'url': 'https://wanted.example.com/1', 'status_seen': 'always_open'}]
        L['jobs'][0]['open_evidence'] = {'url': 'https://wanted.example.com/1', 'kind': 'always_open_label', 'quote': '상시채용'}
        self.assertType(self.ev(L), '02', 'not_done', '충돌')

    def test_E_conflict_marked_unknown(self):
        L = copy.deepcopy(self.L)
        L['jobs'][0]['sources'] = [{'url': 'https://old.example.com/job/1', 'status_seen': 'closed'},
                                   {'url': 'https://wanted.example.com/1', 'status_seen': 'always_open'}]
        L['jobs'][0].update(status='unknown_conflict', open_evidence=None)
        self.assertType(self.ev(L), '02', 'complete', '접수 불명')

    def test_E_open_without_evidence(self):
        L = copy.deepcopy(self.L)
        L['jobs'][0]['open_evidence'] = None
        self.assertType(self.ev(L), '02', 'not_done', '모집 중 근거')

    def test_E_open_past_deadline(self):
        L = copy.deepcopy(self.L)
        L['jobs'][0]['deadline'] = '2026-11-20'
        self.assertType(self.ev(L), '02', 'not_done', '지남')

    def test_F_blocked_with_alternative(self):
        L = copy.deepcopy(self.L)
        x = next(x for x in L['channels'] if x['candidate_id'] == '02-01' and x['channel_id'] == 'linkedin')
        x.update(status='access_blocked', alternative_url='https://saramin.example.com/1')
        self.assertType(self.ev(L), '02', 'complete')

    def test_F_blocked_without_alternative_declared_partial(self):
        L = copy.deepcopy(self.L)
        x = next(x for x in L['channels'] if x['candidate_id'] == '02-01' and x['channel_id'] == 'linkedin')
        x.update(status='access_blocked')
        t = next(t for t in L['types'] if t['type_id'] == '02')
        t.update(status='partial', partial_reason='LinkedIn 로그인 제한, 대체 원문 없음')
        rep = self.ev(L)
        self.assertEqual(rep['verdict'], 'PARTIAL')
        self.assertType(rep, '02', 'partial')

    def test_F_blocked_without_alternative_declared_complete(self):
        L = copy.deepcopy(self.L)
        next(x for x in L['channels'] if x['candidate_id'] == '02-01' and x['channel_id'] == 'linkedin').update(
            status='access_blocked')
        self.assertEqual(self.ev(L)['verdict'], 'FAIL')

    def test_G_zero_found(self):
        rep = self.ev(self.L)
        self.assertTrue(rep['types']['03']['zero_found'])
        self.assertEqual(rep['types']['03']['status'], 'complete')

    def test_H_one_channel_unsearched(self):
        L = copy.deepcopy(self.L)
        next(x for x in L['channels'] if x['candidate_id'] == '05-01').update(status='unsearched')
        rep = self.ev(L)
        self.assertType(rep, '05', 'not_done', '채널 미실시 05-01/official')
        self.assertEqual(sum(r['status'] == 'complete' for r in rep['types'].values()), 9)

    def test_H_undecided_job(self):
        L = copy.deepcopy(self.L)
        L['decisions'][0]['outcome'] = None
        self.assertType(self.ev(L), '02', 'not_done', 'outcome')

    def test_I_overlap_order(self):
        L = copy.deepcopy(self.L)
        t1 = next(t for t in L['types'] if t['type_id'] == '01')
        t2 = next(t for t in L['types'] if t['type_id'] == '02')
        t1['finished_at'] = (LG.ts(t2['started_at']) + dt.timedelta(minutes=1)).isoformat()
        self.assertTrue(any('순서 위반' in e for e in self.ev(L)['errors']))

    def test_X_new_company_without_route(self):
        L = copy.deepcopy(self.L)
        L['candidates'].append({'id': 'N-02-1', 'type_id': '02', 'brand_name': '신규카셰어', 'origin': 'discovered',
                                'relation_status': 'verified', 'resolved_company_id': 'CO-N', 'discovered_by': 'S-U-02-1-web',
                                'relation_evidence_url': 'https://n.example.com', 'at': self.win(L, '02')})
        self.assertType(self.ev(L), '02', 'not_done', '신규 후보 N-02-1: 채용 경로 기록 없음')

    def test_report(self):
        out = Path(self.tmp) / 'report.md'
        self.assertEqual(run('report', self.path, str(out))[0], 0)
        text = out.read_text(encoding='utf-8')
        for s in ('휴대폰 요약', '유형별 상태', '공고 목록', '쏘카', '근무지', '(0건)'):
            self.assertIn(s, text)


class TestFlow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.clock = Clock()
        self.path = str(Path(self.tmp) / 'l.json')
        self.clock.tick()
        run('init', self.path)

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
        code, out = run('finish-type', self.path, '01', '--abandon', '시간 부족')
        self.assertEqual(code, 0)
        self.clock.tick()
        self.assertEqual(run('start-type', self.path, '02')[0], 0)
        self.assertEqual(run('audit', self.path)[0], 2)

    def test_partial_requires_reason(self):
        tmp = tempfile.mkdtemp()
        clock = Clock()
        path = build_complete(tmp, clock, skip=lambda t: t == '01')
        clock.tick()
        run('add', path, 'channel', '--json', json.dumps({'candidate_id': '01-01', 'channel_id': 'linkedin',
                                                           'status': 'access_blocked', 'query': 'q', 'note': '로그인'}))
        clock.tick()
        code, out = run('finish-type', path, '01')
        self.assertEqual(code, 2)
        self.assertIn('--partial-reason', out)
        clock.tick()
        self.assertEqual(run('finish-type', path, '01', '--partial-reason', 'LinkedIn 로그인 제한')[0], 0)

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
        self.assertEqual(t['https://a.example.com/recruit/view/1']['type_id'], '02')
        self.assertEqual(t['https://career.example.com/job/posting/1']['candidate_id'], '08-03')
        self.assertIsNone(t['https://m.saramin.co.kr/job-search/view?rec_idx=1']['type_id'])
        self.assertEqual(run('start-type', path, '01')[0], 2)
        tid = t['https://m.saramin.co.kr/job-search/view?rec_idx=1']['target_id']
        self.assertEqual(run('assign-baseline', path, f'{tid}=00')[0], 2)
        self.assertEqual(run('assign-baseline', path, f'{tid}=00:비모빌리티')[0], 0)
        self.assertEqual(run('start-type', path, '01')[0], 0)


if __name__ == '__main__':
    unittest.main()
