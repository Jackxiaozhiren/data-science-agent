#!/usr/bin/env python3
"""Deterministic synthetic benchmark datasets — seed 42, public domain."""
from __future__ import annotations
import random, math, csv
from pathlib import Path

R = random.Random(42)
ROOT = Path(__file__).resolve().parents[1] / "benchmarks" / "ds-agent-benchmark" / "datasets"
ROOT.mkdir(parents=True, exist_ok=True)

def write_csv(path: Path, header: list[str], rows: list[list[object]]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

# 1-4 Sales / Retail
for name, n in [("sales.csv", 500), ("retail_sales.csv", 600), ("marketing.csv", 400), ("financial.csv", 500)]:
    rows = []
    for i in range(n):
        region = R.choice(["East","West","North","South"])
        cat = R.choice(["A","B","C"])
        price = round(R.uniform(10, 100), 2)
        units = R.randint(1, 50)
        revenue = round(price * units * R.uniform(0.9, 1.1), 2)
        date = f"2024-{(i%12)+1:02d}-{(i%28)+1:02d}"
        rows.append([date, region, cat, price, units, revenue])
    write_csv(ROOT / name, ["date","region","category","price","units","revenue"], rows)

# 5-7 Churn / Titanic-like / Housing
rows = []
for i in range(600):
    tenure = R.randint(0, 72)
    monthly = round(R.uniform(20, 120),2)
    total = round(tenure * monthly * R.uniform(0.9,1.1),2)
    churn = 1 if R.random() < (0.3 if tenure<12 else 0.1) else 0
    rows.append([tenure, monthly, total, R.choice(["Yes","No"]), churn])
write_csv(ROOT / "customer_churn.csv", ["tenure","monthly_charges","total_charges","partner","churn"], rows)

rows=[]
for i in range(900):
    pclass = R.choice([1,2,3]); sex = R.choice(["male","female"]); age = R.randint(1,80) if R.random()>0.05 else ""
    fare = round(R.uniform(5, 200),2); survived = 1 if (sex=="female" and R.random()<0.7) or (pclass==1 and R.random()<0.6) else (1 if R.random()<0.2 else 0)
    rows.append([pclass, sex, age, fare, survived])
write_csv(ROOT / "titanic.csv", ["pclass","sex","age","fare","survived"], rows)

rows=[]
for i in range(500):
    area = R.randint(500, 4000); beds = R.randint(1,6); age = R.randint(0,50)
    price = round(area*120 + beds*8000 - age*500 + R.gauss(0, 15000),2)
    rows.append([area, beds, age, price])
write_csv(ROOT / "house_prices.csv", ["area","bedrooms","age","price"], rows)

# 8-11 Health / Energy / Public Health-ish / HR
rows=[]
for i in range(400):
    bmi = round(R.uniform(18, 35),1); bp = R.randint(90, 160); chol = R.randint(150, 280)
    disease = 1 if bmi>30 and bp>140 else (1 if R.random()<0.1 else 0)
    rows.append([bmi, bp, chol, disease])
write_csv(ROOT / "health.csv", ["bmi","bp","chol","disease"], rows)

rows=[]
for i in range(500):
    temp = round(R.uniform(-5, 35),1); hour = i%24; demand = round(200 + hour*5 + temp*3 + R.gauss(0,10),1)
    rows.append([hour, temp, demand])
write_csv(ROOT / "energy.csv", ["hour","temp","demand"], rows)

rows=[]
for i in range(600):
    exp = R.randint(0,15); score = round(min(100, 60 + exp*2 + R.gauss(0,5)),1); promoted = 1 if score>75 and R.random()<0.7 else 0
    rows.append([exp, score, promoted])
write_csv(ROOT / "hr_promotion.csv", ["experience","score","promoted"], rows)

rows=[]
for i in range(300):
    spend = round(R.uniform(100, 10000),2); clicks = R.randint(10, 1000); conv = round(clicks * 0.05 * R.uniform(0.8,1.2),1)
    rows.append([spend, clicks, conv])
write_csv(ROOT / "ads.csv", ["spend","clicks","conversions"], rows)

# 12-15 Time series
for name, base in [("timeseries.csv", 0), ("timeseries_trend.csv", 1), ("timeseries_seasonal.csv", 2)]:
    rows=[]
    for t in range(300):
        trend = t*0.5 if base==1 else 0
        seasonal = 10*math.sin(2*math.pi*t/30) if base==2 else 0
        val = round(100 + trend + seasonal + R.gauss(0,5),2)
        rows.append([f"2024-01-{(t%28)+1:02d}", val])
    write_csv(ROOT / name, ["date","value"], rows)

rows=[]
for t in range(200):
    rows.append([t, round(50 + R.gauss(0,10),2), round(52 + R.gauss(0,10),2)])
write_csv(ROOT / "paired_series.csv", ["t","series_a","series_b"], rows)

# 16-20 Misc EDA / Data quality / Correlation / Groups
rows=[]
for i in range(400):
    x = R.gauss(0,1); y = x*0.8 + R.gauss(0,0.6); z = R.gauss(0,1)
    rows.append([round(x,3), round(y,3), round(z,3), R.choice(["X","Y","Z"])])
write_csv(ROOT / "correlation.csv", ["x","y","z","group"], rows)

rows=[]
for i in range(500):
    g = R.choice(["A","B","C"]); v = round(R.gauss(10 if g=="A" else (12 if g=="B" else 15), 2),2)
    rows.append([g, v])
write_csv(ROOT / "groups.csv", ["group","value"], rows)

rows=[]
for i in range(300):
    a = R.randint(1,10); b = "" if R.random()<0.08 else R.randint(1,10)
    c = R.randint(1,5) if R.random()<0.03 else R.randint(1,100)
    rows.append([a,b,c])
write_csv(ROOT / "data_quality.csv", ["a","b","c"], rows)

rows=[]
for i in range(250):
    # include outlier
    v = 1000 if i==0 else round(R.gauss(50,10),1)
    rows.append([v, R.choice(["M","F"]), R.randint(20,60)])
write_csv(ROOT / "outliers.csv", ["value","sex","age"], rows)

rows=[]
for i in range(400):
    region = R.choice(["North","South","East"]); rev = round(R.uniform(1000, 5000),2)
    rows.append([region, rev])
write_csv(ROOT / "region_revenue.csv", ["region","revenue"], rows)

print(f"Wrote {len(list(ROOT.glob('*.csv')))} datasets to {ROOT}")
