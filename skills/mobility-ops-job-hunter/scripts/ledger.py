#!/usr/bin/env python3
"""Mobility Ops Job Hunter v1.2.1 조사 장부 도구 (Claude·GPT 공용, Python 3.9+ 표준 라이브러리).

명령
  init LEDGER [--baseline 이전장부.json|이전조사표.xlsx]   새 회차 장부(법인 등록부·이월 항목 포함)
  assign-baseline LEDGER T0001=05 T0002=00:사유 ...        유형 미배정 재방문 대상 지정
  plan LEDGER [--budget 500]                               턴 분할 계획(유형 경계 기준)
  next LEDGER                                              지금 턴에서 할 일
  names LEDGER [--json]                                    후보별 매칭용 이름 목록(짧은 이름 포함)
  start-type LEDGER 01                                     유형 시작(01→10 순서 강제)
  add LEDGER KIND --json '{...}' | --file records.jsonl    기록 추가(시각 자동, 진행 중 유형만)
  todo LEDGER [TYPE]                                       남은 작업
  finish-type LEDGER 01 [--partial-reason 사유 | --abandon 사유]
  audit LEDGER [--json]                                    0=COMPLETE 1=PARTIAL 2=FAIL
  report LEDGER OUT.md                                     휴대폰 요약·유형별 상태·공고 목록

검사는 기록의 존재·정합성만 확인한다. 실제 열람 여부와 원문 일치는 표본 대조(spotcheck)와 사람의 확인으로 본다.
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

SCHEMA = '1.2.1'
KST = dt.timezone(dt.timedelta(hours=9))
HERE = Path(__file__).resolve().parent

CH_DONE = {'posting_checked', 'page_checked', 'search_only', 'searched_no_match', 'access_blocked', 'not_applicable',
           'shared', 'covered_by_type_search', 'covered_by_entity_search', 'covered_by_registry'}
CH_EVIDENCE = {'posting_checked', 'page_checked', 'search_only', 'searched_no_match', 'access_blocked'}
REL_DONE = {'verified', 'excluded_verified', 'searched_unresolved', 'access_blocked', 'verified_cached'}
REVISIT_RESULTS = {'ok', 'redirected', 'closed', 'gone', 'blocked'}
EXCLUDE_CODES = {'duplicate', 'closed', 'condition_mismatch', 'irrelevant_jd', 'detail_blocked', 'out_of_scope'}
POSTER = {'direct', 'parent', 'agency'}
JOB_STATUS = {'open_verified', 'closed_verified', 'unknown_conflict', 'unknown'}
OPEN_KINDS = {'deadline_date', 'always_open_label', 'apply_open_label'}
CONDITION_FIT = {'match', 'mismatch', 'check'}
METHODS = {'browser', 'platform_search', 'web_search', 'fetch'}
CLASSIFIERS = {'manual', 'code'}
JOB_TEXT_FIELDS = ['title', 'hiring_entity', 'poster_entity', 'location', 'career', 'employment_type', 'deadline',
                   'url', 'fit_reason']
KINDS = ['candidate', 'channel', 'revisit', 'search', 'discovered', 'decision', 'job', 'spotcheck']


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


def host(u):
    try:
        return (urlsplit(u).hostname or '').lower().removeprefix('www.').removeprefix('m.')
    except (ValueError, AttributeError):
        return ''


def ne(v, n=1):
    return isinstance(v, str) and len(v.strip()) >= n


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


def scope_of(C):
    return {ch['id']: ch['scope'] for ch in C['channels']}


def match_names(c):
    """매칭에 쓸 이름. 길이로 거르지 않는다(쏘카·모빈·타다·딜리 누락 방지)."""
    out = []
    for n in [c.get('brand_name', '')] + re.split(r'\s*/\s*', c.get('legal_hint', '') or '') + list(c.get('aliases', [])):
        for part in [re.sub(r'\(.*?\)', '', n).strip()] + re.findall(r'\((.*?)\)', n) + re.split(r'\s*·\s*', n):
            part = part.strip()
            if part and part not in out:
                out.append(part)
    return out


# ---------------------------------------------------------------- 장부 생성 / 이전 자료

def fresh(entry, run_date, days):
    try:
        d = dt.date.fromisoformat((entry or {}).get('verified_at', '')[:10])
    except ValueError:
        return False
    return 0 <= (run_date - d).days <= days


def new_ledger(C, registry=None):
    t0 = now()
    reg = registry or {}
    days = C['registry']['recheck_days']
    sc = scope_of(C)
    L = {'schema_version': SCHEMA, 'run_started_at': t0.isoformat(),
         'types': [{'type_id': t['type_id'], 'seq': t['seq'], 'category': t['category'], 'status': 'not_started',
                    'started_at': None, 'finished_at': None, 'partial_reason': '', 'abandon_reason': ''}
                   for t in sorted(C['types'], key=lambda x: x['seq'])],
         'baseline': {'source_file': None, 'targets': []}, 'registry': reg, 'turn_plan': [],
         'candidates': [], 'channels': [], 'discovery_plan': [],
         'revisits': [], 'searches': [], 'discovered': [], 'decisions': [], 'jobs': [], 'spotchecks': []}
    rows = [dict(c, origin='contract') for c in C['candidates']]
    for cid, e in reg.items():
        if e.get('origin') in ('discovered', 'carried') and e.get('type_id'):
            rows.append({'id': cid, 'type_id': e['type_id'], 'category': '', 'brand_name': e.get('brand_name', cid),
                         'legal_hint': e.get('legal_name', ''), 'origin': 'carried'})
    for c in rows:
        e = reg.get(c['id'])
        cached = fresh(e, t0.date(), days) and e.get('status') == 'verified'
        rec = {'id': c['id'], 'type_id': c['type_id'], 'brand_name': c['brand_name'], 'legal_hint': c['legal_hint'],
               'origin': c['origin'], 'relation_status': 'unsearched', 'resolved_company_id': '',
               'relation_evidence_url': '', 'queries': [], 'note': '', 'at': None}
        if cached:
            rec.update(relation_status='verified_cached', resolved_company_id=e.get('resolved_company_id', ''),
                       relation_evidence_url=e.get('relation_evidence_url', ''),
                       note=f'법인 등록부 재사용(확인일 {e.get("verified_at")})')
        L['candidates'].append(rec)
        if c['origin'] == 'contract':
            for ch in C['channels']:
                L['channels'].append({'candidate_id': c['id'], 'channel_id': ch['id'], 'type_id': c['type_id'],
                                      'scope': sc[ch['id']], 'status': 'unsearched', 'query': '', 'url': '',
                                      'route_hint': (e or {}).get('routes', {}).get(ch['id'], ''),
                                      'alternative_url': '', 'relevant_found': None, 'note': '', 'at': None})
        if not cached:
            L['discovery_plan'].append({'task_id': 'E-' + c['id'], 'type_id': c['type_id'], 'candidate_id': c['id'],
                                        'kind': 'entity', 'channel_id': 'web',
                                        'suggested_query': f"{c['brand_name']} {c['legal_hint']} 채용"})
    for t in C['types']:
        for qi, q in enumerate(t['unanchored_queries'], 1):
            for ch in C['discovery']['keyword_channels']:
                L['discovery_plan'].append({'task_id': f"U-{t['type_id']}-{qi}-{ch}", 'type_id': t['type_id'],
                                            'candidate_id': None, 'kind': 'unanchored', 'channel_id': ch,
                                            'suggested_query': q})
    return L


URL_RE = re.compile(r'https?://[^\s,;)\]]+')


def url_kind(u):
    if re.search(r'search|searchword', u):
        return 'search_page'
    if re.search(r'GI_Read|rec_idx|/wd/\d|/job/|/jobs/\d|recruitment/|view/\d|gh_jid|/posting|job_posting', u):
        return 'job_posting'
    return 'company_page'


def targets_from_xlsx(path, C):
    try:
        import openpyxl
    except ImportError:
        die('xlsx를 읽으려면 openpyxl이 필요합니다 (pip install openpyxl).')
    cands = C['candidates']
    toks = sorted(((n, c) for c in cands for n in match_names(c) if len(n) >= 2), key=lambda x: -len(x[0]))
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
    return targets, errors, {}, {}


def from_ledger(path, C):
    """이전 장부에서 재방문 대상·이월 항목·법인 등록부를 만든다."""
    P = load(path)
    sc = scope_of(C)
    out, seen = [], set()

    def add(u, tid, cid, kind, why):
        if url_ok(u) and tid and tid != '00' and u not in seen:
            seen.add(u)
            out.append({'target_id': f'T{len(out) + 1:04d}', 'type_id': tid, 'candidate_id': cid,
                        'assigned_by': 'previous_ledger', 'url': u, 'kind': kind, 'source_sheets': [why],
                        'assign_reason': ''})
    rv = {r.get('target_id'): r for r in P.get('revisits', [])}
    dec = {d.get('disc_id'): d for d in P.get('decisions', [])}
    closed_urls = {d.get('url') for d in P.get('discovered', [])
                   if dec.get(d.get('disc_id'), {}).get('reason_code') == 'closed'}
    # 1) 미판정·상세 차단 공고 이월
    for d in P.get('discovered', []):
        x = dec.get(d.get('disc_id'))
        if d.get('relevant') and (x is None or x.get('outcome') not in ('job', 'excluded')
                                  or x.get('reason_code') == 'detail_blocked'):
            add(d.get('url'), d.get('type_id'), None, 'job_posting', 'carryover:undecided_or_blocked')
    # 2) 이전 재방문 대상 중 마감·소멸이 아닌 것
    for t in P.get('baseline', {}).get('targets', []):
        r = rv.get(t.get('target_id'), {})
        if r.get('result') in ('closed', 'gone') or t.get('url') in closed_urls:
            continue
        add(r.get('final_url') or t.get('url'), t.get('type_id'), t.get('candidate_id'), t.get('kind', 'company_page'),
            'carryover:baseline_' + (r.get('result') or 'not_visited'))
    # 3) 모집 중·불명 공고의 출처
    for j in P.get('jobs', []):
        if j.get('status') != 'closed_verified':
            for s in j.get('sources', []):
                add(s.get('url'), j.get('type_id'), None, 'job_posting', 'carryover:job')
    # 법인 등록부
    has_reg = 'registry' in P
    reg = dict(P.get('registry') or {})
    for c in ([] if has_reg else P.get('candidates', [])):
        if c.get('relation_status') == 'verified' and url_ok(c.get('relation_evidence_url')) and ts(c.get('at')):
            e = reg.setdefault(c['id'], {})
            e.update(status='verified', brand_name=c.get('brand_name'), type_id=c.get('type_id'),
                     resolved_company_id=c.get('resolved_company_id'), legal_name=c.get('resolved_company_id'),
                     relation_evidence_url=c.get('relation_evidence_url'), verified_at=c['at'][:10],
                     origin='carried' if c.get('origin') in ('discovered', 'carried') else 'contract')
            e.setdefault('routes', {})
    for ch in ([] if has_reg else P.get('channels', [])):
        if ch.get('status') in ('page_checked', 'posting_checked') and url_ok(ch.get('url')) \
                and sc.get(ch.get('channel_id')) in ('company', 'entity') and ch.get('candidate_id') in reg:
            reg[ch['candidate_id']].setdefault('routes', {})[ch['channel_id']] = ch['url']
    prev_disc = Counter(d.get('type_id') for d in P.get('discovered', []) if d.get('relevant'))
    return out, [], reg, dict(prev_disc)


def cmd_init(a):
    C = find_contract(a.contract)
    if Path(a.ledger).exists():
        die(f'{a.ledger} 이미 존재. 장부를 덮어쓰거나 다시 만들지 않습니다. 이어서 할 때는 이 파일로 next를 실행하세요.')
    targets, errors, reg, prev = [], [], {}, {}
    src = Path(a.baseline) if a.baseline else None
    if src:
        targets, errors, reg, prev = (targets_from_xlsx(src, C) if src.suffix.lower() in ('.xlsx', '.xlsm')
                                      else from_ledger(src, C))
    L = new_ledger(C, reg)
    L['baseline'] = {'source_file': src.name if src else None, 'targets': targets, 'import_errors': errors,
                     'prev_discovered_by_type': prev}
    make_plan(L, C, C['execution']['turn_budget'])
    save(a.ledger, L)
    un = [x for x in targets if x['type_id'] is None]
    cached = sum(1 for c in L['candidates'] if c['relation_status'] == 'verified_cached')
    print(f'장부 생성: 후보 {len(L["candidates"])} (등록부 재사용 {cached}), 채널 {len(L["channels"])}, '
          f'발굴 작업 {len(L["discovery_plan"])}, 재방문·이월 대상 {len(targets)} (유형 미배정 {len(un)})')
    if un:
        print('유형 미배정 대상은 assign-baseline으로 01~10 또는 00(유형 외:사유)을 지정해야 start-type이 가능합니다.')
        for x in un[:15]:
            print(f'  {x["target_id"]} {x["url"]} ({",".join(x["source_sheets"])})')
        if len(un) > 15:
            print(f'  ... 외 {len(un) - 15}건 (todo로 전체 확인)')
    print_plan(L)


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
    make_plan(L, find_contract(a.contract), L.get('turn_budget') or find_contract(a.contract)['execution']['turn_budget'])
    save(a.ledger, L)
    print(f'지정 완료. 남은 미배정 {sum(1 for t in L["baseline"]["targets"] if t["type_id"] is None)}건')


# ---------------------------------------------------------------- 턴 계획

def estimate(L, C, tid):
    cands = [c for c in L['candidates'] if c['type_id'] == tid]
    company_ch = sum(1 for ch in C['channels'] if ch['scope'] == 'company')
    seen_ids = {c['resolved_company_id'] for c in L['candidates']
                if c['type_id'] < tid and c['resolved_company_id']}
    company = sum(company_ch for c in cands if not (c['resolved_company_id'] and c['resolved_company_id'] in seen_ids))
    entity = sum(1 for p in L['discovery_plan'] if p['type_id'] == tid and p['kind'] == 'entity')
    keyword = sum(1 for p in L['discovery_plan'] if p['type_id'] == tid and p['kind'] == 'unanchored')
    revisit = sum(1 for t in L['baseline']['targets'] if t['type_id'] == tid)
    new = L['baseline'].get('prev_discovered_by_type', {}).get(tid) or C['execution']['default_new_discoveries_per_type']
    return {'company': company, 'entity': entity, 'keyword': keyword, 'revisit': revisit, 'detail': new,
            'total': company + entity + keyword + revisit + new}


def make_plan(L, C, budget):
    L['turn_budget'] = budget
    turns, cur, load_ = [], [], 0
    for t in sorted(L['types'], key=lambda x: x['seq']):
        e = estimate(L, C, t['type_id'])
        if cur and load_ + e['total'] > budget:
            turns.append({'turn': len(turns) + 1, 'types': cur, 'estimate': load_})
            cur, load_ = [], 0
        cur.append(t['type_id'])
        load_ += e['total']
    if cur:
        turns.append({'turn': len(turns) + 1, 'types': cur, 'estimate': load_})
    L['turn_plan'] = turns
    L['type_estimates'] = {t['type_id']: estimate(L, C, t['type_id']) for t in L['types']}


def print_plan(L):
    print(f'턴 계획 (턴당 예상 웹 작업 {L["turn_budget"]}건 기준, 유형 경계에서 끊음)')
    for t in L['turn_plan']:
        print(f'  턴 {t["turn"]}: 유형 {", ".join(t["types"])} · 예상 {t["estimate"]}건')
    print('  (웹 작업 = 페이지 열기 + 검색. 상세 열람 수는 이전 회차 발견량 기준 추정)')


def cmd_plan(a):
    L = load(a.ledger)
    C = find_contract(a.contract)
    if any(t['status'] != 'not_started' for t in L['types']) and a.budget:
        die('조사 시작 후에는 턴 계획을 바꿀 수 없습니다.')
    if a.budget:
        make_plan(L, C, a.budget)
        save(a.ledger, L)
    print_plan(L)
    for tid, e in L['type_estimates'].items():
        print(f'  {tid}: 기업별 채널 {e["company"]} · 법인 {e["entity"]} · 키워드 {e["keyword"]} · 재방문 {e["revisit"]} '
              f'· 상세(추정) {e["detail"]} = {e["total"]}')


def current_turn(L):
    st = {t['type_id']: t['status'] for t in L['types']}
    for t in L['turn_plan']:
        if any(st[x] in ('not_started', 'in_progress') for x in t['types']):
            return t
    return None


def cmd_next(a):
    L = load(a.ledger)
    C = find_contract(a.contract)
    t = current_turn(L)
    if not t:
        print('모든 유형 종료. 다음: audit → report → 장부·보고서 파일 전달.')
        return
    act = active_type(L)
    nxt = act or next(x for x in sorted(L['types'], key=lambda x: x['seq']) if x['status'] == 'not_started')
    print(f'현재 턴 {t["turn"]}/{len(L["turn_plan"])}: 유형 {", ".join(t["types"])}')
    if not act:
        if any(x['type_id'] is None for x in L['baseline']['targets']):
            print('먼저: 유형 미배정 재방문 대상 지정(assign-baseline). todo로 목록 확인.')
            return
        print(f'다음 행동: start-type {nxt["type_id"]}')
        return
    print(f'진행 중: 유형 {act["type_id"]} {act["category"]}')
    print_todo(L, act['type_id'], C, limit=25)
    print(f'이 유형이 끝나면 finish-type {act["type_id"]}. '
          + ('이 유형이 이번 턴의 마지막입니다. 종료 후 장부를 저장하고 멈추세요.' if act['type_id'] == t['types'][-1] else ''))


def cmd_names(a):
    L = load(a.ledger)
    data = {c['id']: match_names(c) for c in L['candidates']}
    if a.json:
        print(json.dumps(data, ensure_ascii=False))
    else:
        for k, v in data.items():
            print(k, ' | '.join(v))


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
            if ne(rec.get('recheck_reason')):
                rec.setdefault('relation_status', 'unsearched')
                if not any(p['task_id'] == 'E-' + row['id'] for p in L['discovery_plan']):
                    L['discovery_plan'].append({'task_id': 'E-' + row['id'], 'type_id': tid, 'candidate_id': row['id'],
                                                'kind': 'entity', 'channel_id': 'web',
                                                'suggested_query': f"{row['brand_name']} {row['legal_hint']} 채용"})
            row.update(rec)
        else:
            if not ne(rec.get('id')) or not ne(rec.get('brand_name')):
                die('신규 후보는 id·brand_name 필요')
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
                          'revisit': (None, None, 'revisits'), 'decision': (None, None, 'decisions'),
                          'spotcheck': (None, None, 'spotchecks')}[kind]
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
    shown = ids if len(ids) <= 12 else ids[:6] + [f'... 외 {len(ids) - 6}건']
    print(f'기록 {len(ids)}건: ' + ', '.join(shown))


# ---------------------------------------------------------------- 파생 칸(유형 검색·법인 검색·등록부)

def derive_map(L, C, tid):
    """scope=type/entity 칸 중 미조사로 남은 것 가운데 실제 수행 기록으로 채울 수 있는 칸: {(cid, ch): (status, 근거)}"""
    done_tasks = defaultdict(set)
    for s in L.get('searches', []):
        if s.get('task_id'):
            done_tasks[s['task_id']].add(s.get('search_id'))
    plan = [p for p in L.get('discovery_plan', []) if p['type_id'] == tid]
    reg = L.get('registry') or {}
    days = C['registry']['recheck_days']
    run_date = ts(L['run_started_at']).date()
    rel = {c['id']: c.get('relation_status') for c in L.get('candidates', [])}
    out = {}
    for x in L.get('channels', []):
        if x.get('type_id') != tid or x.get('status') != 'unsearched':
            continue
        new = None
        if x.get('scope') == 'type':
            tasks = [p['task_id'] for p in plan if p['kind'] == 'unanchored' and p['channel_id'] == x['channel_id']]
            if tasks and all(done_tasks.get(t) for t in tasks):
                new = ('covered_by_type_search', ','.join(sorted(s for t in tasks for s in done_tasks[t])))
        elif x.get('scope') == 'entity':
            e = 'E-' + x['candidate_id']
            if done_tasks.get(e):
                new = ('covered_by_entity_search', ','.join(sorted(done_tasks[e])))
            elif rel.get(x['candidate_id']) == 'verified_cached' and fresh(reg.get(x['candidate_id']), run_date, days):
                new = ('covered_by_registry', '법인 등록부 확인일 ' + reg[x['candidate_id']].get('verified_at', ''))
        if new:
            out[(x['candidate_id'], x['channel_id'])] = new
    return out


def derive_cells(L, C, tid, write_at):
    m = derive_map(L, C, tid)
    for x in L.get('channels', []):
        k = (x['candidate_id'], x['channel_id'])
        if k in m:
            x.update(status=m[k][0], covered_by=m[k][1], at=write_at, note=f'{m[k][0]}: {m[k][1]}')
    return len(m)


# ---------------------------------------------------------------- 감사

def evaluate(L, C, only=None, at_time=None):
    errs = []
    miss, part, unres = defaultdict(list), defaultdict(list), defaultdict(list)
    stats = defaultdict(Counter)
    tnow = at_time or now()
    ex = C['execution']
    types = {t['type_id']: t for t in L.get('types', [])}
    type_ids = [t['type_id'] for t in sorted(C['types'], key=lambda x: x['seq'])]
    run_start = ts(L.get('run_started_at'))
    if not run_start:
        return {'verdict': 'FAIL', 'errors': ['run_started_at 없음'], 'types': {}, 'type_status_count': {}}
    reg = L.get('registry') or {}
    days = C['registry']['recheck_days']

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

    def need_evidence(tid, rec, label, blocked=False):
        if rec.get('method') not in METHODS:
            miss[tid].append(f'{label}: method(browser/platform_search/web_search/fetch) 없음')
            return
        stats[tid]['method_' + rec['method']] += 1
        if not ne(rec.get('evidence'), 8):
            miss[tid].append(f'{label}: evidence(화면 문구·결과 제목·오류 메시지 8자 이상) 없음')

    def need_classifier(tid, rec, label):
        if rec.get('classified_by') not in CLASSIFIERS:
            miss[tid].append(f'{label}: classified_by(manual/code) 없음')
        else:
            stats[tid]['by_' + rec['classified_by']] += 1

    disc_by_via = Counter(d.get('found_via') for d in L.get('discovered', []))

    def check_found(tid, via, n, label):
        if not isinstance(n, int) or n < 0:
            miss[tid].append(f'{label}: relevant_found(본 관련 공고 수) 미기재')
        elif disc_by_via[via] < n:
            miss[tid].append(f'{label}: 관련 공고 {n}건 확인했으나 발견 목록 등록 {disc_by_via[via]}건')

    # 0) 사후 일괄 기록 감지
    rec_times = defaultdict(set)
    for k in ('candidates', 'channels', 'revisits', 'searches', 'discovered', 'decisions', 'jobs', 'spotchecks'):
        for r in L.get(k, []):
            if r.get('at') and not str(r.get('status', '')).startswith('covered_by'):
                rec_times[r.get('type_id')].add(r['at'])
    for tid in type_ids:
        t = types.get(tid) or {}
        if tid in win and t.get('status') not in ('in_progress', 'not_started') and rec_times[tid]:
            mins = (win[tid][1] - win[tid][0]).total_seconds() / 60
            if mins < ex['min_type_minutes'] or len(rec_times[tid]) < ex['min_record_batches']:
                miss[tid].append(f'사후 일괄 기록 의심: 유형 작업 {mins:.1f}분, 기록 시점 {len(rec_times[tid])}회 '
                                 f'(기준 {ex["min_type_minutes"]}분 이상, {ex["min_record_batches"]}회 이상)')

    # 1) 재방문
    rv = {r.get('target_id'): r for r in L.get('revisits', [])}
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
        need_evidence(tid, r, f'재방문 {tg["target_id"]}')
        stats[tid]['revisit_done'] += 1
        if res == 'blocked':
            stats[tid]['blocked'] += 1
            if not url_ok(r.get('alternative_url')):
                part[tid].append(f'재방문 차단·대체 원문 없음 {tg["target_id"]} {tg["url"]}')
        if res in ('ok', 'redirected'):
            check_found(tid, f'revisit:{tg["target_id"]}', r.get('relevant_found'), f'재방문 {tg["target_id"]}')
        if tg.get('kind') == 'job_posting' and res in ('ok', 'redirected', 'closed'):
            posting_urls[tid].add((tg['target_id'], tg['url'], r.get('final_url') or tg['url']))

    # 2) 발굴 계획 ↔ 실행
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
            lbl = f'검색 {s.get("search_id")}'
            if not ne(s.get('query')):
                miss[tid].append(f'{lbl}: query 없음')
                continue
            if p['kind'] == 'unanchored' and s.get('candidate_id'):
                miss[tid].append(f'{lbl}: 기업명 비고정 작업에 candidate_id 지정')
                continue
            need_evidence(tid, s, lbl)
            need_classifier(tid, s, lbl)
            seen, rev = s.get('result_count_seen'), s.get('results_reviewed')
            if not isinstance(rev, int):
                miss[tid].append(f'{lbl}: results_reviewed 미기재')
                continue
            if rev < minrev and not (isinstance(seen, int) and rev >= seen):
                part[tid].append(f'{p["task_id"]}: 검색 결과 {rev}개만 검토(기준 {minrev}개 또는 전체)')
            check_found(tid, f'search:{s.get("search_id")}', s.get('relevant_found'), lbl)
            done = True
        if done:
            stats[tid]['plan_done'] += 1
        else:
            miss[tid].append(f'발굴 검색 미실시 {p["task_id"]} ({p["kind"]}, 예시: {p["suggested_query"]})')

    # 3) 후보 관계 + 등록부
    cand = {c['id']: c for c in L.get('candidates', [])}
    rid = {c['id']: c.get('resolved_company_id') for c in cand.values()}
    for c in cand.values():
        tid = c.get('type_id')
        if tid not in type_ids:
            errs.append(f'후보 {c.get("id")}: 유형 없음')
            continue
        st = c.get('relation_status')
        if st == 'verified_cached':
            stats[tid]['registry_reused'] += 1
            if not fresh(reg.get(c['id']), run_start.date(), days):
                miss[tid].append(f'후보 {c["id"]}: 등록부 기간({days}일) 만료, 재확인 필요')
            continue
        if st not in REL_DONE:
            miss[tid].append(f'법인 관계 미조사 {c["id"]} {c.get("brand_name")}'
                             + (f' (재확인 사유: {c.get("recheck_reason")})' if c.get('recheck_reason') else ''))
        elif in_win(tid, c.get('at'), f'후보 {c["id"]}'):
            stats[tid]['registry_rechecked' if c['id'] in reg else 'relation_new'] += 1
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

    # 4) 채널 768칸 + 신규·이월 후보
    sc = scope_of(C)
    chans = {(x['candidate_id'], x['channel_id']): x for x in L.get('channels', [])}
    derivable = {tid: derive_map(L, C, tid) for tid in type_ids}
    for cid, c in cand.items():
        tid = c.get('type_id')
        if tid not in type_ids:
            continue
        if c.get('origin') in ('discovered', 'carried') and not any(
                k[0] == cid and v.get('status') in CH_EVIDENCE | {'shared'} for k, v in chans.items()):
            miss[tid].append(f'{"신규" if c.get("origin") == "discovered" else "이월"} 후보 {cid}: 채용 경로 기록 없음')
        need = [ch['id'] for ch in C['channels']] if c.get('origin') == 'contract' else []
        for ch in need + [k[1] for k in chans if k[0] == cid and k[1] not in need]:
            x = chans.get((cid, ch))
            stats[tid]['channel_total'] += 1
            if x and x.get('status') == 'unsearched' and (cid, ch) in derivable[tid]:
                x = dict(x, status=derivable[tid][(cid, ch)][0])
            if not x or x.get('status') not in CH_DONE:
                hint = ''
                if x and x.get('route_hint'):
                    hint = f' (등록 경로 {x["route_hint"]})'
                elif sc.get(ch) == 'type':
                    hint = ' (유형 키워드 검색 완료 시 자동 처리)'
                elif sc.get(ch) == 'entity':
                    hint = ' (법인·경로 검색 E 작업 완료 시 자동 처리)'
                miss[tid].append(f'채널 미실시 {cid}/{ch}{hint}')
                continue
            s = x['status']
            stats[tid]['channel_done'] += 1
            stats[tid]['ch_' + s] += 1
            if s.startswith('covered_by'):
                continue
            if not in_win(tid, x.get('at'), f'채널 {cid}/{ch}'):
                continue
            lbl = f'채널 {cid}/{ch}'
            if s == 'shared':
                src = chans.get((x.get('shared_from'), ch))
                if not (src and src.get('status') in CH_EVIDENCE and rid.get(x.get('shared_from'))
                        and rid.get(x.get('shared_from')) == rid.get(cid)):
                    miss[tid].append(f'{lbl}: shared_from이 같은 법인(resolved_company_id)의 확인된 칸이 아님')
                continue
            if s in CH_EVIDENCE:
                need_evidence(tid, x, lbl)
                need_classifier(tid, x, lbl)
            if s in ('posting_checked', 'page_checked'):
                if not url_ok(x.get('url')):
                    miss[tid].append(f'{lbl}: url 없음')
                check_found(tid, f'channel:{cid}/{ch}', x.get('relevant_found'), lbl)
            if s in ('search_only', 'searched_no_match', 'access_blocked') and not (ne(x.get('query')) and ne(x.get('note'))):
                miss[tid].append(f'{lbl}: query·note 없음')
            if s == 'not_applicable' and (ch not in ('group', 'global_careers') or not ne(x.get('note'))):
                miss[tid].append(f'{lbl}: not_applicable은 group·global_careers에 사유와 함께만 허용')
            if s == 'access_blocked':
                stats[tid]['blocked'] += 1
                if not url_ok(x.get('alternative_url')):
                    part[tid].append(f'채널 차단·대체 원문 없음 {cid}/{ch}')
            if c.get('relation_status') == 'verified_cached' and x.get('route_status') in ('gone', 'moved') \
                    and cand[cid].get('relation_status') == 'verified_cached':
                miss[tid].append(f'후보 {cid}: 등록 경로가 사라지거나 이동함 → 법인 재확인 필요'
                                 f'(candidate에 recheck_reason 기록 후 확인)')

    # 5) 공고
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
                if not re.match(r'\d{4}-\d{2}-\d{2}$', (j.get('deadline') or '')[:10]):
                    miss[tid].append(f'공고 {k}: deadline_date 근거인데 deadline이 YYYY-MM-DD로 시작하지 않음')
                elif j['deadline'][:10] < end.date().isoformat():
                    miss[tid].append(f'공고 {k}: 마감일 {j["deadline"]} 지남인데 모집 중')
        if tid in win:
            in_win(tid, j.get('at'), f'공고 {k}')

    # 6) 발견 ↔ 판정, 코드 판정 표본 대조
    vias = {f'revisit:{r.get("target_id")}' for r in L.get('revisits', [])}
    vias |= {f'search:{s.get("search_id")}' for s in L.get('searches', [])}
    vias |= {f'channel:{x["candidate_id"]}/{x["channel_id"]}' for x in L.get('channels', [])}
    decs = defaultdict(list)
    for d in L.get('decisions', []):
        decs[d.get('disc_id')].append(d)
    linked_jobs = set()
    disc_urls = defaultdict(set)
    code_decisions = defaultdict(set)
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
        if x.get('classified_by') not in CLASSIFIERS:
            miss[tid].append(f'판정 {d["disc_id"]}: classified_by(manual/code) 없음')
        else:
            stats[tid]['decision_' + x['classified_by']] += 1
            if x['classified_by'] == 'code':
                code_decisions[tid].add(d['disc_id'])
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
                stats[tid]['detail_blocked'] += 1
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
    spot = defaultdict(list)
    for s in L.get('spotchecks', []):
        spot[s.get('type_id')].append(s)
    for tid in type_ids:
        need = min(ex['spotcheck_per_type'], len(code_decisions[tid]))
        valid = [s for s in spot[tid] if s.get('disc_id') in code_decisions[tid] and isinstance(s.get('agrees'), bool)
                 and ne(s.get('evidence'), 8)]
        if len({s['disc_id'] for s in valid}) < need:
            miss[tid].append(f'코드 판정 표본 대조 {len(valid)}/{need}건 (spotcheck: disc_id, agrees, evidence)')
        for s in valid:
            if not s['agrees']:
                unres[tid].append(f'표본 대조 불일치 {s["disc_id"]}: 코드 판정 재검토 필요 — {s.get("note", "")}')
        stats[tid]['spotcheck'] = len(valid)

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
    sc_ = Counter(r['status'] for r in result.values())
    if errs or sc_['not_done']:
        verdict = 'FAIL'
    elif sc_['partial']:
        verdict = 'PARTIAL'
    else:
        verdict = 'COMPLETE'
    return {'verdict': verdict, 'type_status_count': dict(sc_), 'errors': errs, 'types': result}


def print_todo(L, tid, C, limit=None):
    r = evaluate(L, C, only=tid)['types'][tid]
    items = [x for x in r['not_done'] if not x.startswith('유형 진행 중')]
    groups = Counter(re.split(r'[ :(]', x, 1)[0] for x in items)
    print(f'[{tid} {r["category"]}] 남은 작업 {len(items)}건 ' + (str(dict(groups)) if groups else '')
          + f', 부분 조사 사유 {len(r["partial"])}건, 미확인 {len(r["unresolved"])}건')
    for x in items[:limit] if limit else items:
        print('  - ' + x)
    if limit and len(items) > limit:
        print(f'  ... 외 {len(items) - limit}건 (todo로 전체 확인)')
    for x in r['partial'][:limit] if limit else r['partial']:
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


def update_registry(L, C, tid, when):
    reg = L.setdefault('registry', {})
    sc = scope_of(C)
    for c in L['candidates']:
        if c['type_id'] != tid:
            continue
        e = reg.get(c['id'])
        if c['relation_status'] == 'verified' and url_ok(c.get('relation_evidence_url')):
            e = reg.setdefault(c['id'], {})
            e.update(status='verified', brand_name=c['brand_name'], type_id=tid,
                     resolved_company_id=c['resolved_company_id'],
                     legal_name=c.get('legal_name') or c['resolved_company_id'],
                     relation_evidence_url=c['relation_evidence_url'], verified_at=when[:10],
                     origin='contract' if c.get('origin') == 'contract' else 'carried')
            e.setdefault('routes', {})
        if not e:
            continue
        for x in L['channels']:
            if x['candidate_id'] == c['id'] and sc.get(x['channel_id']) in ('company', 'entity'):
                if x.get('status') in ('page_checked', 'posting_checked') and url_ok(x.get('url')) \
                        and x.get('route_status') not in ('gone', 'moved'):
                    e['routes'][x['channel_id']] = x['url']
                    e['routes_checked_at'] = when[:10]
                elif x.get('route_status') in ('gone', 'moved'):
                    e.get('routes', {}).pop(x['channel_id'], None)


def cmd_finish(a):
    L = load(a.ledger)
    C = find_contract(a.contract)
    t = active_type(L)
    if not t or t['type_id'] != a.type_id:
        die(f'유형 {a.type_id}는 진행 중이 아닙니다.')
    when = now().isoformat()
    t['finished_at'] = when
    t['status'] = 'checking'
    derive_cells(L, C, a.type_id, write_at=when)
    r = evaluate(L, C, only=a.type_id, at_time=ts(when))['types'][a.type_id]
    remaining = [x for x in r['not_done'] if not x.startswith('미완료 종료')]
    if remaining:
        if not a.abandon:
            print(f'[{a.type_id}] 남은 작업 {len(remaining)}건')
            for x in remaining[:40]:
                print('  - ' + x)
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
    update_registry(L, C, a.type_id, when)
    save(a.ledger, L)
    print(f'유형 {a.type_id} 종료: {t["status"]} (공고 {r["counts"].get("jobs", 0)}건, 미확인 {len(r["unresolved"])}건)')
    turn = next((x for x in L['turn_plan'] if a.type_id in x['types']), None)
    nxt = next((x for x in sorted(L['types'], key=lambda x: x['seq']) if x['status'] == 'not_started'), None)
    if not nxt:
        print('모든 유형 종료. audit → report 실행 후 장부·보고서 파일을 전달하세요.')
    elif turn and a.type_id == turn['types'][-1]:
        print(f'턴 {turn["turn"]} 종료. 장부 파일을 저장(다운로드 링크 제공)하고 여기서 멈추세요. '
              f'사용자가 "계속"이라고 하면 next → start-type {nxt["type_id"]}.')
    else:
        print(f'다음: start-type {nxt["type_id"]}')


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
    tot = Counter()
    for r in rep['types'].values():
        tot.update(r['counts'])
    date = (L.get('run_started_at') or '')[:10]
    carried = sum(1 for t in L['baseline']['targets'] if any(s.startswith('carryover') for s in t.get('source_sheets', [])))
    out = [f'# 국내 모빌리티 운영 채용 조사 {date}', '',
           f'**감사 판정: {rep["verdict"]}** · 완료 {sc.get("complete", 0)} / 부분 조사 {sc.get("partial", 0)} / '
           f'미실시 {sc.get("not_done", 0)} (10개 유형)', '',
           f'확인 방법: 직접 열기 {tot["method_browser"]} · 사이트 내부 검색 {tot["method_platform_search"]} · '
           f'외부 검색 {tot["method_web_search"]} · 가져오기 도구 {tot["method_fetch"]}  ',
           f'판정 주체: 직접 판정 {tot["decision_manual"]} · 코드 분류 {tot["decision_code"]} (표본 대조 {tot["spotcheck"]}건)  ',
           f'법인 등록부: 재사용 {tot["registry_reused"]} · 재확인 {tot["registry_rechecked"]} · 신규 확인 {tot["relation_new"]}  ',
           f'이전 회차 이월 대상 {carried}건 · 접근 차단 {tot["blocked"]}건 · 상세 접근 제한 {tot["detail_blocked"]}건', '',
           '## 휴대폰 요약', '']
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
            '| 유형 | 상태 | 재방문 | 발굴 검색 | 채널 768 | 발견→판정 | 등록부 재사용 | 신규 기업 | 공고 | 미확인 |',
            '|---|---|---|---|---|---|---|---|---|---|']
    for tid, r in rep['types'].items():
        c = r['counts']
        st = STATUS_KO[r['status']] + (' (0건)' if r['zero_found'] else '')
        out.append(f'| {tid} {r["category"]} | {st} | {c.get("revisit_done", 0)}/{c.get("revisit_total", 0)} | '
                   f'{c.get("plan_done", 0)}/{c.get("plan_total", 0)} | {c.get("channel_done", 0)}/{c.get("channel_total", 0)} | '
                   f'{c.get("decided", 0)}/{c.get("discovered", 0)} | {c.get("registry_reused", 0)} | '
                   f'{c.get("new_companies", 0)} | {c.get("jobs", 0)} | {len(r["unresolved"])} |')
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
    p = sp.add_parser('plan'); p.add_argument('ledger'); p.add_argument('--budget', type=int); p.set_defaults(f=cmd_plan)
    p = sp.add_parser('next'); p.add_argument('ledger'); p.set_defaults(f=cmd_next)
    p = sp.add_parser('names'); p.add_argument('ledger'); p.add_argument('--json', action='store_true'); p.set_defaults(f=cmd_names)
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
