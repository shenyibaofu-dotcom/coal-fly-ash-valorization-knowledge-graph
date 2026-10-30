# -*- coding: utf-8 -*-
"""候选三元组的原规则复算：源自Untitled.ipynb cell44，不包含后续V2/V3人工修正。
命令: python 01_reextract_candidates_3075.py --corpus inputs/01_2000-2025_文献基础库_3075篇.csv
"""
from pathlib import Path
from collections import Counter,defaultdict
import argparse,csv,re
import pandas as pd

ap=argparse.ArgumentParser()
ap.add_argument('--corpus',default=str(Path(__file__).resolve().parent/'inputs'/'01_2000-2025_文献基础库_3075篇.csv'))
ap.add_argument('--out',default=str(Path(__file__).resolve().parent/'outputs'/'03_初始候选三元组.csv'))
args=ap.parse_args()
df=pd.read_csv(args.corpus,encoding='utf-8-sig',dtype=str,keep_default_na=False).fillna('')
df.columns=df.columns.str.strip()
assert 'Paper_ID' in df.columns, 'Paper_ID must come from the frozen 3075 corpus'
assert len(df)==3075, f'Expected 3075 records, got {len(df)}; check the frozen 2000-2025 input'
# 3. 自动匹配字段
# =========================================================

def find_col(possible_names):
    for name in possible_names:
        if name in df.columns:
            return name
    return None

col_title = find_col(["Title", "Article Title", "题名", "标题"])
col_abstract = find_col(["Abstract", "Abstract Note", "摘要"])
col_year = find_col(["Year_clean", "Year", "Publication Year", "年份"])
col_primary = find_col(["Primary Category", "Primary_Category", "Revised Category", "技术大类", "Category"])
col_subroute = find_col(["Sub-route Label", "Subroute", "Sub_route", "Subroute_Label", "具体技术路径", "Sub-route"])

keyword_cols = []
for c in ["Keywords", "Author Keywords", "Keywords Plus", "Index Keywords"]:
    if c in df.columns:
        keyword_cols.append(c)

print("标题字段：", col_title)
print("摘要字段：", col_abstract)
print("年份字段：", col_year)
print("技术大类字段：", col_primary)
print("具体路径字段：", col_subroute)
print("关键词字段：", keyword_cols)

if col_title is None:
    raise ValueError("没有找到标题字段，请检查 Title / Article Title。")

# =========================================================
# 4. 文本清洗函数
# =========================================================

def norm_text(x):
    x = str(x).lower()
    x = x.replace("–", "-").replace("—", "-")
    x = x.replace("_", " ")
    x = x.replace("co₂", "co2")
    x = x.replace("co 2", "co2")
    x = x.replace("al₂o₃", "al2o3")
    x = x.replace("sio₂", "sio2")
    x = x.replace("fe₂o₃", "fe2o3")
    x = x.replace("cao", "cao")
    x = re.sub(r"\s+", " ", x)
    return x

def contains_any(text, patterns):
    hit = []
    for p in patterns:
        p2 = norm_text(p)
        if p2 and p2 in text:
            hit.append(p)
    return hit

# =========================================================
# 5. 实体词表
# =========================================================
# 格式：
# 标准实体名: {
#     "type": 节点类型,
#     "category": 所属类别,
#     "patterns": 匹配词
# }

tech_dict = {
    "吸附材料": {
        "type": "技术路径",
        "category": "环境功能材料",
        "patterns": ["adsorption", "adsorbent", "adsorbents", "sorption", "biosorption", "activated carbon"]
    },
    "沸石/分子筛": {
        "type": "技术路径",
        "category": "高附加值材料",
        "patterns": ["zeolite", "zeolites", "molecular sieve", "molecular sieves"]
    },
    "废水处理材料": {
        "type": "技术路径",
        "category": "环境功能材料",
        "patterns": ["wastewater treatment", "water treatment", "sewage treatment"]
    },
    "水泥/混凝土/砂浆": {
        "type": "技术路径",
        "category": "建材利用",
        "patterns": ["cement", "cements", "concrete", "mortar", "cement mortar", "portland cement", "opc"]
    },
    "地聚物材料": {
        "type": "技术路径",
        "category": "地聚物与碱激发材料",
        "patterns": ["geopolymer", "geopolymers", "geopolymerization", "geopolymerisation"]
    },
    "碱激发材料": {
        "type": "技术路径",
        "category": "地聚物与碱激发材料",
        "patterns": ["alkali activation", "alkali-activated", "alkali activated", "sodium hydroxide", "naoh"]
    },
    "陶瓷/玻璃陶瓷": {
        "type": "技术路径",
        "category": "高附加值材料",
        "patterns": ["ceramic", "ceramics", "glass-ceramic", "glass ceramic", "glass-ceramics", "glass ceramics", "mullite"]
    },
    "稀土/关键元素回收": {
        "type": "技术路径",
        "category": "元素提取",
        "patterns": ["rare earth", "rare earth elements", "ree", "rees", "critical elements", "critical element"]
    },
    "铝/氧化铝提取": {
        "type": "技术路径",
        "category": "元素提取",
        "patterns": ["alumina", "aluminum oxide", "aluminium oxide", "aluminum extraction", "aluminium extraction"]
    },
    "金属回收": {
        "type": "技术路径",
        "category": "元素提取",
        "patterns": ["metal recovery", "metals recovery", "recovery of metals", "extract metals"]
    },
    "碳材料": {
        "type": "技术路径",
        "category": "能源与碳相关利用",
        "patterns": ["carbon materials", "activated carbon", "porous carbon", "carbon nanotube", "carbon fiber"]
    },
    "碳捕集/矿化封存": {
        "type": "技术路径",
        "category": "能源与碳相关利用",
        "patterns": ["co2 capture", "carbon capture", "carbon dioxide capture", "mineral carbonation", "carbonation"]
    },
    "土壤改良/稳定化": {
        "type": "技术路径",
        "category": "生态与回填利用",
        "patterns": ["soil amendment", "soil stabilization", "soil stabilisation", "soil remediation", "soil improvement"]
    },
    "骨料/路基/道路材料": {
        "type": "技术路径",
        "category": "建材利用",
        "patterns": ["aggregate", "aggregates", "road material", "road base", "roadbed", "pavement"]
    },
    "砖/烧结制品": {
        "type": "技术路径",
        "category": "建材利用",
        "patterns": ["brick", "bricks", "sintered products", "sintering"]
    },
    "催化/光催化材料": {
        "type": "技术路径",
        "category": "高附加值材料",
        "patterns": ["catalyst", "catalysts", "photocatalyst", "photocatalysis", "photocatalytic"]
    },
    "功能填料/复合材料": {
        "type": "技术路径",
        "category": "高附加值材料",
        "patterns": ["filler", "fillers", "composite", "composites", "polymer composite"]
    },
    "空心微珠": {
        "type": "技术路径",
        "category": "高附加值材料",
        "patterns": ["cenosphere", "cenospheres", "hollow microsphere", "hollow microspheres"]
    },
    "未燃碳回收/浮选": {
        "type": "技术路径",
        "category": "能源与碳相关利用",
        "patterns": ["unburned carbon", "unburnt carbon", "carbon recovery", "flotation"]
    },
    "多固废协同": {
        "type": "技术路径",
        "category": "协同资源化利用",
        "patterns": ["co-utilization", "co utilization", "co-processing", "multi-solid waste", "multi waste", "solid waste synergy"]
    }
}

application_dict = {
    "废水处理": {
        "type": "应用场景",
        "category": "环境应用",
        "patterns": ["wastewater treatment", "water treatment", "sewage treatment", "aqueous solution"]
    },
    "重金属去除": {
        "type": "应用场景",
        "category": "污染物去除",
        "patterns": ["heavy metals", "heavy metal", "pb(ii)", "cd(ii)", "cr(vi)", "cu(ii)", "lead", "cadmium", "chromium", "copper"]
    },
    "染料吸附": {
        "type": "应用场景",
        "category": "污染物去除",
        "patterns": ["dye", "dyes", "methylene blue", "rhodamine", "malachite green"]
    },
    "建筑材料": {
        "type": "应用场景",
        "category": "工程应用",
        "patterns": ["construction material", "building material", "cement", "concrete", "mortar"]
    },
    "道路工程": {
        "type": "应用场景",
        "category": "工程应用",
        "patterns": ["road", "roadbed", "pavement", "road base", "highway"]
    },
    "生态修复": {
        "type": "应用场景",
        "category": "生态应用",
        "patterns": ["ecological restoration", "remediation", "soil remediation", "land reclamation"]
    },
    "CO2减排": {
        "type": "应用场景",
        "category": "碳减排",
        "patterns": ["co2 reduction", "carbon reduction", "carbon emission", "carbon dioxide", "carbon capture"]
    },
    "资源回收": {
        "type": "应用场景",
        "category": "资源回收",
        "patterns": ["resource recovery", "metal recovery", "element recovery", "rare earth recovery"]
    }
}

indicator_dict = {
    "吸附容量": {
        "type": "评价指标",
        "category": "环境性能",
        "patterns": ["adsorption capacity", "sorption capacity", "qmax", "maximum adsorption"]
    },
    "去除率": {
        "type": "评价指标",
        "category": "环境性能",
        "patterns": ["removal efficiency", "removal rate", "removal percentage"]
    },
    "抗压强度": {
        "type": "评价指标",
        "category": "工程性能",
        "patterns": ["compressive strength", "strength", "mechanical strength"]
    },
    "浸出毒性": {
        "type": "评价指标",
        "category": "环境风险",
        "patterns": ["leaching toxicity", "leachability", "leaching concentration", "toxicity characteristic"]
    },
    "回收率": {
        "type": "评价指标",
        "category": "资源回收性能",
        "patterns": ["recovery rate", "extraction efficiency", "leaching efficiency", "recovery efficiency"]
    },
    "碳排放": {
        "type": "评价指标",
        "category": "环境绩效",
        "patterns": ["carbon emission", "co2 emission", "greenhouse gas", "gwp", "global warming potential"]
    },
    "能耗": {
        "type": "评价指标",
        "category": "资源消耗",
        "patterns": ["energy consumption", "energy demand", "energy use"]
    },
    "物耗": {
        "type": "评价指标",
        "category": "资源消耗",
        "patterns": ["material consumption", "material demand", "material flow"]
    },
    "经济性": {
        "type": "评价指标",
        "category": "经济评价",
        "patterns": ["cost", "economic", "techno-economic", "benefit", "feasibility"]
    },
    "稳定性": {
        "type": "评价指标",
        "category": "工程稳定性",
        "patterns": ["stability", "durability", "immobilization", "stabilization"]
    }
}

property_dict = {
    "SiO2/Al2O3": {
        "type": "原料特性",
        "category": "化学组成",
        "patterns": ["sio2", "silica", "al2o3", "alumina", "aluminosilicate", "si/al"]
    },
    "CaO": {
        "type": "原料特性",
        "category": "化学组成",
        "patterns": ["cao", "calcium oxide", "free lime", "lime"]
    },
    "Fe2O3": {
        "type": "原料特性",
        "category": "化学组成",
        "patterns": ["fe2o3", "iron oxide", "ferric oxide"]
    },
    "未燃碳": {
        "type": "原料特性",
        "category": "碳组分",
        "patterns": ["unburned carbon", "unburnt carbon", "loss on ignition", "loi"]
    },
    "空心微珠": {
        "type": "原料特性",
        "category": "形貌组分",
        "patterns": ["cenosphere", "cenospheres", "hollow microsphere", "hollow sphere"]
    },
    "重金属浸出风险": {
        "type": "原料特性",
        "category": "环境风险",
        "patterns": ["heavy metal", "heavy metals", "leaching toxicity", "leachability", "toxic elements"]
    },
    "粒径/细度": {
        "type": "原料特性",
        "category": "物理性质",
        "patterns": ["particle size", "fineness", "specific surface area"]
    },
    "矿物相": {
        "type": "原料特性",
        "category": "矿物组成",
        "patterns": ["mullite", "quartz", "hematite", "crystalline phase", "mineral phase"]
    },
    "碱度": {
        "type": "原料特性",
        "category": "化学性质",
        "patterns": ["alkalinity", "alkaline", "ph"]
    }
}

cowaste_dict = {
    "矿渣": {
        "type": "协同固废",
        "category": "工业固废",
        "patterns": ["slag", "blast furnace slag", "steel slag"]
    },
    "钢渣": {
        "type": "协同固废",
        "category": "工业固废",
        "patterns": ["steel slag"]
    },
    "赤泥": {
        "type": "协同固废",
        "category": "工业固废",
        "patterns": ["red mud", "bauxite residue"]
    },
    "脱硫石膏": {
        "type": "协同固废",
        "category": "工业固废",
        "patterns": ["desulfurization gypsum", "desulphurization gypsum", "fgd gypsum", "gypsum"]
    },
    "污泥": {
        "type": "协同固废",
        "category": "污泥",
        "patterns": ["sludge", "sewage sludge"]
    },
    "水泥窑灰": {
        "type": "协同固废",
        "category": "工业固废",
        "patterns": ["cement kiln dust", "ckd"]
    },
    "尾矿": {
        "type": "协同固废",
        "category": "矿业固废",
        "patterns": ["tailings", "mine tailings"]
    },
    "生物质灰": {
        "type": "协同固废",
        "category": "灰渣类固废",
        "patterns": ["biomass ash", "rice husk ash"]
    }
}

# =========================================================
# 6. 工具函数：匹配实体
# =========================================================

def match_entities(text, entity_dict):
    results = {}
    for std_name, info in entity_dict.items():
        hits = contains_any(text, info["patterns"])
        if hits:
            results[std_name] = {
                "type": info["type"],
                "category": info["category"],
                "hits": hits
            }
    return results

def safe_get(row, col):
    if col is None:
        return ""
    return str(row.get(col, ""))

# =========================================================
# 7. 生成三元体
# =========================================================

triples = []
seen = set()

def add_triple(
    paper_id, year, title, primary, subroute,
    source, relation, target,
    source_type, target_type,
    evidence, confidence="Medium", need_check="No"
):
    key = (paper_id, source, relation, target)
    if key in seen:
        return
    seen.add(key)
    
    triples.append({
        "Paper_ID": paper_id,
        "Year": year,
        "Title": title,
        "Primary_Category": primary,
        "Subroute": subroute,
        "Source": source,
        "Relation": relation,
        "Target": target,
        "Source_Type": source_type,
        "Target_Type": target_type,
        "Evidence_Text": evidence,
        "Confidence": confidence,
        "Need_Check": need_check
    })

for idx, row in df.iterrows():
    paper_id = str(row.get("Paper_ID", "")).strip()
    if paper_id == "":
        paper_id = f"P{idx+1:05d}"
    
    year = safe_get(row, col_year)
    title = safe_get(row, col_title)
    abstract = safe_get(row, col_abstract)
    primary = safe_get(row, col_primary)
    subroute = safe_get(row, col_subroute)
    
    kw_text = " ".join([safe_get(row, c) for c in keyword_cols])
    text_all_raw = " ".join([title, abstract, kw_text, primary, subroute])
    text_all = norm_text(text_all_raw)
    
    techs = match_entities(text_all, tech_dict)
    apps = match_entities(text_all, application_dict)
    indicators = match_entities(text_all, indicator_dict)
    props = match_entities(text_all, property_dict)
    cowastes = match_entities(text_all, cowaste_dict)
    
    # -----------------------------------------------------
    # 规则 1：粉煤灰 — 制备 — 技术路径
    # -----------------------------------------------------
    for tech, info in techs.items():
        add_triple(
            paper_id, year, title, primary, subroute,
            source="粉煤灰",
            relation="制备",
            target=tech,
            source_type="原料",
            target_type="技术路径",
            evidence="; ".join(info["hits"][:6]),
            confidence="High",
            need_check="No"
        )
    
    # -----------------------------------------------------
    # 规则 2：技术路径 — 用于 — 应用场景
    # -----------------------------------------------------
    for tech, tinfo in techs.items():
        for app, ainfo in apps.items():
            add_triple(
                paper_id, year, title, primary, subroute,
                source=tech,
                relation="用于",
                target=app,
                source_type="技术路径",
                target_type="应用场景",
                evidence="Tech: " + "; ".join(tinfo["hits"][:3]) + " | App: " + "; ".join(ainfo["hits"][:3]),
                confidence="Medium",
                need_check="No"
            )
    
    # -----------------------------------------------------
    # 规则 3：技术路径 — 评价 — 指标
    # -----------------------------------------------------
    for tech, tinfo in techs.items():
        for ind, iinfo in indicators.items():
            add_triple(
                paper_id, year, title, primary, subroute,
                source=tech,
                relation="评价",
                target=ind,
                source_type="技术路径",
                target_type="评价指标",
                evidence="Tech: " + "; ".join(tinfo["hits"][:3]) + " | Indicator: " + "; ".join(iinfo["hits"][:3]),
                confidence="Medium",
                need_check="No"
            )
    
    # -----------------------------------------------------
    # 规则 4：技术路径 — 去除 — 污染物/对象
    # -----------------------------------------------------
    pollutant_targets = {
        "重金属": ["heavy metal", "heavy metals", "pb(ii)", "cd(ii)", "cr(vi)", "lead", "cadmium", "chromium"],
        "染料": ["dye", "dyes", "methylene blue", "rhodamine", "malachite green"]
    }
    
    for target_name, pats in pollutant_targets.items():
        hits = contains_any(text_all, pats)
        if hits:
            for tech, tinfo in techs.items():
                if tech in ["吸附材料", "废水处理材料", "沸石/分子筛", "碳材料", "催化/光催化材料"]:
                    add_triple(
                        paper_id, year, title, primary, subroute,
                        source=tech,
                        relation="去除",
                        target=target_name,
                        source_type="技术路径",
                        target_type="污染物/对象",
                        evidence="Tech: " + "; ".join(tinfo["hits"][:3]) + " | Target: " + "; ".join(hits[:3]),
                        confidence="High",
                        need_check="No"
                    )
    
    # -----------------------------------------------------
    # 规则 5：粉煤灰 — 回收/提取 — 元素
    # -----------------------------------------------------
    element_targets = {
        "稀土元素": ["rare earth", "rare earth elements", "ree", "rees"],
        "关键元素": ["critical elements", "critical element"],
        "铝/氧化铝": ["alumina", "aluminum oxide", "aluminium oxide", "aluminum", "aluminium"],
        "镓": ["gallium", "ga"],
        "锂": ["lithium", "li"]
    }
    
    extraction_signal = contains_any(
        text_all,
        ["extraction", "extract", "recovery", "recover", "leaching", "acid leaching", "alkali leaching"]
    )
    
    for elem, pats in element_targets.items():
        hits = contains_any(text_all, pats)
        if hits and extraction_signal:
            add_triple(
                paper_id, year, title, primary, subroute,
                source="粉煤灰",
                relation="回收",
                target=elem,
                source_type="原料",
                target_type="目标元素",
                evidence="Element: " + "; ".join(hits[:3]) + " | Signal: " + "; ".join(extraction_signal[:3]),
                confidence="High",
                need_check="No"
            )
    
    # -----------------------------------------------------
    # 规则 6：原料特性 — 关联 — 技术路径
    # 这类关系不强行判断促进/限制，先标为“关联”，后续可人工改。
    # -----------------------------------------------------
    for prop, pinfo in props.items():
        for tech, tinfo in techs.items():
            add_triple(
                paper_id, year, title, primary, subroute,
                source=prop,
                relation="关联",
                target=tech,
                source_type="原料特性",
                target_type="技术路径",
                evidence="Property: " + "; ".join(pinfo["hits"][:3]) + " | Tech: " + "; ".join(tinfo["hits"][:3]),
                confidence="Low",
                need_check="Yes"
            )
    
    # -----------------------------------------------------
    # 规则 7：粉煤灰 — 协同 — 其他固废
    # -----------------------------------------------------
    for cw, cinfo in cowastes.items():
        add_triple(
            paper_id, year, title, primary, subroute,
            source="粉煤灰",
            relation="协同",
            target=cw,
            source_type="原料",
            target_type="协同固废",
            evidence="; ".join(cinfo["hits"][:6]),
            confidence="Medium",
            need_check="No"
        )
    
    # -----------------------------------------------------
    # 规则 8：技术大类 — 包含 — 具体技术路径
    # 来自你的分类结果，置信度最高
    # -----------------------------------------------------
    if primary and primary.lower() not in ["unclear", "nan", ""]:
        if subroute and subroute.lower() not in ["unclear", "nan", ""]:
            add_triple(
                paper_id, year, title, primary, subroute,
                source=primary,
                relation="包含",
                target=subroute,
                source_type="技术大类",
                target_type="具体技术路径",
                evidence="分类字段",
                confidence="High",
                need_check="No"
            )

# =========================================================

assert len(triples)>0, 'No relation extracted'
out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
with out.open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=list(triples[0]));writer.writeheader();writer.writerows(triples)
print(f'Original dictionary candidate extraction: {len(df):,} papers, {len(triples):,} candidate supports saved to {out}')
print('This is NOT the author-corrected final 19,177 triple snapshot. V2/V3 decisions must be applied or use the frozen final table.')
