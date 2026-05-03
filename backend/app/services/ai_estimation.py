"""
AI / Rule-based Estimation Engine — Scope 3 Missing Data (v8)

Priority:
  1. XGBoost ML model — categories 1, 2, 13, 14, 15  (requires NIC + region)
  2. Rule-based DEFRA/IPCC spend factor — all 15 categories (fallback)
  3. None — if spend_inr is missing or zero

Confidence always capped at 0.75 (C-grade per GHG Protocol Tier 3).
"""
from datetime import date
from typing import Any, Optional
from app.services.ml_client import MLServiceError, estimate_spend

ML_SPEND_CATEGORIES  = {1, 2, 13, 14, 15}
ALL_SPEND_CATEGORIES = set(range(1, 16))

# DEFRA/IPCC/PCAF spend intensity kgCO2e per 1000 INR
_RULE_EF = {
    1: {"ef":0.43,"src":"DEFRA 2024 — manufacturing"},
    2: {"ef":0.38,"src":"DEFRA 2024 — capital goods"},
    3: {"ef":0.51,"src":"DEFRA 2024 — energy upstream"},
    4: {"ef":0.29,"src":"DEFRA 2024 — transport & logistics"},
    5: {"ef":0.35,"src":"DEFRA 2024 — waste management"},
    6: {"ef":0.22,"src":"DEFRA 2024 — travel & accommodation"},
    7: {"ef":0.18,"src":"DEFRA 2024 — local transport"},
    8: {"ef":0.29,"src":"DEFRA 2024 — downstream transport"},
    9: {"ef":0.47,"src":"IPCC AR6 — industrial processing"},
    10:{"ef":0.41,"src":"IPCC AR6 — product lifetime energy"},
    11:{"ef":0.33,"src":"DEFRA 2024 — end-of-life waste"},
    12:{"ef":0.45,"src":"CPCB 2023 — leased assets energy"},
    13:{"ef":0.38,"src":"IPCC AR6 — franchise revenue-based"},
    14:{"ef":0.52,"src":"PCAF 2023 — investment portfolio"},
    15:{"ef":0.40,"src":"IPCC AR6 — industry-specific"},
}
_CAT_NAMES = {
    1:"Purchased Goods & Services",2:"Capital Goods",3:"Fuel & Energy (not S1/S2)",
    4:"Upstream Transport",5:"Waste in Operations",6:"Business Travel",
    7:"Employee Commuting",8:"Downstream Transport",9:"Processing of Sold Products",
    10:"Use of Sold Products",11:"End-of-Life Treatment",12:"Leased Assets",
    13:"Franchises",14:"Investments",15:"Other / Custom",
}

def _nic(raw):
    if raw is None: return None
    digits="".join(c for c in str(raw) if c.isdigit())
    return int(digits) if digits else None

def _rgn(raw):
    if raw is None: return None
    v=getattr(raw,"value",raw)
    return str(v).strip().lower() or None

def _rule(cat, spend, year):
    m=_RULE_EF[cat]; ef=m["ef"]
    adj=1.0+max(-0.30,min(0.30,(2024-year)*0.015))
    tco2=round((spend/1000)*ef*adj/1000,4)
    return {
        "estimated_value":tco2,"estimated_co2e":tco2,
        "confidence_score":0.45,"confidence_band":[round(tco2*0.65,4),round(tco2*1.35,4)],
        "explanation":(f"Rule-based spend estimate for {_CAT_NAMES[cat]}. "
                       f"₹{spend:,.0f} × {ef} kgCO₂e/1000 INR ({m['src']}). "
                       "Data Quality C — replace with primary activity data for GRI reporting."),
        "model_used":f"Rule-based ({m['src'].split('—')[0].strip()})",
        "data_quality":"C",
        "inputs_used":{"category_id":cat,"spend_inr":spend,"year":year},
        "methodology_reference":f"GHG Protocol Category {cat} spend-based — {m['src']}",
    }

def estimate_spend_based_emissions(category_id, available_data, vendor_profile=None):
    if category_id not in ALL_SPEND_CATEGORIES: return None
    vendor_profile=vendor_profile or {}
    spend=available_data.get("spend_inr") or available_data.get("activity_value")
    year=int(available_data.get("year") or date.today().year)
    if not spend or float(spend)<=0: return None
    spend=float(spend)

    if category_id in ML_SPEND_CATEGORIES:
        nic=(_nic(available_data.get("nic_4digit"))
             or _nic(vendor_profile.get("nic_4digit") or vendor_profile.get("nic_code")))
        rgn=(_rgn(available_data.get("region")) or _rgn(vendor_profile.get("region")))
        if nic and rgn:
            try:
                pred=estimate_spend(spend_inr=spend,nic_4digit=int(nic),region=str(rgn),year=year)
                val=float(pred["estimated_co2e"])
                band=[float(v) for v in pred.get("confidence_band",[])]
                cs=(round(max(0.05,min(0.75,1-(band[1]-band[0])/(2*val))),2)
                    if len(band)==2 and val>0 else 0.50)
                return {
                    "estimated_value":round(val,4),"estimated_co2e":round(val,4),
                    "confidence_score":cs,"confidence_band":band,
                    "explanation":(f"ML spend estimate for {_CAT_NAMES[category_id]} "
                                   f"({pred['model_used']}, NIC {nic}, {rgn}). "
                                   "Data Quality C — replace with primary data for GRI reporting."),
                    "model_used":pred["model_used"],"data_quality":pred.get("data_quality","C"),
                    "inputs_used":{"category_id":category_id,"spend_inr":spend,
                                   "nic_4digit":int(nic),"region":str(rgn),"year":year},
                    "methodology_reference":f"GHG Protocol Category {category_id} — DEFRA/EEIO ML model",
                }
            except MLServiceError:
                pass
    return _rule(category_id, spend, year)
