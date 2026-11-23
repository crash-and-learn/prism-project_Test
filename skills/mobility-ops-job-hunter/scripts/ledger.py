#!/usr/bin/env python3
"""Mobility Ops Job Hunter v1.2 조사 장부 도구 (Claude·GPT 공용, Python 3.9+ 표준 라이브러리만 사용).

명령 요약
  init LEDGER [--baseline 이전조사표.xlsx|이전장부.json]   새 장부 생성(+ 재방문 대상 가져오기)
  assign-baseline LEDGER T0001=05 T0002=00:사유 ...        유형 미배정 재방문 대상에 유형 지정
  start-type LEDGER 01                                      유형 시작(01→10 순서 강제)
  add LEDGER KIND --json '{...}' | --file records.jsonl     기록 추가(시각 자동, 진행 중 유형만 허용)
  todo LEDGER [TYPE]                                        해당 유형의 남은 작업 목록
  finish-type LEDGER 01 [--partial-reason 사유 | --abandon 사유]
  audit LEDGER [--json]                                     종료 코드 0=완료 1=부분 조사 2=FAIL
  report LEDGER OUT.md                                      유형별 상태·공고 목록·휴대폰 요약

검사는 기록의 존재·정합성만 확인한다. 실제로 페이지를 열었는지, 원문 문구가 맞는지는 사람이 표본 대조한다.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit

SCHEMA = '1.2'
KST = dt.timezone(dt.timedelta(hours=9))
HERE = Path(__file__).resolve().parent

CH_DONE = {'posting_checked', 'page_checked', 'search_only', 'searched_no_match', 'access_blocked', 'not_applicable'}
REL_DONE = {'verified', 'excluded_verified', 'searched_unresolved', 'access_blocked'}
REVISIT_RESULTS = {'ok', 'redirected', 'closed', 'gone', 'blocked'}
EXCLUDE_CODES = {'duplicate', 'closed', 'condition_mismatch', 'irrelevant_jd', 'detail_blocked', 'out_of_scope'}
POSTER = {'direct', 'parent', 'agency'}
JOB_STATUS = {'open_verified', 'closed_verified', 'unknown_conflict', 'unknown'}
OPEN_KINDS = {'deadline_date', 'always_open_label', 'apply_open_label'}
CONDITION_FIT = {'match', 'mismatch', 'check'}
JOB_TEXT_FIELDS = ['title', 'hiring_entity', 'poster_entity', 'location', 'career', 'employment_type', 'deadline',
                   'url', 'fit_reason']
KINDS = ['candidate', 'channel', 'revisit', 'search', 'discovered', 'decision', 'job']


# ---------------------------------------------------------------- 공통

def now():
    v = os.environ.get('MOJH_NOW')  # 테스트 전용 시계
    return dt.datetime.fromisoformat(v) if v else dt.datetime.now(KST).replace(microsecond=0)


def ts(s):
    if not isinstance(s, str):
        return None
    try:
        t = dt.datetime.fromisoformat(s)
    except ValueError:
        return None
    return t if t.tzinfo else None


def url_ok(s):
    try:
        p = urlsplit(s) if isinstance(s, str) else None
        return bool(p and p.scheme in ('http', 'https') and p.netloc)
    except ValueError:
        return False


def ne(v):
    return isinstance(v, str) and bool(v.strip())


def die(msg):
    print('오류: ' + msg, file=sys.stderr)
    sys.exit(2)


def find_contract(explicit=None):
    paths = [explicit, os.environ.get('MOJH_CONTRACT'), HERE.parent / 'references' / 'coverage_contract.json',
             HERE / 'coverage_contract.json', Path.cwd() / 'coverage_contract.json',
             Path('/mnt/data/coverage_contract.json')]
    for p in paths:
        if p and Path(p).is_file():
            return json.loads(Path(p).read_text(encoding='utf-8'))
    die('coverage_contract.json을 찾지 못함. --contract 경로를 지정하세요.')


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save(path, L):
    p = Path(path)
    tmp = p.with_suffix(p.suffix + '.tmp')
    tmp.write_text(json.dumps(L, ensure_ascii=False, indent=1), encoding='utf-8')
    os.replace(tmp, p)


# ---------------------------------------------------------------- 장부 생성 / 이전 조사표

def new_ledger(C):
    t0 = now().isoformat()
    L = {'schema_version': SCHEMA, 'run_started_at': t0,
         'types': [{'type_id': t['type_id'], 'seq': t['seq'], 'category': t['category'], 'status': 'not_started',
                    'started_at': None, 'finished_at': None, 'partial_reason': '', 'abandon_reason': ''}
                   for t in sorted(C['types'], key=lambda x: x['seq'])],
         'baseline': {'source_file': None, 'targets': []},
         'candidates': [], 'channels': [], 'discovery_plan': [],
         'revisits': [], 'searches': [], 'discovered': [], 'decisions': [], 'jobs': []}
    for c in C['candidates']:
        L['candidates'].append({'id': c['id'], 'type_id': c['type_id'], 'brand_name': c['brand_name'],
                                'legal_hint': c['legal_hint'], 'origin': 'contract', 'relation_status': 'unsearched',
                                'resolved_company_id': '', 'relation_evidence_url': '', 'queries': [], 'note': '',
                                'at': None})
        for ch in C['channels']:
            L['channels'].append({'candidate_id': c['id'], 'channel_id': ch['id'], 'type_id': c['type_id'],
                                  'status': 'unsearched', 'query': '', 'url': '', 'alternative_url': '',
                                  'relevant_found': None, 'note': '', 'at': None})
        L['discovery_plan'].append({'task_id': 'E-' + c['id'], 'type_id': c['type_id'], 'candidate_id': c['id'],
                                    'kind': 'entity', 'channel_id': 'web',
                                    'suggested_query': f"{c['brand_name']} {c['legal_hint']} 채용"})
    d = C['discovery']
    for t in C['types']:
        for qi, q in enumerate(t['unanchored_queries'], 1):
            for ch in d['unanchored_channels']:
                L['discovery_plan'].append({'task_id': f"U-{t['type_id']}-{qi}-{ch}", 'type_id': t['type_id'],
                                            'candidate_id': None, 'kind': 'unanchored', 'channel_id': ch,
                                            'suggested_query': q})
    return L


URL_RE = re.compile(r'https?://[^\s,;)\]]+')


def url_kind(u):
    if re.search(r'search|searchword', u):
        return 'search_page'
    if re.search(r'GI_Read|rec_idx|/wd/\d|/job/|/jobs/\d|recruitment/|view/\d|gh_jid|/posting', u):
        return 'job_posting'
    return 'company_page'


def name_tokens(C):
    toks = []
    for c in C['candidates']:
        names = [c['brand_name']] + re.split(r'\s*/\s*', c['legal_hint'])
        for n in names:
            for part in [re.sub(r'\(.*?\)', '', n).strip()] + re.findall(r'\((.*?)\)', n):
                if len(part) >= 2:
                    toks.append((part, c))
    toks.sort(key=lambda x: -len(x[0]))
    return toks


def targets_from_xlsx(path, C):
    try:
        import openpyxl
    except ImportError:
        die('xlsx를 읽으려면 openpyxl이 필요합니다 (pip install openpyxl).')
    cands = C['candidates']
    toks = name_tokens(C)
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    targets, seen, errors = [], {}, []
    for ws in wb.worksheets:
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            continue
        header = [str(h or '') for h in rows[0]]
        id_col = next((i for i, h in enumerate(header) if h == '후보ID'), None)
        brand_col = next((i for i, h in enumerate(header) if h in ('브랜드', '브랜드·서비스')), None)
        name_cols = [i for i, h in enumerate(header) if re.search(r'기업|법인|회사', h)]
        for r in rows[1:]:
            cand, how = None, None
            if id_col is not None and isinstance(r[id_col], str) and r[id_col].startswith('BR-'):
                n = int(r[id_col][3:]) - 1
                if not 0 <= n < len(cands):
                    errors.append(f'{ws.title}: {r[id_col]} 범위 밖')
                    continue
                cand, how = cands[n], 'candidate_id'
                if brand_col is not None and r[brand_col] != cand['brand_name']:
                    errors.append(f'{ws.title}: {r[id_col]} 브랜드 불일치({r[brand_col]})')
            else:
                text = ' '.join(str(r[i]) for i in name_cols if i < len(r) and r[i])
                hit = next((c for tok, c in toks if tok in text), None) if text else None
                if hit:
                    cand, how = hit, 'name_match'
            for v in r:
                for u in (URL_RE.findall(v) if isinstance(v, str) else []):
                    key = (u, cand['id'] if cand else None)
                    if key in seen:
                        seen[key]['source_sheets'].append(ws.title)
                        continue
                    t = {'target_id': f'T{len(targets) + 1:04d}', 'type_id': cand['type_id'] if cand else None,
                         'candidate_id': cand['id'] if cand else None, 'assigned_by': how, 'url': u,
                         'kind': url_kind(u), 'source_sheets': [ws.title], 'assign_reason': ''}
                    seen[key] = t
                    targets.append(t)
    return targets, errors


def targets_from_ledger(path):
    P = load(path)
    out, seen = [], set()

    def add(u, tid, cid, kind):
        if url_ok(u) and (u, cid) not in seen:
            seen.add((u, cid))
            out.append({'target_id': f'T{len(out) + 1:04d}', 'type_id': tid, 'candidate_id': cid,
                        'assigned_by': 'previous_ledger', 'url': u, 'kind': kind, 'source_sheets': ['ledger'],
                        'assign_reason': ''})
    for c in P.get('channels', []):
        if c.get('status') in ('posting_checked', 'page_checked'):
            add(c.get('url'), c.get('type_id'), c.get('candidate_id'), url_kind(c.get('url') or ''))
    for j in P.get('jobs', []):
        if j.get('status') != 'closed_verified':
            for s in j.get('sources', []):
                add(s.get('url'), j.get('type_id'), None, 'job_posting')
    return out, []


def cmd_init(a):
    C = find_contract(a.contract)
    if Path(a.ledger).exists():
        die(f'{a.ledger} 이미 존재. 기존 장부를 덮어쓰지 않습니다. 새 파일명을 쓰세요.')
    L = new_ledger(C)
    if a.baseline:
        src = Path(a.baseline)
        targets, errors = targets_from_xlsx(src, C) if src.suffix.lower() in ('.xlsx', '.xlsm') else targets_from_ledger(src)
        L['baseline'] = {'source_file': src.name, 'targets': targets, 'import_errors': errors}
    save(a.ledger, L)
    t = L['baseline']['targets']
    un = [x for x in t if x['type_id'] is None]
    print(f'장부 생성: 후보 {len(L["candidates"])}, 채널 {len(L["channels"])}, 발굴 작업 {len(L["discovery_plan"])}, '
          f'재방문 대상 {len(t)} (유형 미배정 {len(un)})')
    if un:
        print('유형 미배정 대상은 assign-baseline으로 01~10 또는 00(유형 외:사유)을 지정해야 start-type이 가능합니다.')
        for x in un[:15]:
            print(f'  {x["target_id"]} {x["url"]} ({",".join(x["source_sheets"])})')
        if len(un) > 15:
            print(f'  ... 외 {len(un) - 15}건 (todo로 전체 확인)')


def cmd_assign(a):
    L = load(a.ledger)
    if any(t['status'] != 'not_started' for t in L['types']):
        die('조사가 시작된 뒤에는 재방문 대상 유형을 바꿀 수 없습니다.')
    by = {t['target_id']: t for t in L['baseline']['targets']}
    valid = {t['type_id'] for t in L['types']} | {'00'}
    for spec in a.specs:
        m = re.fullmatch(r'(T\d+)=(\d\d)(?::(.+))?', spec)
        if not m or m.group(1) not in by or m.group(2) not in valid:
            die(f'형식 오류 또는 없는 대상: {spec} (예: T0003=05 또는 T0004=00:비모빌리티 공고)')
        if m.group(2) == '00' and not ne(m.group(3)):
            die(f'{spec}: 유형 외(00) 지정에는 사유가 필요합니다.')
        by[m.group(1)].update(type_id=m.group(2), assigned_by='manual', assign_reason=m.group(3) or '')
    save(a.ledger, L)
    print(f'지정 완료. 남은 미배정 {sum(1 for t in L["baseline"]["targets"] if t["type_id"] is None)}건')


# ---------------------------------------------------------------- 유형 진행

def active_type(L):
    act = [t for t in L['types'] if t['status'] == 'in_progress']
    return act[0] if act else None


def cmd_start(a):
    L = load(a.ledger)
    if active_type(L):
        die(f'유형 {active_type(L)["type_id"]} 진행 중. finish-type 후 다음 유형을 시작하세요.')
    if any(t['type_id'] is None for t in L['baseline']['targets']):
        die('유형 미배정 재방문 대상이 있습니다. assign-baseline 먼저 실행.')
    nxt = next((t for t in sorted(L['types'], key=lambda x: x['seq']) if t['status'] == 'not_started'), None)
    if not nxt or nxt['type_id'] != a.type_id:
        die(f'다음 순서 유형은 {nxt["type_id"] if nxt else "없음"} 입니다.')
    nxt.update(status='in_progress', started_at=now().isoformat())
    save(a.ledger, L)
    print(f'유형 {a.type_id} {nxt["category"]} 시작 {nxt["started_at"]}')
    print_todo(L, a.type_id, find_contract(a.contract), limit=30)


def type_of(L, kind, rec):
    if kind == 'candidate':
        c = next((x for x in L['candidates'] if x['id'] == rec.get('id')), None)
        return c['type_id'] if c else rec.get('type_id')
    if kind == 'channel':
        c = next((x for x in L['candidates'] if x['id'] == rec.get('candidate_id')), None)
        if not c:
            die(f'channel: 후보 {rec.get("candidate_id")} 없음. 신규 기업은 candidate 먼저 추가.')
        return c['type_id']
    if kind == 'revisit':
        t = next((x for x in L['baseline']['targets'] if x['target_id'] == rec.get('target_id')), None)
        if not t:
            die(f'revisit: 대상 {rec.get("target_id")} 없음')
        return t['type_id']
    if kind == 'search' and rec.get('task_id'):
        p = next((x for x in L['discovery_plan'] if x['task_id'] == rec['task_id']), None)
        if not p:
            die(f'search: 작업 {rec["task_id"]} 없음 (추가 검색이면 task_id를 비우세요)')
        return p['type_id']
    if kind == 'decision':
        d = next((x for x in L['discovered'] if x['disc_id'] == rec.get('disc_id')), None)
        if not d:
            die(f'decision: 발견 공고 {rec.get("disc_id")} 없음')
        return d['type_id']
    return rec.get('type_id')


def add_record(L, kind, rec):
    act = active_type(L)
    if not act:
        die('진행 중인 유형이 없습니다. start-type 먼저 실행.')
    tid = type_of(L, kind, rec) or act['type_id']
    if tid != act['type_id']:
        die(f'{kind}: 유형 {tid} 기록은 현재 진행 유형 {act["type_id"]} 구간에 쓸 수 없습니다.')
    rec = dict(rec, type_id=tid, at=now().isoformat())
    if kind == 'candidate':
        row = next((x for x in L['candidates'] if x['id'] == rec.get('id')), None)
        if row:
            for k in ('origin', 'brand_name', 'legal_hint'):
                rec.pop(k, None)
            row.update(rec)
        else:
            if not ne(rec.get('id')) or not ne(rec.get('brand_name')):
                die('신규 후보는 id·brand_name 필요')
            rec.setdefault('origin', 'discovered')
            rec['origin'] = 'discovered'
            L['candidates'].append(rec)
        return rec.get('id')
    if kind == 'channel':
        key = (rec.get('candidate_id'), rec.get('channel_id'))
        row = next((x for x in L['channels'] if (x['candidate_id'], x['channel_id']) == key), None)
        if row:
            row.update(rec)
        else:
            L['channels'].append(rec)
        return '/'.join(map(str, key))
    if kind == 'job':
        row = next((x for x in L['jobs'] if x['job_key'] == rec.get('job_key')), None)
        if not ne(rec.get('job_key')):
            die('job: job_key 필요')
        if row:
            if row['type_id'] != tid:
                die('다른 유형의 공고는 수정할 수 없습니다. decision(duplicate)으로 연결하세요.')
            srcs = {s.get('url'): s for s in row.get('sources', [])}
            for s in rec.pop('sources', []):
                srcs[s.get('url')] = s
            row.update(rec)
            row['sources'] = list(srcs.values())
        else:
            L['jobs'].append(rec)
        return rec['job_key']
    idkey, prefix, lst = {'search': ('search_id', 'S', 'searches'), 'discovered': ('disc_id', 'D', 'discovered'),
                          'revisit': (None, None, 'revisits'), 'decision': (None, None, 'decisions')}[kind]
    if idkey:
        if not rec.get(idkey):
            rec[idkey] = f'{prefix}{len(L[lst]) + 1:04d}'
        if any(x.get(idkey) == rec[idkey] for x in L[lst]):
            die(f'{kind}: {rec[idkey]} 중복')
    L[lst].append(rec)
    return rec.get(idkey) if idkey else rec.get('target_id') or rec.get('disc_id')


def cmd_add(a):
    L = load(a.ledger)
    items = []
    if a.json:
        if not a.kind:
            die('--json 사용 시 KIND 필요')
        data = json.loads(a.json)
        items = [(a.kind, d) for d in (data if isinstance(data, list) else [data])]
    elif a.file:
        for line in Path(a.file).read_text(encoding='utf-8').splitlines():
            if line.strip():
                d = json.loads(line)
                items.append((d.pop('kind', a.kind), d))
    else:
        die('--json 또는 --file 필요')
    ids = []
    for kind, d in items:
        if kind not in KINDS:
            die(f'알 수 없는 KIND {kind}. 사용 가능: {", ".join(KINDS)}')
        ids.append(f'{kind}:{add_record(L, kind, d)}')
    save(a.ledger, L)
    print('기록 ' + ', '.join(ids))


# ---------------------------------------------------------------- 감사

def evaluate(L, C, only=None, at_time=None):
    errs = []
    miss, part, unres = defaultdict(list), defaultdict(list), defaultdict(list)
    stats = defaultdict(Counter)
    tnow = at_time or now()
    types = {t['type_id']: t for t in L.get('types', [])}
    type_ids = [t['type_id'] for t in sorted(C['types'], key=lambda x: x['seq'])]
    run_start = ts(L.get('run_started_at'))
    if not run_start:
        return {'verdict': 'FAIL', 'errors': ['run_started_at 없음'], 'types': {}}

    win = {}
    for tid in type_ids:
        t = types.get(tid) or {}
        s = ts(t.get('started_at'))
        e = ts(t.get('finished_at')) if t.get('status') != 'in_progress' else tnow
        if t.get('status') == 'not_started' or not s:
            miss[tid].append('유형 미착수')
            continue
        if not (e and run_start <= s <= e):
            miss[tid].append('유형 시작·종료 시각 이상')
            continue
        if t.get('status') == 'in_progress':
            miss[tid].append('유형 진행 중(finish-type 전)')
        if t.get('status') == 'not_done':
            miss[tid].append(f'미완료 종료: {t.get("abandon_reason")}')
        win[tid] = (s, e)
    ordered = [t for t in type_ids if t in win]
    for x, y in zip(ordered, ordered[1:]):
        if win[y][0] < win[x][1]:
            errs.append(f'순서 위반: 유형 {y} 시작이 유형 {x} 종료보다 이름')
    for x, y in zip(type_ids, type_ids[1:]):
        if y in win and x not in win:
            errs.append(f'순서 위반: 유형 {x} 미착수인데 유형 {y} 진행')

    def in_win(tid, when, label):
        if tid not in win:
            return False
        t = ts(when)
        if not t or not (win[tid][0] <= t <= win[tid][1]):
            miss[tid].append(f'{label}: 시각이 유형 {tid} 작업 구간 밖({when})')
            return False
        return True

    disc_by_via = Counter(d.get('found_via') for d in L.get('discovered', []))

    def check_found(tid, via, n, label):
        if not isinstance(n, int) or n < 0:
            miss[tid].append(f'{label}: relevant_found(본 관련 공고 수) 미기재')
        elif disc_by_via[via] < n:
            miss[tid].append(f'{label}: 관련 공고 {n}건 확인했으나 발견 목록 등록 {disc_by_via[via]}건')

    # 1) 이전 조사표 재방문
    rv = {}
    for r in L.get('revisits', []):
        rv[r.get('target_id')] = r
    posting_urls = defaultdict(set)
    for tg in L.get('baseline', {}).get('targets', []):
        tid = tg.get('type_id')
        if tid is None:
            errs.append(f'재방문 대상 {tg["target_id"]}: 유형 미배정')
            continue
        if tid == '00':
            if not ne(tg.get('assign_reason')):
                errs.append(f'재방문 대상 {tg["target_id"]}: 유형 외(00) 사유 없음')
            continue
        stats[tid]['revisit_total'] += 1
        r = rv.get(tg['target_id'])
        if not r:
            miss[tid].append(f'재방문 누락 {tg["target_id"]} {tg["url"]}')
            continue
        if not in_win(tid, r.get('at'), f'재방문 {tg["target_id"]}'):
            continue
        res = r.get('result')
        if res not in REVISIT_RESULTS:
            miss[tid].append(f'재방문 {tg["target_id"]}: result 없음')
            continue
        stats[tid]['revisit_done'] += 1
        if res == 'blocked' and not url_ok(r.get('alternative_url')):
            part[tid].append(f'재방문 차단·대체 원문 없음 {tg["target_id"]} {tg["url"]}')
        if res in ('ok', 'redirected'):
            check_found(tid, f'revisit:{tg["target_id"]}', r.get('relevant_found'), f'재방문 {tg["target_id"]}')
        if tg.get('kind') == 'job_posting' and res in ('ok', 'redirected', 'closed'):
            posting_urls[tid].add((tg['target_id'], tg['url'], r.get('final_url') or tg['url']))

    # 2) 신규 발굴 계획 ↔ 실행
    minrev = C['discovery']['min_results_reviewed']
    by_task = defaultdict(list)
    for s in L.get('searches', []):
        by_task[s.get('task_id')].append(s)
    for p in L.get('discovery_plan', []):
        tid = p['type_id']
        stats[tid]['plan_total'] += 1
        done = False
        for s in by_task.get(p['task_id'], []):
            if not in_win(tid, s.get('at'), f'검색 {s.get("search_id")}'):
                continue
            if not ne(s.get('query')):
                miss[tid].append(f'검색 {s.get("search_id")}: query 없음')
                continue
            if p['kind'] == 'unanchored' and s.get('candidate_id'):
                miss[tid].append(f'검색 {s.get("search_id")}: 기업명 비고정 작업에 candidate_id 지정')
                continue
            seen, rev = s.get('result_count_seen'), s.get('results_reviewed')
            if not isinstance(rev, int):
                miss[tid].append(f'검색 {s.get("search_id")}: results_reviewed 미기재')
                continue
            if rev < minrev and not (isinstance(seen, int) and rev >= seen):
                part[tid].append(f'{p["task_id"]}: 검색 결과 {rev}개만 검토(기준 {minrev}개 또는 전체)')
            check_found(tid, f'search:{s.get("search_id")}', s.get('relevant_found'), f'검색 {s.get("search_id")}')
            done = True
        if done:
            stats[tid]['plan_done'] += 1
        else:
            miss[tid].append(f'신규 발굴 미실시 {p["task_id"]} ({p["kind"]}, 예시 검색어: {p["suggested_query"]})')

    # 3) 후보 관계 + 채널
    cand = {c['id']: c for c in L.get('candidates', [])}
    for c in cand.values():
        tid = c.get('type_id')
        if tid not in type_ids:
            errs.append(f'후보 {c.get("id")}: 유형 없음')
            continue
        st = c.get('relation_status')
        if st not in REL_DONE:
            miss[tid].append(f'법인 관계 미조사 {c["id"]} {c.get("brand_name")}')
        elif in_win(tid, c.get('at'), f'후보 {c["id"]}'):
            if st in ('verified', 'excluded_verified') and not url_ok(c.get('relation_evidence_url')):
                miss[tid].append(f'후보 {c["id"]}: 관계 근거 URL 없음')
            elif st == 'verified' and not ne(c.get('resolved_company_id')):
                miss[tid].append(f'후보 {c["id"]}: resolved_company_id 없음')
            elif st in ('searched_unresolved', 'access_blocked') and not (c.get('queries') and ne(c.get('note'))):
                miss[tid].append(f'후보 {c["id"]}: 검색어·사유 없음')
            if st == 'access_blocked':
                part[tid].append(f'후보 {c["id"]}: 법인 관계 접근 제한')
        if c.get('origin') == 'discovered':
            stats[tid]['new_companies'] += 1
            if not any(s.get('search_id') == c.get('discovered_by') for s in L.get('searches', [])):
                miss[tid].append(f'신규 후보 {c["id"]}: discovered_by(발견 검색 ID) 없음')
    contract_ch = [ch['id'] for ch in C['channels']]
    chans = {(x['candidate_id'], x['channel_id']): x for x in L.get('channels', [])}
    for cid, c in cand.items():
        tid = c.get('type_id')
        if tid not in type_ids:
            continue
        need = contract_ch if c.get('origin') == 'contract' else []
        if c.get('origin') == 'discovered' and not any(k[0] == cid and v.get('status') in CH_DONE
                                                        for k, v in chans.items()):
            miss[tid].append(f'신규 후보 {cid}: 채용 경로 기록 없음')
        for ch in need + [k[1] for k in chans if k[0] == cid and k[1] not in need]:
            x = chans.get((cid, ch))
            stats[tid]['channel_total'] += 1
            if not x or x.get('status') not in CH_DONE:
                miss[tid].append(f'채널 미실시 {cid}/{ch}')
                continue
            if not in_win(tid, x.get('at'), f'채널 {cid}/{ch}'):
                continue
            stats[tid]['channel_done'] += 1
            s = x['status']
            if s in ('posting_checked', 'page_checked'):
                if not url_ok(x.get('url')):
                    miss[tid].append(f'채널 {cid}/{ch}: url 없음')
                check_found(tid, f'channel:{cid}/{ch}', x.get('relevant_found'), f'채널 {cid}/{ch}')
            if s in ('search_only', 'searched_no_match', 'access_blocked') and not (ne(x.get('query')) and ne(x.get('note'))):
                miss[tid].append(f'채널 {cid}/{ch}: query·note 없음')
            if s == 'not_applicable' and (ch not in ('group', 'global_careers') or not ne(x.get('note'))):
                miss[tid].append(f'채널 {cid}/{ch}: not_applicable은 group·global_careers에 사유와 함께만 허용')
            if s == 'access_blocked' and not url_ok(x.get('alternative_url')):
                part[tid].append(f'채널 차단·대체 원문 없음 {cid}/{ch}')

    # 4) 공고
    jobs = {}
    for j in L.get('jobs', []):
        k = j.get('job_key')
        tid = j.get('type_id')
        if k in jobs:
            errs.append(f'job_key 중복 {k}')
            continue
        jobs[k] = j
        stats[tid]['jobs'] += 1
        lack = [f for f in JOB_TEXT_FIELDS if not ne(j.get(f))]
        if not isinstance(j.get('fit_score'), int) or not 0 <= j['fit_score'] <= 100:
            lack.append('fit_score(0~100)')
        if j.get('condition_fit') not in CONDITION_FIT:
            lack.append('condition_fit')
        if not url_ok(j.get('url')):
            lack.append('url(형식)')
        if lack:
            miss[tid].append(f'공고 {k}: 필수 필드 없음 {lack}')
        rel = j.get('poster_relation')
        if rel not in POSTER:
            miss[tid].append(f'공고 {k}: poster_relation(direct/parent/agency) 없음')
        elif rel == 'agency':
            if j.get('hiring_entity') in (None, '', j.get('poster_entity')):
                miss[tid].append(f'공고 {k}: 위탁·대행 게시인데 실제 채용 법인이 게시 법인과 같거나 비어 있음')
            elif j.get('hiring_entity') == '확인 불가':
                unres[tid].append(f'공고 {k}: 실제 채용 법인 확인 불가({j.get("poster_entity")} 게시)')
        srcs = j.get('sources') or []
        if not srcs or not all(url_ok(s.get('url')) and s.get('status_seen') in ('open', 'always_open', 'closed', 'unknown')
                               for s in srcs):
            miss[tid].append(f'공고 {k}: sources(url, status_seen) 없음')
        seen = {s.get('status_seen') for s in srcs}
        conflict = 'closed' in seen and bool(seen & {'open', 'always_open'})
        st = j.get('status')
        if st not in JOB_STATUS:
            miss[tid].append(f'공고 {k}: 상태 미판정')
        elif conflict and st != 'unknown_conflict':
            miss[tid].append(f'공고 {k}: 출처 간 마감/모집 충돌인데 {st}')
        elif st == 'unknown_conflict':
            unres[tid].append(f'공고 {k}: 출처 간 상태 충돌 → 접수 불명')
        elif st == 'unknown':
            unres[tid].append(f'공고 {k}: 접수 상태 불명')
        if st == 'open_verified':
            ev = j.get('open_evidence') or {}
            if ev.get('kind') not in OPEN_KINDS or not ne(ev.get('quote')) or ev.get('url') not in {s.get('url') for s in srcs}:
                miss[tid].append(f'공고 {k}: 모집 중 근거(sources 중 상세 URL + 원문 문구) 없음')
            elif ev['kind'] == 'deadline_date':
                end = win.get(tid, (None, tnow))[1]
                if not re.match(r'\d{4}-\d{2}-\d{2}', j.get('deadline') or ''):
                    miss[tid].append(f'공고 {k}: deadline_date 근거인데 마감일 형식 아님')
                elif j['deadline'][:10] < end.date().isoformat():
                    miss[tid].append(f'공고 {k}: 마감일 {j["deadline"]} 지남인데 모집 중')
        if tid in win:
            in_win(tid, j.get('at'), f'공고 {k}')

    # 5) 발견 ↔ 판정
    vias = {f'revisit:{r.get("target_id")}' for r in L.get('revisits', [])}
    vias |= {f'search:{s.get("search_id")}' for s in L.get('searches', [])}
    vias |= {f'channel:{x["candidate_id"]}/{x["channel_id"]}' for x in L.get('channels', [])}
    decs = defaultdict(list)
    for d in L.get('decisions', []):
        decs[d.get('disc_id')].append(d)
    linked_jobs = set()
    disc_urls = defaultdict(set)
    for d in L.get('discovered', []):
        tid = d.get('type_id')
        disc_urls[tid].add(d.get('url'))
        if d.get('found_via') not in vias:
            miss[tid].append(f'발견 {d.get("disc_id")}: found_via가 실제 기록(revisit/search/channel)을 가리키지 않음')
        if not d.get('relevant'):
            if not ne(d.get('reason')):
                miss[tid].append(f'발견 {d.get("disc_id")}: 무관 판단 사유 없음')
            continue
        stats[tid]['discovered'] += 1
        ds = decs.get(d.get('disc_id'), [])
        if len(ds) != 1:
            miss[tid].append(f'발견 공고 {d.get("disc_id")} {d.get("url")}: 최종 판정 {len(ds)}건')
            continue
        x = ds[0]
        if x.get('outcome') == 'job':
            if x.get('job_key') not in jobs:
                miss[tid].append(f'발견 {d["disc_id"]}: job_key {x.get("job_key")} 없음')
            linked_jobs.add(x.get('job_key'))
        elif x.get('outcome') == 'excluded':
            if x.get('reason_code') not in EXCLUDE_CODES or not ne(x.get('reason')):
                miss[tid].append(f'발견 {d["disc_id"]}: 제외 reason_code·reason 없음')
            elif x['reason_code'] == 'duplicate':
                if x.get('duplicate_of') not in jobs:
                    miss[tid].append(f'발견 {d["disc_id"]}: duplicate_of 공고 없음')
                linked_jobs.add(x.get('duplicate_of'))
            elif x['reason_code'] == 'detail_blocked':
                part[tid].append(f'발견 {d["disc_id"]}: 상세 접근 제한 {d.get("url")}')
        else:
            miss[tid].append(f'발견 {d["disc_id"]}: outcome(job/excluded) 없음')
            continue
        stats[tid]['decided'] += 1
    for k, j in jobs.items():
        if k not in linked_jobs:
            miss[j.get('type_id')].append(f'공고 {k}: 발견 목록·판정과 연결되지 않음')
    for tid, items in posting_urls.items():
        for target_id, u1, u2 in items:
            if not ({u1, u2} & disc_urls[tid]):
                miss[tid].append(f'재확인 대상 공고 {target_id}: 발견 목록에 등록·판정 안 됨 {u1}')

    # 유형별 상태
    result = {}
    for tid in type_ids:
        if only and tid != only:
            continue
        t = types.get(tid) or {}
        computed = 'not_done' if miss[tid] else ('partial' if part[tid] else 'complete')
        declared = t.get('status')
        if declared == 'complete' and computed != 'complete':
            errs.append(f'유형 {tid}: complete로 기록됐으나 산정 결과 {computed}')
        if declared == 'partial' and computed == 'partial' and not ne(t.get('partial_reason')):
            computed = 'not_done'
            miss[tid].append('partial_reason 없음')
        if declared == 'partial' and computed == 'complete':
            computed = 'partial'
        s = stats[tid]
        result[tid] = {'category': t.get('category'), 'status': computed, 'declared': declared,
                       'partial_reason': t.get('partial_reason', ''),
                       'zero_found': computed != 'not_done' and s['jobs'] == 0,
                       'counts': dict(s), 'not_done': miss[tid], 'partial': part[tid], 'unresolved': unres[tid]}
    sc = Counter(r['status'] for r in result.values())
    if errs or sc['not_done']:
        verdict = 'FAIL'
    elif sc['partial']:
        verdict = 'PARTIAL'
    else:
        verdict = 'COMPLETE'
    return {'verdict': verdict, 'type_status_count': dict(sc), 'errors': errs, 'types': result}


def print_todo(L, tid, C, limit=None):
    r = evaluate(L, C, only=tid)['types'][tid]
    items = [x for x in r['not_done'] if not x.startswith('유형 진행 중')]
    print(f'[{tid} {r["category"]}] 남은 작업 {len(items)}건, 부분 조사 사유 {len(r["partial"])}건, 미확인 {len(r["unresolved"])}건')
    for x in items[:limit] if limit else items:
        print('  - ' + x)
    if limit and len(items) > limit:
        print(f'  ... 외 {len(items) - limit}건 (todo로 전체 확인)')
    for x in r['partial']:
        print('  ~ ' + x)
    for x in r['unresolved']:
        print('  ? ' + x)
    return items


def cmd_todo(a):
    L = load(a.ledger)
    C = find_contract(a.contract)
    tid = a.type_id or (active_type(L) or {}).get('type_id')
    if not tid:
        un = [t for t in L['baseline']['targets'] if t['type_id'] is None]
        print(f'진행 중 유형 없음. 유형 미배정 재방문 대상 {len(un)}건')
        for t in un:
            print(f'  {t["target_id"]} {t["url"]} ({",".join(t["source_sheets"])})')
        return
    print_todo(L, tid, C)


def cmd_finish(a):
    L = load(a.ledger)
    C = find_contract(a.contract)
    t = active_type(L)
    if not t or t['type_id'] != a.type_id:
        die(f'유형 {a.type_id}는 진행 중이 아닙니다.')
    t['finished_at'] = now().isoformat()
    t['status'] = 'checking'
    r = evaluate(L, C, only=a.type_id, at_time=ts(t['finished_at']))['types'][a.type_id]
    remaining = [x for x in r['not_done'] if not x.startswith('미완료 종료')]
    if remaining:
        if not a.abandon:
            print_todo(dict(L, types=[dict(x, status='in_progress') if x is t else x for x in L['types']]), a.type_id, C)
            die('미실시 항목이 남아 종료할 수 없습니다. 처리하거나, 끝내 못 하면 --abandon "사유"로 미완료 종료하세요.')
        t.update(status='not_done', abandon_reason=a.abandon)
    elif r['partial']:
        if not a.partial_reason:
            for x in r['partial']:
                print('  ~ ' + x)
            die('부분 조사 사유가 있습니다. --partial-reason "사유"를 지정하세요.')
        t.update(status='partial', partial_reason=a.partial_reason)
    else:
        t['status'] = 'complete'
    save(a.ledger, L)
    print(f'유형 {a.type_id} 종료: {t["status"]} (공고 {r["counts"].get("jobs", 0)}건, 미확인 {len(r["unresolved"])}건)')
    nxt = next((x for x in sorted(L['types'], key=lambda x: x['seq']) if x['status'] == 'not_started'), None)
    print(f'다음: start-type {nxt["type_id"]}' if nxt else '모든 유형 종료. audit → report 실행.')


def cmd_audit(a):
    L = load(a.ledger)
    rep = evaluate(L, find_contract(a.contract))
    if a.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
    else:
        label = {'COMPLETE': 'COMPLETE (10개 유형 완료)', 'PARTIAL': 'PARTIAL (부분 조사 유형 있음, 사유 기록됨)',
                 'FAIL': 'FAIL (조사 완료 표시 금지)'}[rep['verdict']]
        print(label, rep['type_status_count'])
        for e in rep['errors']:
            print(' ! ' + e)
        for tid, r in rep['types'].items():
            print(f' [{tid}] {r["status"]:9s} 미실시 {len(r["not_done"])} / 부분 {len(r["partial"])} / '
                  f'미확인 {len(r["unresolved"])} / 공고 {r["counts"].get("jobs", 0)}')
            for x in (r['not_done'] + r['partial'])[:3]:
                print('     - ' + x)
    return {'COMPLETE': 0, 'PARTIAL': 1}.get(rep['verdict'], 2)


# ---------------------------------------------------------------- 보고서

STATUS_KO = {'complete': '완료', 'partial': '부분 조사', 'not_done': '미실시'}
JOB_KO = {'open_verified': '모집 중(원문 확인)', 'closed_verified': '마감', 'unknown_conflict': '접수 불명(출처 충돌)',
          'unknown': '접수 불명'}
FIT_KO = {'match': '조건 부합', 'mismatch': '조건 불일치', 'check': '추가 확인'}


def cmd_report(a):
    L = load(a.ledger)
    rep = evaluate(L, find_contract(a.contract))
    jobs = sorted(L.get('jobs', []), key=lambda j: (j.get('status') != 'open_verified',
                                                     j.get('condition_fit') != 'match', -(j.get('fit_score') or 0)))
    top = [j for j in jobs if j.get('status') == 'open_verified' and j.get('condition_fit') in ('match', 'check')][:5]
    sc = rep['type_status_count']
    date = (L.get('run_started_at') or '')[:10]
    out = [f'# 국내 모빌리티 운영 채용 조사 {date}',
           '',
           f'**감사 판정: {rep["verdict"]}** · 완료 {sc.get("complete", 0)} / 부분 조사 {sc.get("partial", 0)} / '
           f'미실시 {sc.get("not_done", 0)} (10개 유형)',
           '', '## 휴대폰 요약', '']
    if top:
        out.append('**지원 우선순위**')
        for i, j in enumerate(top, 1):
            out.append(f'{i}. {j.get("hiring_entity")} · {j.get("title")} · 마감 {j.get("deadline")} · '
                       f'{j.get("fit_score")}점 · {FIT_KO.get(j.get("condition_fit"))} · [원문]({j.get("url")})')
    else:
        out.append('**지원 우선순위**: 원문으로 모집 중이 확인된 조건 부합 공고 없음')
    cons = []
    for tid, r in rep['types'].items():
        if r['status'] != 'complete':
            cons.append(f'{tid} {r["category"]}: {STATUS_KO[r["status"]]}'
                        + (f' — {r["partial_reason"]}' if r['partial_reason'] else ''))
        cons += [f'{tid}: {x}' for x in r['unresolved'][:2]]
    out += ['', '**주요 제약**'] + [f'- {x}' for x in cons[:8]] + (['- 없음'] if not cons else [])
    out += ['', '## 유형별 상태', '',
            '| 유형 | 상태 | 재방문 | 신규 발굴 | 채널 | 발견→판정 | 신규 기업 | 공고 | 미확인 |',
            '|---|---|---|---|---|---|---|---|---|']
    for tid, r in rep['types'].items():
        c = r['counts']
        st = STATUS_KO[r['status']] + (' (0건)' if r['zero_found'] else '')
        out.append(f'| {tid} {r["category"]} | {st} | {c.get("revisit_done", 0)}/{c.get("revisit_total", 0)} | '
                   f'{c.get("plan_done", 0)}/{c.get("plan_total", 0)} | {c.get("channel_done", 0)}/{c.get("channel_total", 0)} | '
                   f'{c.get("decided", 0)}/{c.get("discovered", 0)} | {c.get("new_companies", 0)} | {c.get("jobs", 0)} | '
                   f'{len(r["unresolved"])} |')
    out += ['', '## 공고 목록', '',
            '| 순위 | 채용 법인 (게시 주체) | 직무 | 근무지 | 경력 | 고용형태 | 마감 | 접수 상태 | 적합도 | 조건 | 원문 |',
            '|---|---|---|---|---|---|---|---|---|---|---|']
    for i, j in enumerate(jobs, 1):
        poster = '' if j.get('poster_relation') == 'direct' else f' ({j.get("poster_entity")}·{j.get("poster_relation")})'
        out.append(f'| {i} | {j.get("hiring_entity")}{poster} | {j.get("title")} | {j.get("location")} | {j.get("career")} | '
                   f'{j.get("employment_type")} | {j.get("deadline")} | {JOB_KO.get(j.get("status"), j.get("status"))} | '
                   f'{j.get("fit_score")} | {FIT_KO.get(j.get("condition_fit"), "")} | [링크]({j.get("url")}) |')
    if not jobs:
        out.append('| - | 관련 공고 0건 | | | | | | | | | |')
    out += ['', '## 미확인·부분 조사·미실시 항목', '']
    for tid, r in rep['types'].items():
        for label, xs in (('미실시', r['not_done']), ('부분', r['partial']), ('미확인', r['unresolved'])):
            out += [f'- [{tid}][{label}] {x}' for x in xs]
    out += [f'- [전체] {e}' for e in rep['errors']]
    if out[-1] == '':
        out.append('- 없음')
    out += ['', '> 감사는 기록의 존재·정합성 검사입니다. 실제 열람 여부와 원문 문구는 표본 대조로 확인하세요. '
                '완료 판정도 공개되지 않은 공고까지 모두 찾았다는 뜻은 아닙니다.']
    Path(a.out).write_text('\n'.join(out) + '\n', encoding='utf-8')
    print(f'{a.out} 작성 ({rep["verdict"]})')


# ---------------------------------------------------------------- CLI

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--contract', help='coverage_contract.json 경로(자동 탐색 실패 시)')
    sp = ap.add_subparsers(dest='cmd', required=True)
    p = sp.add_parser('init'); p.add_argument('ledger'); p.add_argument('--baseline'); p.set_defaults(f=cmd_init)
    p = sp.add_parser('assign-baseline'); p.add_argument('ledger'); p.add_argument('specs', nargs='+'); p.set_defaults(f=cmd_assign)
    p = sp.add_parser('start-type'); p.add_argument('ledger'); p.add_argument('type_id'); p.set_defaults(f=cmd_start)
    p = sp.add_parser('add'); p.add_argument('ledger'); p.add_argument('kind', nargs='?')
    p.add_argument('--json'); p.add_argument('--file'); p.set_defaults(f=cmd_add)
    p = sp.add_parser('todo'); p.add_argument('ledger'); p.add_argument('type_id', nargs='?'); p.set_defaults(f=cmd_todo)
    p = sp.add_parser('finish-type'); p.add_argument('ledger'); p.add_argument('type_id')
    p.add_argument('--partial-reason'); p.add_argument('--abandon'); p.set_defaults(f=cmd_finish)
    p = sp.add_parser('audit'); p.add_argument('ledger'); p.add_argument('--json', action='store_true'); p.set_defaults(f=cmd_audit)
    p = sp.add_parser('report'); p.add_argument('ledger'); p.add_argument('out'); p.set_defaults(f=cmd_report)
    a = ap.parse_args(argv)
    return a.f(a) or 0


if __name__ == '__main__':
    sys.exit(main())
