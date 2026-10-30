#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WM-26-2894 | final paper-linked knowledge-graph deterministic aggregation.

Input is a *frozen author-corrected* 2000–2025 corpus and triple-support table.
This script validates ID links, publication year, unique supports, recomputes
weighted directed edges, nodes, relation reports, and optionally GraphML.

This does NOT create V2/V3 review decisions or independently verify semantics.

Run:
  python 02_rebuild_final_KG_3075.py \
    --papers inputs/01_2000-2025_文献基础库_3075篇.csv \
    --triples inputs/02_2000-2025_图谱三元组_19177条.csv \
    --compare-edges inputs/04_2000-2025_聚合关系边_198条.csv --strict
"""
import argparse,csv,json,collections,hashlib,sys
from pathlib import Path

PAPER_ID=('Paper_ID','Paper ID','paper_id','ID')
YEAR=('Year','Year_clean','Publication Year','year')
SRC=('Source','Source_Entity','source')
REL=('Relation','Predicate','relation')
DST=('Target','Target_Entity','target')
SW=('Weight','weight','Triple_Count','Support_Count')

def load(path):
    with open(path,'r',encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        if not reader.fieldnames:raise ValueError(f'Empty header: {path}')
        rows=[{(k or '').strip(): str(v or '').strip() for k,v in row.items()} for row in reader]
    return rows

def field(rows,aliases,path):
    if not rows:raise ValueError(f'Empty input file {path}')
    for v in aliases:
        if v in rows[0]:return v
    raise ValueError(f'Missing one of columns {aliases} in {path}: {list(rows[0])}')

def write(path,records,columns):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=columns,extrasaction='ignore');w.writeheader();w.writerows(records)

def weight_num(x):
    try: return int(float(x))
    except ValueError:return -1

def audit(papers,triples,expected_edges=None,strict=False):
    pk=field(papers,PAPER_ID,'papers');yk=field(papers,YEAR,'papers')
    tk=field(triples,PAPER_ID,'triples');sk=field(triples,SRC,'triples');rk=field(triples,REL,'triples');dk=field(triples,DST,'triples')
    pids=[r[pk] for r in papers]
    if len(set(pids))!=len(pids):raise ValueError('Duplicate Paper_ID within frozen corpus')
    if not all(2000<=int(r[yk])<=2025 for r in papers if r[yk].isdigit()):
        raise ValueError('Publication year outside 2000–2025 detected')
    if any(not r[yk].isdigit() for r in papers):raise ValueError('Missing/non-numeric Year in final corpus')
    ps=set(pids)
    orphan=[r[tk] for r in triples if r[tk] not in ps]
    if orphan:raise ValueError(f'{len(orphan)} triples reference excluded Paper_IDs, examples: {orphan[:5]}')
    key_set=set();duplicates=[]; edges=collections.defaultdict(set); relation_counts=collections.Counter()
    node_stat=collections.Counter();node_types=collections.defaultdict(collections.Counter)
    fromclass=('Source_Type','SourceType');toclass=('Target_Type','TargetType')
    source_type=next((v for v in fromclass if v in triples[0]),None)
    target_type=next((v for v in toclass if v in triples[0]),None)
    for r in triples:
        p=r[tk];src=r[sk];rel=r[rk];tar=r[dk]
        if not src or not rel or not tar:raise ValueError(f'Empty graph relation in record {r}')
        key=(p,src,rel,tar)
        if key in key_set:duplicates.append(key)
        key_set.add(key)
        edges[(src,rel,tar)].add(p)
        relation_counts[rel]+=1
        node_stat[src]+=1;node_stat[tar]+=1
        if source_type and r[source_type]:node_types[src][r[source_type]]+=1
        if target_type and r[target_type]:node_types[tar][r[target_type]]+=1
    if duplicates:raise ValueError(f'{len(duplicates)} duplicate paper-linked (Paper_ID,Source,Relation,Target) keys; review dedup logic first. Example {duplicates[:2]}')
    edge_rows=[{'Source':a,'Relation':b,'Target':c,'Weight':len(ids),'Paper_Count':len(ids)}
             for (a,b,c),ids in edges.items()]
    edge_rows.sort(key=lambda r:(-r['Weight'],r['Source'],r['Relation'],r['Target']))
    node_rows=[{'Node':n,'Frequency':f,'Node_Type':(node_types[n].most_common(1)[0][0] if node_types[n] else '')}
               for n,f in node_stat.items()]
    node_rows.sort(key=lambda r:(-r['Frequency'],r['Node']))
    rel_rows=[{'Relation':k,'Support_Instances':v,'Unique_Source_Papers':len({r[tk] for r in triples if r[rk]==k})}
              for k,v in sorted(relation_counts.items(),key=lambda t:-t[1])]
    if expected_edges:
        ek=field(expected_edges,SRC,'expected edges');rk_e=field(expected_edges,REL,'expected edges');dk_e=field(expected_edges,DST,'expected edges')
        wk=field(expected_edges,SW,'expected edges')
        expected={(r[ek],r[rk_e],r[dk_e]):weight_num(r[wk]) for r in expected_edges}
        calculated={(r['Source'],r['Relation'],r['Target']):r['Weight'] for r in edge_rows}
        if expected!=calculated:
            missing=set(expected)-set(calculated);added=set(calculated)-set(expected)
            differing=[(k,expected[k],calculated[k]) for k in expected.keys()&calculated.keys() if expected[k]!=calculated[k]]
            raise ValueError(f'Frozen edge comparison FAILED; missing={list(missing)[:4]}, new={list(added)[:4]}, weight_differences={differing[:5]}')
    status={'papers':len(papers),'papers_with_supports':len({r[tk] for r in triples}),
            'paper_linked_relation_supports':len(triples),'distinct_aggregate_edges':len(edge_rows),
            'weight_sum':sum(x['Weight'] for x in edge_rows),'nodes':len(node_rows),
            'publication_period':'2000-2025','edge_comparison': 'matched' if expected_edges else 'not_provided',
            'scope':'Data and weight validation, NOT independent relation-level scientific precision assessment'}
    if strict and (status['papers'],status['paper_linked_relation_supports'],status['distinct_aggregate_edges'])!=(3075,19177,198):
        raise ValueError(f'STRICT FROZEN COUNTS FAILED: actual = {status}; expected papers=3075 supports=19177 aggregate_edges=198')
    return edge_rows,node_rows,rel_rows,status

def main():
    pa=argparse.ArgumentParser();pa.add_argument('--papers',default=str(Path(__file__).resolve().parent/'inputs'/'01_2000-2025_文献基础库_3075篇.csv'));pa.add_argument('--triples',default=str(Path(__file__).resolve().parent/'inputs'/'02_2000-2025_图谱三元组_19177条.csv'))
    pa.add_argument('--compare-edges',default=str(Path(__file__).resolve().parent/'inputs'/'04_2000-2025_聚合关系边_198条.csv'));pa.add_argument('--out',default=str(Path(__file__).resolve().parent/'outputs'/'05_最终图谱'));pa.add_argument('--strict',action='store_true',default=True);arg=pa.parse_args()
    papers=load(arg.papers);tri=load(arg.triples)
    comp=load(arg.compare_edges) if arg.compare_edges else None
    edges,nodes,rels,stats=audit(papers,tri,comp,strict=arg.strict)
    dest=Path(arg.out);dest.mkdir(parents=True,exist_ok=True)
    write(dest/'kg_3075_edges_recomputed.csv',edges,['Source','Relation','Target','Weight','Paper_Count'])
    write(dest/'kg_3075_nodes_recomputed.csv',nodes,['Node','Frequency','Node_Type'])
    write(dest/'kg_3075_relation_stats.csv',rels,['Relation','Support_Instances','Unique_Source_Papers'])
    stats['inputs_sha256']={x:hashlib.sha256(Path(x).read_bytes()).hexdigest() for x in [arg.papers,arg.triples]+([arg.compare_edges] if arg.compare_edges else [])}
    (dest/'audit_3075.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8')
    try:
        import networkx as nx
        graph=nx.DiGraph()
        for n in nodes:graph.add_node(n['Node'],Frequency=n['Frequency'],node_type=n['Node_Type'])
        for e in edges:
            # Use MultiDiGraph, so parallel relations between same nodes are never dropped.
            pass
        multidigraph=nx.MultiDiGraph()
        for n in nodes:multidigraph.add_node(n['Node'],Frequency=n['Frequency'],node_type=n['Node_Type'])
        for e in edges:multidigraph.add_edge(e['Source'],e['Target'],key=e['Relation'],weight=e['Weight'],relation=e['Relation'])
        nx.write_graphml(multidigraph,dest/'kg_3075_multirelational.graphml')
    except ImportError:
        print('networkx not installed; graphml omitted. CSV & audit are complete.')
    print(json.dumps(stats,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
