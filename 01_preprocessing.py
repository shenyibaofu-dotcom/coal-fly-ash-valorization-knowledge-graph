#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文献读取、字段标准化、DOI/题名去重与年份筛查。

默认使用已冻结的3075篇文献做独立完整性检查和字段清洗，不重新筛选研究对象。
如有原始WoS/Scopus导出CSV，可指定 --raw WOS.csv Scopus.csv 执行新的
去重候选识别；这不等于自动重现历史4938->3075个人工决策。
"""
from pathlib import Path
import argparse, csv, json, re, unicodedata
from collections import Counter

HERE=Path(__file__).resolve().parent
DEFAULT=HERE/'inputs'/'01_2000-2025_文献基础库_3075篇.csv'


def read_csv(path):
    with Path(path).open('r',encoding='utf-8-sig',newline='') as f:
        rd=csv.DictReader(f)
        if not rd.fieldnames: raise ValueError(f'CSV header missing: {path}')
        return [dict(r) for r in rd]

def norm_doi(s):
    s=(s or '').strip().lower()
    return re.sub(r'^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)','',s).strip()

def norm_title(s):
    s=unicodedata.normalize('NFKC',s or '').casefold()
    return re.sub(r'[^\w\u4e00-\u9fff]+','',s,flags=re.UNICODE)

def first(row,names,default=''):
    for x in names:
        if row.get(x) is not None and str(row[x]).strip():return str(row[x]).strip()
    return default

def mapped(row,source=''):
    return {
        'Original_ID':first(row,['Original_ID','UT','EID','Accession Number','ID']),
        'Paper_ID':first(row,['Paper_ID','Paper ID']),
        'Source_Database':source,
        'Title':first(row,['Title','Article Title','Document Title','题名']),
        'Abstract':first(row,['Abstract','Abstract Note','摘要']),
        'Keywords':first(row,['Keywords','Author Keywords','Index Keywords','作者关键词']),
        'DOI':norm_doi(first(row,['DOI','DOI Link'])),
        'Year':first(row,['Year','Publication Year','Year_clean','年份']),
    }

def process(rows,check_frozen=False):
    out=[];seen_doi={};seen_title={};dup=[];by_year=Counter()
    for i,r in enumerate(rows,1):
        doi=norm_doi(r.get('DOI',''));title=norm_title(r.get('Title',''))
        reason=''
        if doi and doi in seen_doi:reason='same DOI'
        elif title and title in seen_title:reason='same normalized title'
        if reason:
            dup.append({'row':i,'Paper_ID':r.get('Paper_ID',''),'DOI':doi,'Title':r.get('Title',''),'Reason':reason});continue
        if doi:seen_doi[doi]=i
        if title:seen_title[title]=i
        out.append(r)
        by_year[r.get('Year','')]+=1
    if check_frozen:
        assert len(rows)==3075,f'Frozen dataset expected 3075 records; got {len(rows)}'
        # Corpus is author-frozen. Any potential duplicate is reported, not removed.
        if len({r['Paper_ID'] for r in rows})!=3075:raise ValueError('Frozen Paper_ID duplicates')
        if not all(str(r['Year']).isdigit() and 2000<=int(r['Year'])<=2025 for r in rows):
            raise ValueError('Final corpus contains Year outside 2000..2025')
    return out,dup,by_year

def write(path,rows,cols):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        wr=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore');wr.writeheader();wr.writerows(rows)

def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--frozen',default=str(DEFAULT),help='默认只检查3075篇冻结文献')
    a.add_argument('--raw',nargs='+',help='提供原始WoS / Scopus CSV后执行独立去重候选识别')
    a.add_argument('--out',default=str(HERE/'outputs'/'01_预处理'))
    args=a.parse_args()
    if args.raw:
        rows=[]
        for name in args.raw:
            src=Path(name).stem
            rows.extend(mapped(x,src) for x in read_csv(name))
        cleaned,duplicates,years=process(rows,False)
    else:
        rows=read_csv(args.frozen)
        cleaned,duplicates,years=process(rows,True)
    dest=Path(args.out);dest.mkdir(parents=True,exist_ok=True)
    # Keep the frozen 3075 records unchanged even when a loose DOI/title audit flags review cases.
    saved_rows=cleaned if args.raw else rows
    columns=list(saved_rows[0])
    write(dest/'papers_preprocessed.csv',saved_rows,columns)
    write(dest/'potential_duplicates_for_review.csv',duplicates,['row','Paper_ID','DOI','Title','Reason'])
    report={'input_rows':len(rows),'output_rows':len(saved_rows),'potential_duplicates':len(duplicates),
            'year_counts':dict(sorted(years.items())),'mode':'raw dedup proposed' if args.raw else 'frozen non-destructive audit',
            'note':'Manual scope exclusions and historical fuzzy matching cannot be recovered from the 3075 freeze alone.'}
    (dest/'preprocessing_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'input':report['input_rows'],'output':report['output_rows'],
                      'potential_duplicates':report['potential_duplicates'],'mode':report['mode']},ensure_ascii=False))
if __name__=='__main__':main()
