#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""使用原始Notebook真实词典匹配材料特性、技术路径和协同因素。

词典逐字读取原始cell44/65/66/68 JSON；输出候选实体及来源文献。
本模块执行词项匹配，不宣称独立验证了关系方向或语义正确性。
"""
from pathlib import Path
import argparse,csv,json,re
from collections import Counter
HERE=Path(__file__).resolve().parent
DEFAULT=HERE/'inputs'/'01_2000-2025_文献基础库_3075篇.csv'
FILES=['KG_original_5_entity_dictionaries.json','Property_Pathway_dictionaries.json',
       'Limiting_factors_dictionary.json','External_synergy_dictionaries.json']

def match_text(text,term):
    term=(term or '').strip().lower()
    if not term:return False
    # Exact word boundaries for ASCII phrases prevent e.g. "Pb" matching arbitrary words.
    patt=r'(?<![a-z0-9])'+re.escape(term)+r'(?![a-z0-9])' if re.search(r'[a-z0-9]',term) else re.escape(term)
    return re.search(patt,text.lower()) is not None

def load_dicts():
    merged=[]
    for name in FILES:
        item=json.loads((HERE/'dict'/name).read_text('utf-8'))
        for subgroup,terms in item['dictionaries'].items():
            for entity,info in terms.items():
                merged.append({'Dictionary':name,'Source_Cell':item.get('cell_zero_based',''),
                               'Subgroup':subgroup,'Entity':entity,
                               'Type':info.get('type',info.get('group','')),
                               'Patterns':info.get('patterns',[])})
    return merged

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--papers',default=str(DEFAULT));ap.add_argument('--out',default=str(HERE/'outputs'/'02_候选实体.csv'))
    ap.add_argument('--include-patterns',action='store_true')
    args=ap.parse_args()
    with open(args.papers,'r',encoding='utf-8-sig',newline='') as f:papers=list(csv.DictReader(f))
    definitions=load_dicts();out=Path(args.out);out.parent.mkdir(exist_ok=True,parents=True)
    termsets=[[(v.lower(),v) for v in d['Patterns'] if v and v.strip()] for d in definitions]
    fields=['Paper_ID','Year','Dictionary','Source_Cell','Subgroup','Entity','Entity_Type','Evidence_Pattern']
    count=0;category=Counter()
    with out.open('w',encoding='utf-8-sig',newline='') as f:
        wr=csv.DictWriter(f,fieldnames=fields);wr.writeheader()
        for paper in papers:
            text=' '.join((paper.get(k,'') or '') for k in ('Title','Abstract','Keywords')).lower()
            for dic,terms in zip(definitions,termsets):
                hit=None
                for low,original in terms:
                    start=text.find(low)
                    if start < 0: continue
                    # Retain matched word-boundary semantics; if first occurrence fails,
                    # search later occurrences before deciding.
                    while start >= 0:
                        end=start+len(low)
                        a=(start==0 or not (text[start-1].isascii() and text[start-1].isalnum()))
                        b=(end==len(text) or not (text[end].isascii() and text[end].isalnum()))
                        if a and b:hit=original;break
                        start=text.find(low,start+1)
                    if hit:break
                if hit:
                    wr.writerow({'Paper_ID':paper.get('Paper_ID',''),'Year':paper.get('Year',''),
                                 'Dictionary':dic['Dictionary'],'Source_Cell':dic['Source_Cell'],
                                 'Subgroup':dic['Subgroup'],'Entity':dic['Entity'],
                                 'Entity_Type':dic['Type'],'Evidence_Pattern':hit})
                    count+=1;category[dic['Subgroup']]+=1
    print(f'{len(papers)} papers; {len(definitions)} dictionary entity definitions; {count} candidate entity matches -> {out}')
    print('These are candidate lexical matches, not V2/V3-reviewed final relationships.')
if __name__=='__main__':main()
