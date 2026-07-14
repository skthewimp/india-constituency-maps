#!/usr/bin/env python3
"""Build the India constituency maps repo: pre-2008 and post-2008, assembly + Lok Sabha,
standardised to a common schema in WGS84, per-state + national, with AC-PC mappings.

Sources (all local):
  pre2008/assembly       <- AC_All_Final.shp  (pre-delim ACs, already WGS84, +AC-PC join)
  pre2008/parliamentary  <- PC_Data/States/*_PC.shp  (pre-delim PCs, WGS84)
  post2008/assembly      <- India_AC.shp dissolved by (state,AC_NO)  [27 states]
                            + per-state pipeline for Gujarat/MP/Sikkim  [gap fill]
  post2008/parliamentary <- india_pc_2019.shp  (current PCs, WGS84)

Note: Assam (2023) and J&K (2022) re-delimitations are NOT in the source data, so the
post-2008 layer carries the older boundaries for those (Assam 126, J&K 87). Documented.
"""
import os, glob, csv, collections, re, shapefile

W   = "/Users/Karthik/Documents/work/"
REF = W + "elections/geo/reference/"
OUT = W + "india-constituency-maps"

WGS84_PRJ = ('GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",'
             '6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],'
             'UNIT["Degree",0.0174532925199433]]')

AC_FIELDS = [("ST_CODE","C",3,0),("ST_NAME","C",40,0),("AC_NO","N",4,0),
             ("AC_NAME","C",60,0),("AC_TYPE","C",3,0),("PC_NO","N",4,0),("PC_NAME","C",60,0)]
PC_FIELDS = [("ST_CODE","C",3,0),("ST_NAME","C",40,0),("PC_NO","N",4,0),
             ("PC_NAME","C",60,0),("PC_TYPE","C",3,0)]

# ---- canonical names (modern) + pre-2008 overrides ----
NAME = {"S01":"Andhra Pradesh","S02":"Arunachal Pradesh","S03":"Assam","S04":"Bihar",
"S05":"Goa","S06":"Gujarat","S07":"Haryana","S08":"Himachal Pradesh","S09":"Jammu & Kashmir",
"S10":"Karnataka","S11":"Kerala","S12":"Madhya Pradesh","S13":"Maharashtra","S14":"Manipur",
"S15":"Meghalaya","S16":"Mizoram","S17":"Nagaland","S18":"Odisha","S19":"Punjab",
"S20":"Rajasthan","S21":"Sikkim","S22":"Tamil Nadu","S23":"Tripura","S24":"Uttar Pradesh",
"S25":"West Bengal","S26":"Chhattisgarh","S27":"Jharkhand","S28":"Uttarakhand","S29":"Telangana",
"U01":"Andaman & Nicobar Islands","U02":"Chandigarh","U03":"Dadra & Nagar Haveli",
"U04":"Daman & Diu","U05":"Delhi","U06":"Lakshadweep","U07":"Puducherry"}
NAME_PRE = dict(NAME, **{"S18":"Orissa","S28":"Uttaranchal","U07":"Pondicherry"})

def st_code(name):
    """Resolve any state-name spelling to an ECI state code."""
    n = re.sub(r"[^A-Z]", "", (name or "").upper())
    rules = [("ANDAMAN","U01"),("ANDHRA","S01"),("ARUNACHAL","S02"),("ASSAM","S03"),
        ("BIHAR","S04"),("CHANDIGARH","U02"),("CHHATTISGARH","S26"),("CHATTISGARH","S26"),
        ("DADRA","U03"),("NAGARHAVELI","U03"),("DAMAN","U04"),("DELHI","U05"),("GOA","S05"),
        ("GUJARAT","S06"),("HARYANA","S07"),("HIMACHAL","S08"),("JAMMU","S09"),("KASHMIR","S09"),
        ("JHARKHAND","S27"),("KARNATAKA","S10"),("KERALA","S11"),("LAKSHADWEEP","U06"),
        ("MADHYA","S12"),("MAHARASHTRA","S13"),("MANIPUR","S14"),("MEGHALAYA","S15"),
        ("MIZORAM","S16"),("NAGALAND","S17"),("ODISHA","S18"),("ORISSA","S18"),
        ("UTTARPRADESH","S24"),("PUNJAB","S19"),("RAJASTHAN","S20"),("SIKKIM","S21"),
        ("TAMIL","S22"),("TELANGANA","S29"),("TRIPURA","S23"),("UTTARANCHAL","S28"),
        ("UTTARAKHAND","S28"),("UTTARKHAND","S28"),("WESTBENGAL","S25"),("BENGAL","S25"),
        ("PONDICHERRY","U07"),("PUDUCHERRY","U07")]
    for key, code in rules:
        if key in n:
            return code
    raise ValueError("unmapped state name: %r" % name)

def titlecase(s):
    s = (s or "").strip()
    return s.title() if s.isupper() else s

def num(v):
    try: return int(round(float(v)))
    except (TypeError, ValueError): return None

def rings(shape):
    parts = list(shape.parts) + [len(shape.points)]
    return [shape.points[a:b] for a, b in zip(parts, parts[1:]) if b - a >= 3]

def write_layer(path, fields, feats):
    """feats: list of (record_list, list_of_rings). Also writes .prj."""
    w = shapefile.Writer(path, shapeType=shapefile.POLYGON)
    for f in fields: w.field(*f)
    for rec, rgs in feats:
        w.poly(rgs); w.record(*rec)
    w.close()
    open(path + ".prj", "w").write(WGS84_PRJ)

def split_and_write(dirpath, prefix_of, fields, feats):
    """Write national merge + per-state files. prefix_of(rec)->ST_CODE."""
    os.makedirs(dirpath, exist_ok=True)
    write_layer(os.path.join(dirpath, "india_" + os.path.basename(dirpath)), fields, feats)
    by = collections.defaultdict(list)
    for rec, rgs in feats:
        by[prefix_of(rec)].append((rec, rgs))
    counts = {}
    suffix = "AC" if fields is AC_FIELDS else "PC"
    for code, fs in by.items():
        write_layer(os.path.join(dirpath, f"{code}_{suffix}"), fields, fs)
        counts[code] = len(fs)
    return counts

# ---------- PRE-2008 ASSEMBLY (from AC_All_Final) ----------
def pre_assembly():
    r = shapefile.Reader(W+"elections/legacy/spatial/shapefiles/AC_All_Final.shp",
                         encoding="latin1", encodingErrors="replace")
    f = [x[0] for x in r.fields[1:]]
    idx = {k: f.index(k) for k in ["ST_CODE","AC_NO","AC_NAME","AC_TYPE","PC_NO_1","PC_NAME"]}
    feats = []
    for sr in r.iterShapeRecords():
        rec = sr.record; code = rec[idx["ST_CODE"]]
        row = [code, NAME_PRE.get(code, code), num(rec[idx["AC_NO"]]),
               titlecase(rec[idx["AC_NAME"]]),
               (rec[idx["AC_TYPE"]] or "").strip().upper(),
               num(rec[idx["PC_NO_1"]]), titlecase(rec[idx["PC_NAME"]])]
        feats.append((row, rings(sr.shape)))
    return split_and_write(os.path.join(OUT,"pre2008","assembly"),
                           lambda rec: rec[0], AC_FIELDS, feats)

# ---------- PRE-2008 PARLIAMENTARY (from PC_Data) ----------
def pre_parliamentary():
    feats = []
    for shp in sorted(glob.glob(REF+"PC_Data/States/*/*_PC.shp")):
        code = os.path.basename(shp)[:3]
        r = shapefile.Reader(shp, encoding="latin1", encodingErrors="replace")
        f = [x[0] for x in r.fields[1:]]
        gi = lambda k: f.index(k) if k in f else None
        for sr in r.iterShapeRecords():
            rec = sr.record
            pcno = num(rec[gi("PC_NO")]) if gi("PC_NO") is not None else None
            row = [code, NAME_PRE.get(code, code), pcno,
                   titlecase(rec[gi("PC_NAME")]),
                   (rec[gi("PC_TYPE")] or "").strip().upper()]
            feats.append((row, rings(sr.shape)))
    return split_and_write(os.path.join(OUT,"pre2008","parliamentary"),
                           lambda rec: rec[0], PC_FIELDS, feats)

# ---------- POST-2008 ASSEMBLY (India_AC dissolved + pipeline gap fill) ----------
GAP_STATES = {"S06":"gujarat","S12":"madhyapradesh","S21":"sikkim"}

def type_from_name(nm):
    m = re.search(r"\((SC|ST)\)", nm or "", re.I)
    return m.group(1).upper() if m else ""

def clean_name(nm):
    return titlecase(re.sub(r"\s*\((SC|ST)\)\s*$", "", nm or "", flags=re.I).strip())

def post_assembly():
    feats = []
    # India_AC dissolved, skipping gap states (filled from pipeline below)
    r = shapefile.Reader(W+"data_work/Census/maps/maps/India_AC.shp",
                         encoding="latin1", encodingErrors="replace")
    f = [x[0] for x in r.fields[1:]]
    I = {k: f.index(k) for k in ["ST_NAME","AC_NO","AC_NAME","PC_NO","PC_NAME"]}
    groups = collections.OrderedDict()
    for sr in r.iterShapeRecords():
        rec = sr.record
        code = st_code(rec[I["ST_NAME"]])
        if code in GAP_STATES: continue
        acno = num(rec[I["AC_NO"]])
        if not acno or acno <= 0: continue          # drop unnumbered slivers
        key = (code, acno)
        if key not in groups:
            groups[key] = [rec, []]
        groups[key][1].extend(rings(sr.shape))
    for (code, acno), (rec, rgs) in groups.items():
        nm = rec[I["AC_NAME"]]
        row = [code, NAME[code], acno, clean_name(nm),
               type_from_name(nm), num(rec[I["PC_NO"]]), clean_name(rec[I["PC_NAME"]])]
        feats.append((row, rgs))
    # gap states from pipeline
    for code, folder in GAP_STATES.items():
        r = shapefile.Reader(W+f"elections/geo/maps/{folder}/{folder}.assembly.shp")
        f = [x[0] for x in r.fields[1:]]
        P = {k: f.index(k) for k in ["pc","pc_name","ac","ac_name"]}
        for sr in r.iterShapeRecords():
            rec = sr.record; nm = rec[P["ac_name"]]
            row = [code, NAME[code], num(rec[P["ac"]]), clean_name(nm),
                   type_from_name(nm), num(rec[P["pc"]]), titlecase(rec[P["pc_name"]])]
            feats.append((row, rings(sr.shape)))
    return split_and_write(os.path.join(OUT,"post2008","assembly"),
                           lambda rec: rec[0], AC_FIELDS, feats)

# ---------- POST-2008 PARLIAMENTARY (india_pc_2019) ----------
def post_parliamentary():
    r = shapefile.Reader(W+"data_work/Census/maps/maps/2019/india_pc_2019.shp",
                         encoding="latin1", encodingErrors="replace")
    f = [x[0] for x in r.fields[1:]]
    I = {k: f.index(k) for k in ["ST_NAME","PC_NAME","PC_CODE","Res"]}
    feats = []
    for sr in r.iterShapeRecords():
        rec = sr.record; code = st_code(rec[I["ST_NAME"]])
        row = [code, NAME[code], num(rec[I["PC_CODE"]]),
               clean_name(rec[I["PC_NAME"]]), (rec[I["Res"]] or "").strip().upper()]
        feats.append((row, rings(sr.shape)))
    return split_and_write(os.path.join(OUT,"post2008","parliamentary"),
                           lambda rec: rec[0], PC_FIELDS, feats)

# ---------- AC-PC mapping CSVs ----------
def mapping_csv(layer_dir, path):
    r = shapefile.Reader(os.path.join(layer_dir, "india_assembly.shp"))
    f = [x[0] for x in r.fields[1:]]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(["st_code","st_name","ac_no","ac_name","ac_type","pc_no","pc_name"])
        for rec in sorted(r.records(), key=lambda x:(x[0], x[2] or 0)):
            wr.writerow([rec[0],rec[1],rec[2],rec[3],rec[4],rec[5],rec[6]])

if __name__ == "__main__":
    m = {}
    m["pre2008/assembly"]      = pre_assembly()
    m["pre2008/parliamentary"] = pre_parliamentary()
    m["post2008/assembly"]     = post_assembly()
    m["post2008/parliamentary"]= post_parliamentary()
    mapping_csv(os.path.join(OUT,"pre2008","assembly"),  os.path.join(OUT,"mappings","ac_pc_pre2008.csv"))
    mapping_csv(os.path.join(OUT,"post2008","assembly"), os.path.join(OUT,"mappings","ac_pc_post2008.csv"))
    # manifest
    with open(os.path.join(OUT,"manifest.csv"),"w",newline="") as fh:
        wr=csv.writer(fh); wr.writerow(["layer","st_code","st_name","n_features"])
        for layer,counts in m.items():
            for code in sorted(counts):
                wr.writerow([layer,code,NAME.get(code,code),counts[code]])
    for layer,counts in m.items():
        print(f"{layer:24} {len(counts):2} states  {sum(counts.values()):5} features")
