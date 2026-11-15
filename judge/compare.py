"""Compare scores across LTV tiers and prompt versions.

  python judge/compare.py v1            # one version: tier table
  python judge/compare.py v1 v2 v3      # several: also a version-by-version table
  python judge/compare.py               # every version in results/

Writes results/<version>/tier_summary.csv and results/comparison.csv.

Columns per rubric:
  Low / Medium / High   mean score of scored chats in that tier
  High-Low              gap between the top and bottom tier
  rho_ltv               Spearman correlation of the score with LTV (all tiers);
                        rubrics with a clear positive value separate valuable
                        users' first chats from the rest
  scored%               share of chats where the rubric was not skipped
"""
import glob
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import outcomes  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIERS = ["Low", "Medium", "High"]


def tier_summary(version):
    df = pd.read_csv(os.path.join(ROOT, "results", version, "scores.csv"))
    ok = df[df.status == "ok"].copy()
    cols = (["final", "rubric_score", "blueprint", "ideal_pct", "overall", "B1", "B2", "B3", "B4", "B5"]
            + [c for c in ok.columns if c.startswith("r") and c[1:2].isdigit()]
            + [c for c in ok.columns if c[:1] == "S" and c[1:].isdigit()]
            + [c for c in ok.columns if c.startswith("on_time_")])
    rows = []
    for c in cols:
        if c not in ok:
            continue
        row = {"metric": c.lstrip("r") if c.startswith("r") else c}
        for t in TIERS:
            s = ok.loc[ok.tier == t, c].dropna()
            row[t] = round(s.mean(), 2) if len(s) else None
        row["High-Low"] = round(row["High"] - row["Low"], 2) if None not in (row["High"], row["Low"]) else None
        pair = ok[[c, "ltv"]].dropna()
        row["rho_ltv"] = round(pair[c].rank().corr(pair["ltv"].rank()), 2) if len(pair) > 5 else None
        row["scored%"] = round(100 * ok[c].notna().mean())
        rows.append(row)
    extra = {"metric": "gate_fail%"}
    for t in TIERS:
        s = ok.loc[ok.tier == t, "gate_fail"]
        extra[t] = round(100 * s.notna().mean(), 1) if len(s) else None
    n = {"metric": "n_chats"}
    for t in TIERS:
        n[t] = int((ok.tier == t).sum())
    n["scored%"] = f"{len(ok)}/{len(df)} judged"
    labels = []
    if "label" in ok:
        for lab in ("good", "mixed", "bad"):
            row = {"metric": f"{lab}%"}
            for t in TIERS:
                s = ok.loc[ok.tier == t, "label"]
                row[t] = round(100 * (s == lab).mean(), 1) if len(s) else None
            labels.append(row)
    out = pd.DataFrame([n, extra] + labels + rows)
    out.to_csv(os.path.join(ROOT, "results", version, "tier_summary.csv"), index=False)
    return out


def outcome_check(version):
    """Do the labels line up with what users did after the first chat?"""
    df = pd.read_csv(os.path.join(ROOT, "results", version, "scores.csv"))
    if "label" not in df or df["label"].isna().all():
        return None
    rows = []
    for _, r in df.iterrows():
        o = outcomes.compute(os.path.join(ROOT, r["tier"], r["file"]))
        rows.append({**o, "label": r["label"], "final": r.get("final"), "tier": r["tier"]})
    o = pd.DataFrame(rows)
    order = [l for l in ("good", "mixed", "bad", "bad_no_service") if l in set(o["label"])]
    tab = o.groupby("label").agg(chats=("label", "size"), n_consults=("n_consults", "mean"),
                                 consults_7d=("consults_7d", "mean"),
                                 median_return_min=("return_min", "median"),
                                 first_chat_min=("first_chat_min", "median")).reindex(order).round(2)
    j = o.dropna(subset=["final"])
    corr = {}
    for t in ["all"] + TIERS:
        x = j if t == "all" else j[j.tier == t]
        if len(x) > 5:
            corr[t] = {k: round(x["final"].rank().corr(x[k].rank()), 2)
                       for k in ("n_consults", "consults_7d", "return_min")}
    tab.to_csv(os.path.join(ROOT, "results", version, "outcome_check.csv"))
    return tab, pd.DataFrame(corr).T


def main():
    versions = sys.argv[1:] or sorted(os.path.basename(os.path.dirname(p))
                                      for p in glob.glob(os.path.join(ROOT, "results", "*", "scores.csv")))
    pd.set_option("display.width", 200, "display.max_rows", 100)
    allv = []
    for v in versions:
        s = tier_summary(v)
        print(f"\n===== {v} =====")
        print(s.to_string(index=False))
        oc = outcome_check(v)
        if oc is not None:
            print(f"\n--- {v}: labels vs what users did next (same astrologer) ---")
            print(oc[0].to_string())
            print("rank correlation of final score with outcomes (return_min: lower is better):")
            print(oc[1].to_string())
        s.insert(0, "version", v)
        allv.append(s)
    if len(allv) > 1:
        comp = pd.concat(allv)
        comp.to_csv(os.path.join(ROOT, "results", "comparison.csv"), index=False)
        piv = comp[comp.metric.isin(["final", "blueprint", "rubric_score", "overall", "B1", "B2", "B3", "B4", "B5"])].pivot(
            index="metric", columns="version", values=["High-Low", "rho_ltv"])
        print("\n===== across versions (separation of High vs Low) =====")
        print(piv.to_string())


if __name__ == "__main__":
    main()
