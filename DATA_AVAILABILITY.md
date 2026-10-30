# Data availability and reproducibility boundaries

## Code

The seven Python scripts and the code-to-data correspondence index are included in this repository. The `requirements.txt` file lists the external Python dependencies.

## Archival data status

The complete 3,075-paper frozen corpus, full V2/V3 review history, 19,177 paper-linked relation instances, and original dictionary JSON sources are **not** present in this repository.

Available derived tables under `inputs/` are: `KG_2000-2025_Aggregated_Edges_198.csv` (198 aggregate relation edges), `Fig4d_2000to2025_Evidence_Filtered_Edges.csv` (182 external association edge candidates), and `Fig3_3075_aggregates_and_proxy_inputs.csv` (20 pathway-level summary rows). These files exclude individual bibliographic abstract records. In particular, bibliographic records may contain database-exported titles, abstracts, keywords, DOIs, and other licensed metadata and therefore should not be indiscriminately redistributed.

The authors' separate archival files include numerical, non-bibliographic derived tables that can be considered for sharing after checking their content. Publication of only aggregated edges or pathway summaries cannot reproduce the full manual screening or entity-extraction history.

## Verification methods

- A final corpus of 3,075 papers was used in the reported analysis.
- There are 19,177 paper-linked relation supports and 198 distinct directed core-graph relation edges.
- A *separate* filtered external-association network produces 39 nodes, 104 edges, and five Louvain communities with seed 42 (Q ≈ 0.4684).
- Code checks of counts, network modularity and matching archived edges are computational consistency tests. They are **not** independent full-text semantic validation, extraction precision, or causal proof.
- The primary value of publishing source scripts is inspection of the implemented methodology. Independent full reproduction requires the relevant permitted input files.

## Public-sharing policy

For eventual publication, only non-sensitive derived numerical tables should be placed in this repository without further source-rights clearance; bibliographic abstracts, paper-linked raw review evidence and private review notes must not be uploaded by default.

Any future GitHub release must be publicly accessible to reviewers before the link is cited in the manuscript. A versioned release tag does not itself provide a DOI; consider archiving the release in Zenodo for a DOI if needed.
