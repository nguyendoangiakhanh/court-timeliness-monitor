import random, csv, datetime as dt
random.seed(20260909)

REGIONS = ["Northern","Central","Eastern","Southern"]
COURTS = [
    ("01","Northbridge District Court","Northern","District"),
    ("02","Kauri Point District Court","Northern","District"),
    ("03","Harbourview High Court","Northern","High"),
    ("04","Riverton District Court","Central","District"),
    ("05","Mistvale District Court","Central","District"),
    ("06","Central Plains High Court","Central","High"),
    ("07","Eastfield District Court","Eastern","District"),
    ("08","Cape Lawson District Court","Eastern","District"),
    ("09","Southgate District Court","Southern","District"),
    ("10","Fernbay District Court","Southern","District"),
    ("11","Southern Ranges High Court","Southern","High"),
    ("12","Willow Creek District Court","Southern","District"),
]
TYPES = ["Family","Youth","Civil","Criminal"]
# deliberate dirty variants
TYPE_VARIANTS = {
 "Family":["Family","family","FAMILY","Family ", " Family","Fam","Family Court"],
 "Youth":["Youth","youth","YOUTH","Yth","Youth "],
 "Civil":["Civil","civil","CIVIL"," Civil"],
 "Criminal":["Criminal","criminal","CRIMINAL","Crim","Criminal "],
}
STATUS_VARIANTS = {"Active":["Active","active","ACTIVE","Active "],
                   "Disposed":["Disposed","disposed","DISPOSED"]}

start = dt.date(2024,7,1)
end   = dt.date(2026,6,30)
span  = (end-start).days
today = dt.date(2026,9,1)

# base median duration per type (days)
BASE = {"Family":210,"Youth":95,"Civil":170,"Criminal":140}
# court multipliers - Mistvale (05) and Cape Lawson (08) run slow
COURT_MULT = {c[0]:1.0 for c in COURTS}
COURT_MULT["05"]=1.55; COURT_MULT["08"]=1.40; COURT_MULT["02"]=0.82; COURT_MULT["10"]=0.88
# Eastern region deteriorates over the period
def region_drift(region, filed):
    months = (filed.year-2024)*12 + filed.month - 7
    if region=="Eastern": return 1.0 + 0.022*months
    if region=="Central": return 1.0 + 0.006*months
    return 1.0

rows=[]
n=0
seq=1000
while n < 4200:
    court = random.choice(COURTS)
    cid, cname, region, ctype = court
    ctype_case = random.choices(TYPES, weights=[26,14,25,35])[0]
    filed = start + dt.timedelta(days=random.randint(0,span))
    # december/january filing dip
    if filed.month in (12,1) and random.random()<0.42:
        continue
    mult = COURT_MULT[cid]*region_drift(region, filed)
    if ctype=="High": mult *= 1.25
    mean = BASE[ctype_case]*mult
    dur = max(3, int(random.lognormvariate(0, 0.62) * mean * 0.78))
    disposed = filed + dt.timedelta(days=dur)
    seq += 1
    case_id = f"{seq:06d}"
    if disposed > today or random.random() < 0.06:
        disposed_s = ""
        status = "Active"
    else:
        disposed_s = disposed.strftime("%d/%m/%Y")
        status = "Disposed"
    days_txt = "" if not disposed_s else str(dur)
    rows.append({
        "case_id": case_id,
        "court_id": cid,
        "case_type": random.choice(TYPE_VARIANTS[ctype_case]),
        "filed_date": filed.strftime("%d/%m/%Y"),
        "disposed_date": disposed_s,
        "status": random.choice(STATUS_VARIANTS[status]),
        "reported_days": days_txt,
    })
    n+=1

# ---- inject defects ----
# 1. duplicate case_ids (38 rows, some with a differing status = superseded extract)
for r in random.sample(rows, 38):
    d = dict(r)
    if d["status"].strip().lower()=="disposed" and random.random()<0.5:
        d["disposed_date"]=""; d["status"]="Active"; d["reported_days"]=""
    rows.append(d)

# 2. impossible: disposed before filed (14)
for r in random.sample([x for x in rows if x["disposed_date"]], 14):
    f = dt.datetime.strptime(r["filed_date"], "%d/%m/%Y").date()
    r["disposed_date"] = (f - dt.timedelta(days=random.randint(2,60))).strftime("%d/%m/%Y")

# 3. future filing dates (5)
for r in random.sample(rows, 5):
    r["filed_date"] = (today + dt.timedelta(days=random.randint(20,300))).strftime("%d/%m/%Y")

# 4. orphan court_ids not in the lookup (22)
for r in random.sample(rows, 22):
    r["court_id"] = random.choice(["13","14","99"])

# 5. missing court_id (9)
for r in random.sample(rows, 9):
    r["court_id"] = random.choice(["", "Unknown", "-"])

# 6. reported_days as messy text (whitespace, N/A, a few wrong)
for r in random.sample([x for x in rows if x["reported_days"]], 260):
    v = r["reported_days"]
    r["reported_days"] = random.choice([f" {v}", f"{v} ", f"  {v}  ", "N/A", "-", v.replace(v, v)])
for r in random.sample([x for x in rows if x["reported_days"] not in ("","N/A","-")], 30):
    try: r["reported_days"] = str(int(r["reported_days"].strip()) + random.choice([-30,-10,10,45]))
    except: pass

random.shuffle(rows)

with open("cases_raw.csv","w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f, fieldnames=["case_id","court_id","case_type","filed_date","disposed_date","status","reported_days"])
    w.writeheader(); w.writerows(rows)

with open("courts.csv","w",newline="",encoding="utf-8") as f:
    w=csv.writer(f); w.writerow(["court_id","court_name","region","court_type"])
    for c in COURTS: w.writerow(list(c))

print("cases_raw.csv rows:", len(rows))
print("courts.csv rows:", len(COURTS))
