#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V2/V3人工复核决策与2000–2025年最终冻结图谱的逐字段审计。

核心来源：真实V2存档21269、V3重放21204、42篇作者排除、5条暂缓
候选与最终19177条。逐行验证，生成审计结果及修订明细。真实V2/V3
原始Python完整源码另以historical_sources/*.txt附档（即代码文本）。
不会使用AI自动推测审稿人/作者作出的人工判断。
"""
from pathlib import Path
import csv,json,hashlib
from collections import Counter
ROOT=Path(__file__).resolve().parent;DATA=ROOT/'inputs';OUT=ROOT/'outputs'/'04_V2V3复核'

def read(n):
    path=DATA/n
    with path.open('r',encoding='utf-8-sig',newline='') as f:
        rdr=csv.DictReader(f);return rdr.fieldnames,list(rdr)

def key(row):return (row['Paper_ID'],row['Source'],row['Relation'],row['Target'])

def same_rows(actual,reference):
    columns=list(reference[0])
    ca=Counter(tuple((r.get(c,'') or '') for c in columns) for r in actual)
    cr=Counter(tuple((r.get(c,'') or '') for c in columns) for r in reference)
    if ca!=cr:
        raise ValueError(f'FULL-ROW mismatch: extra {(ca-cr).total()} missing {(cr-ca).total()}')

def dump(file,columns,rows):
    with file.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=columns,extrasaction='ignore');w.writeheader();w.writerows(rows)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    _,v2=read('V2_作者已确认主图谱_21269条.csv')
    v3_cols,v3=read('V3_作者修订后_21204条.csv')
    cols3422,ref3422=read('V3_3422篇_20858条.csv')
    _,removed=read('42篇作者确认排除名单.csv')
    finalcols,final=read('02_2000-2025_图谱三元组_19177条.csv')
    _,papers=read('01_2000-2025_文献基础库_3075篇.csv')
    _,edges=read('04_2000-2025_聚合关系边_198条.csv')
    assert len(v2)==21269 and len(v3)==21204 and len(removed)==42
    eids={r['Paper_ID'] for r in removed};assert len(eids)==42
    held=[r for r in v3 if r.get('V3_Action','').startswith('作者确认更正方向')]
    assert len(held)==5
    after42=[r for r in v3 if r['Paper_ID'] not in eids]
    afterheld=[r for r in after42 if not r.get('V3_Action','').startswith('作者确认更正方向')]
    assert len(after42)==20863 and len(afterheld)==20858
    same_rows(afterheld,ref3422)
    kept_ids={r['Paper_ID'] for r in papers}
    kept=[r for r in afterheld if r['Paper_ID'] in kept_ids]
    same_rows(kept,final)
    assert len(papers)==3075 and len(kept)==19177
    calc=Counter((r['Source'],r['Relation'],r['Target']) for r in kept)
    saved={(r['Source'],r['Relation'],r['Target']):int(r['Weight']) for r in edges}
    assert len(calc)==198 and calc==saved
    # Report V2/V3 author-approved changes without assuming candidate keys are all valid.
    v2keys=Counter(key(r) for r in v2);v3keys=Counter(key(r) for r in v3)
    actions=Counter(r.get('V3_Action','') for r in v3)
    report={'V2_approved':len(v2),'V3_after_author_revision':len(v3),
        'V2_only_relation_keys':sum((v2keys-v3keys).values()),
        'V3_only_relation_keys':sum((v3keys-v2keys).values()),
        'V3_action_counts':dict(actions),'author_scope_excluded_papers':42,
        'V3_after_scope_exclusions':len(after42),'five_held_candidate_relations':len(held),
        'V3_after_holding_candidates':len(afterheld),'outside_window_relation_supports':len(afterheld)-len(kept),
        'final_papers':len(papers),'final_relations':len(final),'final_edges':len(calc),
        'full_row_equality_to_frozen':True,'edge_weight_equality':True,
        'caution':'Replays recorded decisions; does NOT reconstruct or authenticate unrecorded human judgments.'}
    dump(OUT/'V3_待核候选5条.csv',v3_cols,held)
    dump(OUT/'最终3075篇三元组复核输出.csv',finalcols,kept)
    (OUT/'V2V3_审核链条.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='V3_action_counts'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
