#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""粉煤灰3075篇技术路径与成熟度统计，复现Fig2/3的关键统计图。

数据来源为作者冻结的3075篇主表和Fig3已保存的报告频率代理指标。
图中的热度、证据频率不表示产业消纳量、成本或真实工程性能。
"""
from pathlib import Path
from collections import Counter
import csv,math,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE=Path(__file__).resolve().parent
DATA=HERE/'inputs'
OUT=HERE/'outputs'/'07_评价图表'
OUT.mkdir(parents=True,exist_ok=True)

CATS={
'建材利用':'Construction materials','环境功能材料':'Environmental functional materials',
'高附加值材料':'High-value-added materials','地聚物与碱激发材料':'Geopolymers/AAMs',
'元素提取':'Element extraction','能源与碳相关利用':'Energy/carbon use',
'生态与回填利用':'Ecological/backfill','协同资源化利用':'Co-utilization',
'Unclear':'Unclear'}
MAT={
'Basic research': 'Basic research','Laboratory preparation':'Laboratory preparation',
'Process optimization':'Process optimization','Application validation':'Application validation',
'Pilot / demonstration':'Pilot/engineering demonstration',
'Commercial / full-scale':'Industrial/commercial application','Unclear':'Unclear'}

def read(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def plot_bar(rows,title,filename):
    names=[r[0] for r in rows][::-1];values=[r[1] for r in rows][::-1]
    fig,ax=plt.subplots(figsize=(11,6))
    bars=ax.barh(names,values,color='#366F9F')
    for b,n in zip(bars,values):ax.text(n+max(values)*.012,b.get_y()+b.get_height()/2,f'{n:,}',va='center',fontsize=9)
    ax.set_xlim(0,max(values)*1.18);ax.set_xlabel('Number of publications')
    ax.set_title(title,fontsize=12);ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
    fig.tight_layout();fig.savefig(OUT/filename,dpi=300,bbox_inches='tight');plt.close(fig)


def main():
    plt.rcParams['font.family']='DejaVu Sans'
    papers=read(DATA/'01_2000-2025_文献基础库_3075篇.csv')
    assert len(papers)==3075
    classes=Counter(r['Primary_Category'] for r in papers)
    maturity=Counter(r['Maturity_EN'] for r in papers)
    assert classes['建材利用']==998 and classes['环境功能材料']==900 and classes['Unclear']==216
    assert maturity['Application validation']==1019 and maturity['Unclear']==297
    plot_bar([(CATS.get(k,k),v) for k,v in classes.most_common()],
             'Coal fly ash dominant valorization pathways','Fig2b_category_counts.png')
    plot_bar([(MAT.get(k,k),v) for k,v in maturity.most_common()],
             'Literature-reported maturity stages','Fig2d_maturity_distribution.png')
    records=read(DATA/'Fig3_3075_aggregates_and_proxy_inputs.csv')
    # Recompute per-pathway lexical reporting counts and maturity means from
    # the SAVED per-paper flag table and compare against frozen Fig3 inputs.
    flags=read(DATA/'Fig3_3075_paper_keyword_flags.csv')
    byroute={}
    for row in flags:byroute.setdefault(row['Subroute'],[]).append(row)
    stage_scores={'基础研究':1,'实验室制备':2,'工艺优化':3,'应用验证':4,
                  '中试/工程示范':5,'产业化/商业化':6}
    flag_map={'Scale reporting':'Scale reporting_N','Value reporting':'Value reporting_N',
              'Environmental reporting':'Environmental reporting_N',
              'Material/energy reporting':'Material/energy reporting_N',
              'Economic reporting':'Economic reporting_N',
              'Engineering reporting':'Engineering reporting_N'}
    for route in records:
        sub=route['Subroute_CN'];subset=byroute.get(sub,[])
        assert len(subset)==int(route['Papers']),f'Fig3 path count mismatch {sub}'
        for evidence_col,count_col in flag_map.items():
            total=sum(int(float(r[evidence_col])) for r in subset)
            assert total==int(route[count_col]),f'Fig3 flag mismatch {sub}/{evidence_col}'
        stages=[stage_scores[r['Maturity_CN']] for r in subset if r['Maturity_CN'] in stage_scores]
        assert len(stages)==int(route['Maturity_assessed']),f'Maturity count mismatch {sub}'
        if stages:assert abs(sum(stages)/len(stages)-float(route['Maturity_mean_1to6']))<1e-8

    # These values are existing min-max normalized author-derived 0-100 reporting indices.
    cols=[('Research_heat_index','Research heat'),('Maturity_index_0to100','Maturity proxy'),
          ('Environmental reporting_index','Environment'),('Material/energy reporting_index','Material/energy'),
          ('Economic reporting_index','Economics'),('Engineering reporting_index','Engineering')]
    series=np.array([[float(r[k]) for k,_ in cols] for r in records])
    fig,ax=plt.subplots(figsize=(12, max(6,len(records)*.43)))
    im=ax.imshow(series,cmap='YlOrRd',vmin=0,vmax=100,aspect='auto')
    ax.set_xticks(range(len(cols)),[name for _,name in cols],rotation=32,ha='right')
    ax.set_yticks(range(len(records)),[r['Subroute_EN'] for r in records]);ax.tick_params(labelsize=8)
    for i in range(series.shape[0]):
        for j in range(series.shape[1]):ax.text(j,i,f'{series[i,j]:.0f}',ha='center',va='center',fontsize=6.5,
            color='white' if series[i,j]>65 else '#272727')
    fig.colorbar(im,ax=ax,label='Min-max normalized reporting index (0–100)')
    fig.tight_layout();fig.savefig(OUT/'Fig3c_evidence_reporting_heatmap.png',dpi=300,bbox_inches='tight');plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,7))
    for r in records:
        x=float(r['Scale_mention_index']);y=float(r['Value_mention_index']);n=float(r['Papers'])
        ax.scatter([x],[y],s=40+n*.5,alpha=.65,edgecolors='white',linewidths=.5)
        ax.annotate(r['Subroute_EN'],(x,y),fontsize=7,xytext=(4,4),textcoords='offset points')
    ax.set_xlabel('Relative scale-reporting index (0–100)')
    ax.set_ylabel('Relative value-reporting index (0–100)')
    ax.set_title('Fig. 3b: bibliographic proxy map (not measured performance)')
    fig.tight_layout();fig.savefig(OUT/'Fig3b_literature_proxy_scatter.png',dpi=300,bbox_inches='tight');plt.close(fig)
    summary={'corpus':len(papers),'primary_categories':dict(classes),'maturity_stages':dict(maturity),
             'subroutes_in_Fig3':len(records),'per_paper_flag_crosscheck':'passed','data_source':'Author-frozen 3075-paper summary and figure-specific Fig3 aggregates',
             'caution':'Not an engineering performance ranking.'}
    (OUT/'reported_statistics.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print('PASS: Fig2b, Fig2d, Fig3b, Fig3c + statistics ->',OUT)
if __name__=='__main__':main()
