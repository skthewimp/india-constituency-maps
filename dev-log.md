# Dev log

Build log for the India constituency map standardisation (pre- and post-2008). Prompts
(paraphrased, PII stripped) plus the technical decisions and problems hit along the way.

## Prompts

1. "Found boundaries.in with pre-2008 assembly maps. I think I have pre-2008 shapefiles on
   my computer too - search for them and tabulate what we have."
2. "Standardise the nomenclature of the whole thing. Include Lok Sabha (pre-2008 also).
   Make formats consistent and keep it in a folder. Then put it on GitHub."
3. "Make it more comprehensive - I have the post-2008 shapefiles too, put them in the same
   repo in the same format. Assam was reorganised 2-3 years ago, handle that carefully. And
   include the AC-PC mapping from that time if we have it."

Decisions taken during the build (via clarifying questions):
- Pre-2008 AC georeferencing: affine-fit to WGS84 (later superseded, see below).
- Output: per-state standardised files + national merge.
- Post-2008 AC: reconcile multiple sources against official counts.
- Assam/J&K: ship the boundaries we have, clearly labelled.
- Pre-2008 AC: upgrade geometry to the properly-georeferenced source + add AC-PC mapping.

## Pre-2008 layer

- Assembly source was in an unknown projection with no `.prj`; each state in its own local
  grid, S28 (Uttaranchal) misregistered. First fix was a per-state affine mapping each
  state's bbox onto its parliamentary (WGS84) bbox. Worked, but approximate.
- **Superseded:** `AC_All_Final.shp` turned out to be the *same* pre-2008 assembly data,
  already properly georeferenced to WGS84, confirmed by matching the `INDIAASSEM` id field
  (224/224 for Karnataka). Switched to it - better geometry, and it carries the parent-PC
  join, so the affine hack was dropped. Per-state counts match official pre-2008 totals.
- Parliamentary: state-wise pre-delimitation PC files, already WGS84, 543 total.

## Post-2008 layer

- No single clean national assembly file. `India_AC.shp` (2018) had 4,182 records vs the
  ~4,120 expected.
- The inflation was multipart constituencies stored as multiple polygon rows. Dissolving by
  `(ST_NAME, AC_NO)` and dropping `AC_NO<=0` slivers brought **27 of 30 states to exact
  agreement** with official ECI counts.
- `STATUS='Pre delimitation'` in that file flags the states excluded from the 2008
  delimitation (Assam, J&K, Nagaland, Manipur, Arunachal, Jharkhand) - those are valid
  post-2008 boundaries and were kept, not dropped.
- The three states still short after dissolve (Gujarat 162, MP 226, Sikkim 31) were filled
  from the per-state pipeline set (MP 230 ✓, Sikkim 32 ✓, Gujarat 181 - still 1 short of
  the official 182, a source gap).
- Parliamentary: `india_pc_2019.shp`, current Lok Sabha boundaries, 543.

## Assam / J&K vintage

- Assam and J&K were outside the 2008 delimitation, then re-delimited in 2023 and 2022
  respectively. Those new shapefiles are not on disk (searched). So the post-2008 layer
  carries Assam 126 (pre-2023) and J&K 87 (pre-2022). Documented in the README as a known
  limitation rather than silently shipped as current.

## AC-PC mapping

- Available for both eras and emitted as `mappings/ac_pc_{pre,post}2008.csv` (and kept as
  `PC_NO`/`PC_NAME` columns in the assembly attributes). Pre-2008 mapping from
  `AC_All_Final`'s `PC_NO_1`/`PC_NAME`; post-2008 from `India_AC`'s `PC_NO`/`PC_NAME`.

## Known limitations (also in README)

- Post-2008 `AC_TYPE` (GEN/SC/ST) is mostly blank - the 2018 source has no reservation
  field and no `(SC)/(ST)` name suffixes; only the three pipeline states get it. Pre-2008
  `AC_TYPE` is complete.
- Post-2008 J&K assembly is missing the far-north Ladakh geometry (source clips ~35.3°N).
- Island UTs appear in parliamentary layers only.

## Naming

- Era-accurate state names: pre-2008 uses Orissa / Uttaranchal / Pondicherry; post-2008
  uses Odisha / Uttarakhand / Puducherry (renamed 2006-2011). A single `st_code()` resolver
  maps every source spelling (and the numeric/2-digit codes in the newer files) to ECI
  codes.

## Tooling notes

- `ogrinfo` on this machine is broken (missing `libre2` via the Arrow build), so GDAL was
  out. Everything uses **pyshp** (pure Python) - reading, dissolving, writing. Dissolve is
  done by concatenating polygon parts, not a true geometric union, which is fine for a
  reference/visualisation dataset. Install is `pip install pyshp`, no C toolchain.
- `.dbf` files aren't UTF-8; read with `latin1`. Legacy Hindi-name columns are in a
  non-Unicode font encoding and were dropped.
- QA: rendered both eras (assembly fill under Lok Sabha outline) with matplotlib and
  eyeballed alignment. Saved as `docs/preview.png`.

## Output

- `pre2008/` and `post2008/`, each with `assembly/` and `parliamentary/` (per-state +
  national merge), all WGS84 with `.prj`.
- `mappings/` - AC-PC lookup CSVs for both eras.
- `manifest.csv` - per-state feature counts across all layers.
- `scripts/build.py` - the full reproducible build.
