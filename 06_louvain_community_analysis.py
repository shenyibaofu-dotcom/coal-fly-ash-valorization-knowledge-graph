#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""复算WM-26-2894 Fig.5外部关联网络：39节点、104边、5社区、Q≈0.4684。
这是独立于198条主图谱关系边的Figure-specific无向加权网络。"""
from pathlib import Path
from collections import Counter
import csv,json,argparse
import networkx as nx
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE=Path(__file__).resolve().parent
DATA=HERE/'inputs'/'Fig4d_2000to2025_证据来源过滤边表.csv'

def graph_from(counter):
    # 原Fig5算法规则: threshold 20, inadequate candidates then 10 or 5,
    # top65 by weighted degree and at most 110 largest remaining edges.
    edges={k:v for k,v in counter.items() if v>=20}
    if len(edges)<30:edges={k:v for k,v in counter.items() if v>=10}
    if len(edges)<30:edges={k:v for k,v in counter.items() if v>=5}
    net=nx.Graph();net.add_weighted_edges_from((a,b,w) for (a,b),w in edges.items())
    degrees=dict(net.degree(weight='weight'))
    chosen=sorted(degrees,key=degrees.get,reverse=True)[:65]
    net=net.subgraph(chosen).copy()
    result=nx.Graph()
    for u,v,d in sorted(net.edges(data=True),key=lambda x:-x[2]['weight'])[:110]:
        result.add_edge(u,v,weight=int(d['weight']))
    com=nx.community.louvain_communities(result,weight='weight',resolution=1.0,seed=42)
    mod=nx.community.modularity(result,com,weight='weight')
    return result,com,mod

def read_external():
    counter=Counter()
    with DATA.open(encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f):
            k=tuple(sorted([r['Source'],r['Target']]))
            counter[k]+=int(r['After_Excluded_Matched_Weight'])
    return counter

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',default=str(HERE/'outputs'/'06_Louvain网络'))
    args=p.parse_args();out=Path(args.out);out.mkdir(exist_ok=True,parents=True)
    G,C,Q=graph_from(read_external())
    result={'nodes':G.number_of_nodes(),'edges':G.number_of_edges(),'communities':len(C),'modularity_Q':Q,'seed':42,
            'network_scope':'external figure-associated co-mention network; not final 198-edge directed core'}
    if (result['nodes'],result['edges'],result['communities'])!=(39,104,5):
        raise ValueError(f'Unexpected graph topology: {result}')
    if abs(Q-0.46839760766607164)>1e-7:raise ValueError(f'Q mismatch: {Q}')
    membership={node:i+1 for i,c in enumerate(C) for node in c}
    with (out/'nodes_community.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['Node','Community','Weighted_degree'])
        for n,degree in sorted(G.degree(weight='weight'),key=lambda x:-x[1]):w.writerow([n,membership[n],degree])
    with (out/'edges_community.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['Source','Target','Weight','Source_community','Target_community'])
        for a,b,d in G.edges(data=True):w.writerow([a,b,d['weight'],membership[a],membership[b]])
    (out/'louvain_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    # For readable network labels, see original English translation mapping in source archive.
    pos=nx.spring_layout(G,seed=42,weight='weight',iterations=100)
    fig,ax=plt.subplots(figsize=(12,8))
    nodes=list(G)
    cmap=plt.get_cmap('tab10')
    nx.draw_networkx_edges(G,pos,ax=ax,alpha=.18,width=.4,edge_color='#8191A0')
    nx.draw_networkx_nodes(G,pos,nodelist=nodes,ax=ax,node_size=[100+G.degree(n,weight='weight')*.09 for n in nodes],
        node_color=[cmap((membership[n]-1)/10) for n in nodes],alpha=.9,edgecolors='white',linewidths=.7)
    ax.set_axis_off();fig.tight_layout()
    fig.savefig(out/'louvain_network_community.png',dpi=250,bbox_inches='tight')
    plt.close(fig)
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
