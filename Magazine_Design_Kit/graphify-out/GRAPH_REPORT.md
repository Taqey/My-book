# Graph Report - Magazine_Design_Kit  (2026-11-21)

## Corpus Check
- Large corpus: 109 files · ~1,532,707 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder.

## Summary
- 180 nodes · 253 edges · 28 communities (6 shown, 22 thin omitted)
- Extraction: 64% EXTRACTED · 36% INFERRED · 0% AMBIGUOUS · INFERRED: 92 edges (avg confidence: 0.82)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Book Builder Server Backups
- Curriculum and Assessment Questions
- Magazine Design and Mascot Visuals
- Server HTTP Handlers and Operations
- Server Content Block Renderers
- Book HTML Parser and Extractors
- InDesign Template Generator
- HTML Stream Parser Mapper

## God Nodes (most connected - your core abstractions)
1. `AI & Data Science Curriculum (Units 5, 6, 7)` - 35 edges
2. `Codey the Programmer Mascot` - 28 edges
3. `esc()` - 12 edges
4. `extract_block()` - 11 edges
5. `parse_book()` - 10 edges
6. `rich()` - 10 edges
7. `do_insert()` - 8 edges
8. `do_update()` - 8 edges
9. `Mapper` - 7 edges
10. `structure()` - 7 edges

## Surprising Connections (you probably didn't know these)
- `parse_book()` --calls--> `Mapper`  [EXTRACTED]
  book_builder/server.py → book_builder/server.py  _Bridges community 7 → community 5_
- `do_delete()` --calls--> `parse_book()`  [EXTRACTED]
  book_builder/server.py → book_builder/server.py  _Bridges community 5 → community 3_
- `esc()` --calls--> `html`  [EXTRACTED]
  book_builder/server.py →   _Bridges community 4 → community 5_
- `do_delete()` --calls--> `backup()`  [EXTRACTED]
  book_builder/server.py → book_builder/server.py  _Bridges community 0 → community 3_

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Educational Magazine Production Pipeline** — from_zero_to_hero_book_file, book_builder_server, book_builder_index_file, build_indesign_template, concept_educational_tech_magazine_style [EXTRACTED 1.00]

## Communities (28 total, 22 thin omitted)

### Community 0 - "Book Builder Server Backups"
Cohesion: 0.06
Nodes (3): backup(), do_undo(), Book Builder Dynamic Pagination Engine

### Community 2 - "Magazine Design and Mascot Visuals"
Cohesion: 0.06
Nodes (3): Codey the Programmer Mascot, Educational Tech Magazine Design System, Three-Tier Question Pedagogy

### Community 3 - "Server HTTP Handlers and Operations"
Cohesion: 0.28
Nodes (9): do_delete(), do_insert(), do_update(), H, lesson_blocks(), preview_doc(), read_book(), render() (+1 more)

### Community 4 - "Server Content Block Renderers"
Cohesion: 0.22
Nodes (14): c_concept(), c_example(), c_flow(), c_heading(), c_notes(), c_paragraph(), c_problems(), c_rules() (+6 more)

### Community 5 - "Book HTML Parser and Extractors"
Cohesion: 0.29
Nodes (11): all_class(), block_type(), extract_block(), first_class(), parse_book(), walk(), strip_tags(), structure() (+3 more)

### Community 6 - "InDesign Template Generator"
Cohesion: 0.29
Nodes (3): createMagazineTemplate(), Adobe InDesign Automation Pipeline, Magazine Color Palette (Blue/Purple/Neon Pink)

## Knowledge Gaps
- **3 isolated node(s):** `Three-Tier Question Pedagogy`, `Book Builder Dynamic Pagination Engine`, `Adobe InDesign Automation Pipeline`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 122 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **22 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AI & Data Science Curriculum (Units 5, 6, 7)` connect `Curriculum and Assessment Questions` to `Magazine Design and Mascot Visuals`?**
  _High betweenness centrality (0.302) - this node is a cross-community bridge._
- **Are the 34 inferred relationships involving `AI & Data Science Curriculum (Units 5, 6, 7)` (e.g. with `all_lesson_covers.html` and `banner_5_1.jpg`) actually correct?**
  _`AI & Data Science Curriculum (Units 5, 6, 7)` has 34 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Three-Tier Question Pedagogy`, `Book Builder Dynamic Pagination Engine`, `Adobe InDesign Automation Pipeline` to the rest of the system?**
  _3 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Book Builder Server Backups` be split into smaller, more focused modules?**
  _Cohesion score 0.06156156156156156 - nodes in this community are weakly interconnected._
- **Why does `Magazine Color Palette (Blue/Purple/Neon Pink)` connect `InDesign Template Generator` to `Magazine Design and Mascot Visuals`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._
- **Are the 26 inferred relationships involving `Codey the Programmer Mascot` (e.g. with `clipboard_3d.png` and `customer_survey_f9ur.svg`) actually correct?**
  _`Codey the Programmer Mascot` has 26 INFERRED edges - model-reasoned connections that need verification._
- **Should `Curriculum and Assessment Questions` be split into smaller, more focused modules?**
  _Cohesion score 0.05714285714285714 - nodes in this community are weakly interconnected._