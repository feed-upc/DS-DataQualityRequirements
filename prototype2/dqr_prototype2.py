#!/usr/bin/env python3
"""
prototype2/dqr_prototype2.py — v3 (HTML design port)

Design changes from v2:
  • Dark sidebar with step indicator and coverage mini-panel
  • Intent-first wizard restructured into 4 clean steps:
      1. Quality Dimension (tiles with color bar, icon, description, count badge)
      2. Rule Pattern (cards with human-readable names and example sentences)
      3. Define the Rule (Mad Libs sentence preview above smart input grid)
      4. Governance & save (side-by-side with pattern reference image)
  • Live sentence preview updates as parameters are filled (blue=filled, orange=empty)
  • Right-column live policy preview card in step 3
  • ODRL stays hidden in expert expanders

Run:  streamlit run dqr_prototype2.py
"""

import base64
import json
import os
import re
import subprocess
from datetime import date
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

# ── Paths ──────────────────────────────────────────────────────────────────────
HERE         = Path(__file__).resolve().parent
CATS         = HERE.parent
PATTERNS_DIR = CATS / "prototype" / "patterns"
REQS_DIR     = CATS / "prototype" / "requirements"
ODRL_TMPL    = CATS / "prototype" / "odrl_templates"
ODRL_RULES   = CATS / "prototype" / "odrl_rules"
MEDIA2_DIR   = CATS / "media2"
API_URL      = os.environ.get("VALIDATION_API_URL", "http://localhost:5000")

# ── Dimension palette ──────────────────────────────────────────────────────────
DIM_COLORS = {
    "Completeness": "#2563EB",
    "Currentness":  "#0891B2",
    "Compliance":   "#7C3AED",
    "Consistency":  "#EA580C",
    "Fairness":     "#059669",
    "Accuracy":     "#DC2626",
    "Credibility":  "#0D9488",
}
DIM_ICONS = {
    "Completeness": "📊",
    "Currentness":  "⏱️",
    "Compliance":   "📋",
    "Consistency":  "🔗",
    "Fairness":     "⚖️",
    "Accuracy":     "🎯",
    "Credibility":  "🏅",
}
DIM_DESCS = {
    "Completeness": "All required fields are present and populated",
    "Currentness":  "Data is up-to-date within acceptable time bounds",
    "Compliance":   "Data conforms to specified standards and formats",
    "Consistency":  "Values are internally coherent and logically sound",
    "Fairness":     "All groups are represented without discriminatory bias",
    "Accuracy":     "Values are correct, precise, and free from error",
    "Credibility":  "Data is trustworthy and comes from a reliable source",
}
PATTERN_NAMES = {
    "DQRP1": "Data Freshness Limit",
    "DQRP2": "Mandatory Field Completeness",
    "DQRP3": "Format Standard Conformance",
    "DQRP4": "Cross-attribute Value Consistency",
    "DQRP5": "Minimum Record Count",
    "DQRP6": "Group Representation Balance",
}
PATTERN_EXAMPLES = {
    "DQRP1": '"Observations must be no older than 24 hours at time of query."',
    "DQRP2": '"Fields patientId, birthDate, and gender must all be present in every record."',
    "DQRP3": '"Diagnoses must be coded according to ICD-10 (2024 edition)."',
    "DQRP4": '"If condition is \'Deceased\', then dateOfDeath must be populated."',
    "DQRP5": '"The Patient Summary dataset must contain at least 1,000 records."',
    "DQRP6": '"No single age group may represent more than 60% of the dataset."',
}
BRAND = "#2563EB"

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DQR Catalog",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styles ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
/* ── Global ──────────────────────────────────────────────────────────────────── */
body, .stApp {{ background: #EEF2FA !important; }}
.main .block-container {{ max-width: 1100px; padding-top: 1.5rem; }}

/* ── Dark sidebar ─────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {{
    background: #1a2e55 !important;
}}
[data-testid="stSidebar"] > div {{
    padding: 0 !important;
}}
[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] p {{
    color: rgba(255,255,255,0.85) !important;
}}
[data-testid="stSidebar"] .stButton > button {{
    background: rgba(255,255,255,0.07) !important;
    color: rgba(255,255,255,0.8) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 8px !important;
    font-size: 0.85rem !important;
    transition: background 0.15s !important;
}}
[data-testid="stSidebar"] .stButton > button:hover {{
    background: rgba(255,255,255,0.13) !important;
    color: white !important;
}}

/* Sidebar logo */
.sb-logo {{
    display: flex; align-items: center; gap: 10px;
    margin-bottom: 24px; padding: 20px 18px 0;
}}
.sb-logo-mark {{
    width: 34px; height: 34px; background: #3B82F6; border-radius: 9px;
    display: grid; place-items: center; font-size: 16px; flex-shrink: 0;
}}
.sb-logo-text {{ font-size: 17px; font-weight: 800; color: white; line-height: 1.2; }}
.sb-logo-sub  {{ font-size: 10px; color: #64A2FF; font-weight: 500; }}

.sb-section-label {{
    font-size: 10px; font-weight: 700; color: #5B7DB8;
    text-transform: uppercase; letter-spacing: 0.1em;
    margin-bottom: 8px; padding: 0 18px; display: block;
}}

/* Step rows */
.sb-step {{
    display: flex; align-items: flex-start; gap: 11px;
    padding: 8px 12px; border-radius: 8px; margin: 1px 8px;
}}
.sb-step.active {{ background: rgba(59,130,246,0.18); }}
.sb-step.done   {{ opacity: 0.75; }}
.sb-bubble {{
    width: 24px; height: 24px; border-radius: 50%;
    border: 2px solid rgba(255,255,255,0.2);
    font-size: 10px; font-weight: 700; color: rgba(255,255,255,0.5);
    display: grid; place-items: center; flex-shrink: 0; margin-top: 2px;
}}
.sb-step.active .sb-bubble {{ background: #3B82F6; border-color: #3B82F6; color: white; }}
.sb-step.done   .sb-bubble {{ background: #10B981; border-color: #10B981; color: white; }}
.sb-step-name {{ font-size: 13px; font-weight: 600; color: rgba(255,255,255,0.85); }}
.sb-step-hint {{ font-size: 11px; color: #5B7DB8; margin-top: 2px; }}
.sb-step.active .sb-step-hint {{ color: #93C5FD; }}
.sb-connector {{
    width: 2px; height: 11px; background: rgba(255,255,255,0.08);
    margin: 0 0 0 29px;
}}

/* Coverage mini-panel */
.sb-cov-panel {{
    padding: 14px 18px 20px;
    border-top: 1px solid rgba(255,255,255,0.07);
    margin-top: 12px;
}}
.sb-cov-row {{
    display: flex; align-items: center; gap: 8px;
    padding: 4px 4px; border-radius: 6px; margin-bottom: 3px;
}}
.sb-cov-pip {{ width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }}
.sb-cov-name {{ font-size: 12px; color: rgba(255,255,255,0.65); flex: 1; }}
.sb-cov-badge {{
    font-size: 10px; font-weight: 700; padding: 1px 7px; border-radius: 20px;
    background: rgba(255,255,255,0.08); color: rgba(255,255,255,0.5);
}}
.sb-cov-badge.has {{ background: rgba(16,185,129,0.2); color: #6EE7B7; }}

/* ── Page header ──────────────────────────────────────────────────────────────── */
.dqr-header {{
    background: linear-gradient(135deg, #1a2e55 0%, {BRAND} 100%);
    padding: 1.75rem 2rem; border-radius: 14px;
    color: white; margin-bottom: 1.75rem;
}}
.dqr-header h1 {{ font-size: 1.9rem; margin: 0 0 0.35rem; font-weight: 800; }}
.dqr-header p  {{ font-size: 0.97rem; margin: 0; opacity: 0.85; }}

.breadcrumb {{
    font-size: 0.83rem; color: #64748B;
    margin-bottom: 1.25rem; display: flex; align-items: center; gap: 6px;
}}
.breadcrumb b {{ color: #0F172A; font-weight: 600; }}

/* ── Home tool cards ──────────────────────────────────────────────────────────── */
.tool-card {{
    border: 1.5px solid #dce3ef; border-radius: 14px;
    padding: 1.4rem 1.5rem; background: white; height: 100%;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}}
.card-icon  {{ font-size: 1.9rem; margin-bottom: 0.6rem; }}
.card-title {{ font-size: 1.05rem; font-weight: 700; color: #1a2e55; margin-bottom: 0.4rem; }}
.card-desc  {{ font-size: 0.875rem; color: #555; line-height: 1.5; }}

/* ── Dimension tiles (step 1) ─────────────────────────────────────────────────── */
.dim-tile {{
    background: white; border-radius: 14px;
    padding: 20px 14px 14px; border: 2px solid transparent;
    position: relative; overflow: hidden;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    text-align: center; margin-bottom: 6px;
}}
.dim-tile-bar {{
    position: absolute; top: 0; left: 0; right: 0;
    height: 4px; border-radius: 12px 12px 0 0;
}}
.dim-tile-icon {{ font-size: 1.9rem; margin: 6px 0 8px; }}
.dim-tile-name {{ font-size: 0.87rem; font-weight: 700; margin-bottom: 5px; color: #0F172A; }}
.dim-tile-desc {{ font-size: 0.74rem; color: #64748B; line-height: 1.4; }}
.dim-count-badge {{
    position: absolute; top: 8px; right: 8px;
    font-size: 10px; font-weight: 700; color: white;
    padding: 1px 7px; border-radius: 20px; line-height: 1.5;
}}

/* ── Pattern cards (step 2) ───────────────────────────────────────────────────── */
.pcard {{
    background: white; border-radius: 12px;
    border: 2px solid #E2E8F0; padding: 20px 22px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 4px;
}}
.pcard-pid  {{
    font-size: 10px; font-weight: 700; color: #94A3B8;
    letter-spacing: 0.06em; text-transform: uppercase; margin-bottom: 3px;
}}
.pcard-name {{ font-size: 1.05rem; font-weight: 700; color: #0F172A; margin-bottom: 8px; }}
.pcard-desc {{ font-size: 0.85rem; color: #64748B; margin-bottom: 10px; line-height: 1.5; }}
.pcard-ex-label {{
    font-size: 9px; font-weight: 700; color: #93C5FD;
    text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 3px;
}}
.pcard-example {{
    background: #F0F7FF; border-left: 3px solid #3B82F6;
    padding: 8px 12px; border-radius: 0 7px 7px 0;
    font-size: 0.83rem; color: #1E40AF; font-style: italic;
    margin-bottom: 10px; line-height: 1.5;
}}

/* ── Mad Libs builder (step 3) ────────────────────────────────────────────────── */
.builder-card {{
    background: white; border-radius: 14px;
    padding: 22px 24px; box-shadow: 0 1px 4px rgba(0,0,0,0.07); margin-bottom: 14px;
}}
.builder-label {{
    font-size: 10px; font-weight: 700; color: #94A3B8;
    text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 12px;
}}
.sentence-wrap {{
    font-size: 1.08rem; line-height: 2.4; color: #0F172A;
}}
.sp-filled {{
    color: #1D4ED8; font-weight: 700;
    background: #DBEAFE; border-radius: 4px; padding: 2px 7px;
}}
.sp-empty {{
    color: #EA580C; font-weight: 500;
    background: #FFF7ED; border-radius: 4px; padding: 2px 7px;
    border-bottom: 2px solid #EA580C; font-style: italic;
}}

/* ── Live policy preview (step 3 right panel) ─────────────────────────────────── */
.policy-box {{
    border: 2px solid #10B981; border-radius: 11px;
    padding: 16px; background: #F0FDF4; margin-bottom: 12px;
}}
.policy-box-hdr {{
    display: flex; align-items: center; gap: 8px;
    font-size: 0.82rem; font-weight: 700; color: #065F46; margin-bottom: 8px;
}}
.policy-stmt-text {{
    font-size: 0.83rem; color: #374151; font-style: italic;
    line-height: 1.6; margin-bottom: 12px; min-height: 40px;
}}
.policy-stmt-text.dim {{ color: #9CA3AF; }}
.pm-row {{ display: flex; gap: 6px; font-size: 0.78rem; margin-bottom: 3px; }}
.pm-label {{ font-weight: 600; color: #6B7280; min-width: 72px; }}
.pm-val   {{ color: #1F2937; }}

/* ── Shared legacy helpers ────────────────────────────────────────────────────── */
.policy-card {{
    border: 2px solid #10b981; border-radius: 10px;
    padding: 1.2rem 1.4rem; background: #f0fdf4; margin: 0.8rem 0;
}}
.pc-header {{ font-weight: 700; color: #065f46; font-size: 1rem; margin-bottom: 0.6rem; }}
.pc-row    {{ display: flex; gap: 0.6rem; margin: 0.25rem 0; font-size: 0.9rem; }}
.pc-label  {{ font-weight: 600; color: #374151; min-width: 120px; }}
.pc-value  {{ color: #1f2937; }}

.stmt-preview {{
    background: #f0f7ff; border-left: 4px solid {BRAND};
    border-radius: 6px; padding: 1rem 1.2rem;
    font-size: 0.97rem; line-height: 1.65; margin: 0.6rem 0;
}}
.stmt-confirm {{
    background: #f0fdf4; border: 2px solid #10b981;
    border-radius: 10px; padding: 1rem 1.25rem;
    font-size: 1rem; color: #065f46; font-style: italic;
    line-height: 1.6; margin-bottom: 1.25rem;
}}

.conflict-box {{
    background: #fff7ed; border: 1.5px solid #f59e0b;
    border-radius: 8px; padding: 0.75rem 1rem;
    font-size: 0.87rem; margin: 0.4rem 0;
}}
.dep-box {{
    background: #eff6ff; border: 1.5px solid #93c5fd;
    border-radius: 8px; padding: 0.75rem 1rem;
    font-size: 0.87rem; margin: 0.4rem 0;
}}
.dim-badge {{
    display: inline-block; border-radius: 20px; padding: 2px 10px;
    font-size: 0.78rem; font-weight: 600; color: white; margin-bottom: 0.4rem;
}}
.tool-card {{ border: 1.5px solid #dce3ef; border-radius: 12px; padding: 1.25rem 1.4rem; background: #fafcff; height: 100%; }}
.cov-tile {{
    border-radius: 10px; padding: 0.85rem 0.5rem;
    text-align: center; margin-bottom: 0.5rem;
}}
.step-bar  {{ display: flex; margin-bottom: 1.5rem; }}
.step-item {{
    flex: 1; text-align: center; padding: 0.5rem 0.25rem;
    font-size: 0.82rem; font-weight: 600;
    border-bottom: 3px solid #dce3ef; color: #aaa;
}}
.step-item.active {{ border-bottom-color: {BRAND}; color: {BRAND}; }}
.step-item.done   {{ border-bottom-color: #10b981; color: #10b981; }}

/* Success state */
.success-wrap {{ text-align: center; padding: 2.5rem 1rem; }}
.success-ring {{
    width: 72px; height: 72px; border-radius: 50%;
    background: #D1FAE5; display: grid; place-items: center;
    font-size: 30px; margin: 0 auto 18px;
}}
.success-h {{ font-size: 1.5rem; font-weight: 800; color: #065F46; margin-bottom: 8px; }}
.success-p {{
    font-size: 0.95rem; color: #374151; font-style: italic;
    max-width: 540px; margin: 0 auto 22px; line-height: 1.65;
}}
</style>
""", unsafe_allow_html=True)


# ── Data loaders ───────────────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def load_patterns() -> list[dict]:
    items = []
    for f in sorted(PATTERNS_DIR.glob("DQRP*.json")):
        try:
            items.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            pass
    return items


@st.cache_data(ttl=10)
def load_requirements() -> list[dict]:
    items = []
    for f in sorted(REQS_DIR.glob("DQR[0-9]*.json")):
        try:
            items.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            pass
    return items


def load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        st.error(f"Error reading {path.name}: {e}")
        return None


def save_json(path: Path, data: dict) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return True
    except Exception as e:
        st.error(f"Error saving {path.name}: {e}")
        return False


def find_by_id(items: list, item_id: str) -> dict | None:
    return next((x for x in items if x.get("id") == item_id), None)


# ── Media2 helpers ─────────────────────────────────────────────────────────────

def get_pattern_image(pattern: dict) -> Path | None:
    pid = pattern["id"]
    dim = pattern_primary_dim(pattern)
    p = MEDIA2_DIR / pid / f"{pid}-{dim}.png"
    return p if p.exists() else None


def get_instantiation_image(req: dict) -> Path | None:
    pid = req.get("pattern", {}).get("id", "")
    rid = req["id"]
    p = MEDIA2_DIR / pid / f"{rid}Instantiation.png"
    return p if p.exists() else None


def show_pattern_image(pattern: dict, caption: str = ""):
    img = get_pattern_image(pattern)
    if img:
        st.image(str(img), caption=caption or f"{pattern['id']} pattern card",
                 use_container_width=True)


def show_instantiation_image(req: dict, caption: str = ""):
    img = get_instantiation_image(req)
    if img:
        st.image(str(img), caption=caption or f"{req['id']} card",
                 use_container_width=True)


def _try_regen_media2(req: dict):
    script = MEDIA2_DIR / "generate_media.py"
    if not script.exists():
        return
    try:
        subprocess.run(
            ["python", str(script), req["id"]],
            cwd=str(MEDIA2_DIR),
            capture_output=True,
            timeout=30,
        )
    except Exception:
        pass


# ── Smart parameter inputs ─────────────────────────────────────────────────────

def _norm(s: str) -> str:
    return s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")


def _enum_opts(inv_str: str) -> list[str] | None:
    normed = _norm(inv_str)
    opts = re.findall(r'"([^"]+)"', normed)
    return opts if len(opts) >= 2 else None


def _time_units(inv_raw) -> list[str]:
    joined = " ".join(str(x) for x in inv_raw) if isinstance(inv_raw, list) else str(inv_raw or "")
    m = re.search(r'\[([^\]]+)\]', joined)
    if m:
        content = m.group(1)
        parts = [x.strip() for x in content.split(",") if x.strip()]
        return parts if len(parts) > 1 else [x.strip() for x in content.split() if x.strip()]
    return ["Seconds", "Minutes", "Hours", "Days", "Years"]


def _range(inv_str: str) -> tuple[float, float] | None:
    m = re.search(r'(\d+(?:\.\d+)?)\s*<=?\s*\w+\s*<=?\s*(\d+(?:\.\d+)?)', inv_str)
    return (float(m.group(1)), float(m.group(2))) if m else None


def _min_gt(inv_str: str) -> float | None:
    m = re.search(r'\w+\s*>[\s=]*(\d+(?:\.\d+)?)', inv_str)
    return float(m.group(1)) if m else None


def smart_input(param: dict, key: str, current: str = "") -> str:
    name  = param["name"]
    dtype = param.get("domainType", "String")
    inv   = param.get("invariants", "")
    inv_s = _norm(" ".join(str(x) for x in inv) if isinstance(inv, list) else str(inv or ""))
    help_text = inv_s if inv_s and inv_s.lower() != "none" else None

    if "TimeUnitTypes" in dtype or "TimeUnitTypes" in inv_s or name == "timeUnit":
        units = _time_units(inv)
        idx = units.index(current) if current in units else 0
        return st.selectbox(name, units, index=idx, key=key)

    opts = _enum_opts(inv_s)
    if opts:
        idx = opts.index(current) if current in opts else 0
        return st.selectbox(name, opts, index=idx, key=key, help=help_text)

    if "Set" in dtype:
        raw = current.strip("{}") if current else ""
        val = st.text_area(f"{name}  *(comma-separated)*", value=raw, key=key, height=72)
        return "{" + val.strip() + "}" if val.strip() else ""

    if dtype in ("Float", "Integer", "Value"):
        rng = _range(inv_s)
        if rng:
            lo, hi = rng
            if dtype in ("Integer", "Value"):
                try:
                    default = int(current)
                except Exception:
                    default = int(lo)
                return str(st.slider(name, int(lo), int(hi), default, key=key))
            else:
                try:
                    default = float(current)
                except Exception:
                    default = lo
                return str(st.slider(name, lo, hi, default, step=0.5, key=key))

        mn = _min_gt(inv_s)
        if mn is not None:
            if dtype == "Integer":
                try:
                    default = int(current)
                except Exception:
                    default = int(mn) + 1
                v = st.number_input(name, min_value=int(mn) + 1, value=default,
                                    step=1, key=key, help=help_text)
            else:
                try:
                    default = float(current)
                except Exception:
                    default = mn + 0.1
                v = st.number_input(name, min_value=float(mn), value=default,
                                    step=0.1, format="%.1f", key=key, help=help_text)
            return str(v)

    return st.text_input(name, value=current or "", key=key, help=help_text)


# ── Statement helpers ──────────────────────────────────────────────────────────

def live_statement_html(template: str, values: dict) -> str:
    """Return HTML with filled values styled blue and empty slots orange."""
    result = template
    for name, val in values.items():
        ph = f"%{name}%"
        v  = str(val).strip() if val is not None else ""
        if v:
            result = result.replace(ph, f'<span class="sp-filled">{v}</span>')
        else:
            result = result.replace(ph, f'<span class="sp-empty">⟨{name}⟩</span>')
    return result


def live_statement(template: str, values: dict) -> str:
    result = template
    for name, val in values.items():
        ph = f"%{name}%"
        v  = str(val).strip() if val is not None else ""
        if v:
            result = result.replace(ph, f"**{v}**")
        else:
            result = result.replace(ph, f":orange[⟨{name}⟩]")
    return result


def show_stmt_preview(template: str, values: dict, label: str = "Statement preview"):
    md = live_statement(template, values)
    st.markdown(f"**{label}**")
    st.markdown(f'<div class="stmt-preview">{md}</div>', unsafe_allow_html=True)


# ── UI helpers ─────────────────────────────────────────────────────────────────

def dim_badge(dimension: str) -> str:
    color = DIM_COLORS.get(dimension, "#6B7280")
    icon  = DIM_ICONS.get(dimension, "•")
    return f'<span class="dim-badge" style="background:{color}">{icon} {dimension}</span>'


def pattern_dims(p: dict) -> list[str]:
    """All dimension names for a pattern (supports both old single-object and new array format)."""
    dims = p.get("qualityDimensions", p.get("qualityDimension"))
    if isinstance(dims, list):
        return [d["dimension"] for d in dims]
    if isinstance(dims, dict) and dims.get("dimension"):
        return [dims["dimension"]]
    return []


def pattern_primary_dim(p: dict) -> str:
    """Primary dimension name (first entry marked primary:true, else first entry)."""
    dims = p.get("qualityDimensions", p.get("qualityDimension"))
    if isinstance(dims, list):
        primary = next((d for d in dims if d.get("primary")), dims[0] if dims else {})
        return primary.get("dimension", "")
    if isinstance(dims, dict):
        return dims.get("dimension", "")
    return ""


def pattern_primary_source(p: dict) -> str:
    """Source reference for the primary dimension."""
    dims = p.get("qualityDimensions", p.get("qualityDimension"))
    if isinstance(dims, list):
        primary = next((d for d in dims if d.get("primary")), dims[0] if dims else {})
        return primary.get("source", "")
    if isinstance(dims, dict):
        return dims.get("source", "")
    return ""


def dim_badges_html(p: dict) -> str:
    """HTML for all dimension badges of a pattern, primary first."""
    return " ".join(dim_badge(d) for d in pattern_dims(p))


def step_bar(steps: list[str], current: int):
    html = '<div class="step-bar">'
    for i, s in enumerate(steps, 1):
        if i < current:
            cls, prefix = "done", "✓ "
        elif i == current:
            cls, prefix = "active", f"{i}. "
        else:
            cls, prefix = "", f"{i}. "
        html += f'<div class="step-item {cls}">{prefix}{s}</div>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def nav(page: str, **kwargs):
    st.session_state.page = page
    for k, v in kwargs.items():
        st.session_state[k] = v
    st.rerun()


def back_btn(label: str, target: str):
    if st.button(f"← {label}"):
        nav(target)


# ── Policy card & ODRL builder ─────────────────────────────────────────────────

def policy_card_html(req: dict) -> str:
    dim    = req.get("qualityDimension", {}).get("dimension", "—")
    color  = DIM_COLORS.get(dim, "#6B7280")
    icon   = DIM_ICONS.get(dim, "•")
    stmt   = req.get("statement", "—")
    source = req.get("sourceEntity", "—")
    sup    = req.get("supportingMaterials", "—")
    pid    = req.get("pattern", {}).get("id", "—")
    rows = "".join(
        f'<div class="pc-row">'
        f'<span class="pc-label">{k}</span>'
        f'<span class="pc-value">{v}</span></div>'
        for k, v in [
            ("Dimension", f'<span style="color:{color};font-weight:600">{icon} {dim}</span>'),
            ("Pattern",   pid),
            ("Raised by", source),
            ("Reference", sup),
        ]
    )
    return (
        f'<div class="policy-card">'
        f'<div class="pc-header">✅ Policy: {req["id"]}</div>'
        f'<p style="font-size:0.93rem;font-style:italic;color:#374151;margin:0 0 0.8rem">{stmt}</p>'
        f'{rows}'
        f'</div>'
    )


def build_odrl_rule(requirement: dict, template: dict) -> dict:
    params    = requirement.get("parameters", {})
    c_tmpl    = template["constraint"]
    attribute = params.get(template["target"]["parameter"])
    req_id    = requirement["id"]
    dim       = requirement["qualityDimension"]["dimension"]
    concept   = requirement.get("measurementConcept", dim)

    if "refinement" in template:
        ref_tmpl = template["refinement"]

        def clean_vs(v):
            return ",".join(s.strip() for s in str(v).strip("{}").split(","))

        refinement_block = {
            "@id": f"ab:{req_id}_Refinement", "@type": "odrl:Constraint",
            "odrl:leftOperand": {"@id": f"ab:{params.get(ref_tmpl['leftOperand']['parameter'])}"},
            "odrl:operator": ref_tmpl["operator"],
            "odrl:rightOperand": {
                "@value": clean_vs(params.get(ref_tmpl["rightOperand"]["parameter"], "")),
                "@type": ref_tmpl["rightOperand"]["type"],
            },
        }
        rm_id = f"{concept}Measurement"
        constraint_block = {
            "@id": f"ab:{req_id}_Constraint", "@type": "odrl:Constraint",
            "odrl:leftOperand": {"@id": f"ab:{rm_id}", "@type": c_tmpl["leftOperand"]["type"]},
            "odrl:operator": c_tmpl["operator"],
            "odrl:rightOperand": {
                "@value": clean_vs(params.get(c_tmpl["rightOperand"]["parameter"], "")),
                "@type": c_tmpl["rightOperand"]["type"],
            },
        }
        graph_nodes = [
            {
                "@id": f"ab:{req_id}Rule", "@type": template["policy"]["type"],
                "rdfs:label": f"ab:{req_id}Rule - QualityPolicy",
                "tb:derivedFrom": req_id, "tb:qualityDimension": dim,
                "tb:sourceEntity": {"@id": f"ab:{requirement['sourceEntity']}"},
                "odrl:permission": [{
                    "@id": f"ab:{req_id}_Permission", "@type": "odrl:Permission",
                    "odrl:action": template["policy"]["action"],
                    "odrl:assigner": {"@id": f"ab:{requirement['sourceEntity']}"},
                    "odrl:assignee": {"@id": f"ab:{template['assignee']['fixed']}"},
                    "odrl:target": {"@id": f"ab:{attribute}"},
                    "odrl:duty": [{
                        "@id": f"ab:{req_id}_Duty", "@type": "odrl:Duty",
                        "odrl:action": {
                            "@id": f"ab:{req_id}_Action", "@type": "odrl:Action",
                            "rdf:value": {"@id": f"ab:Check{dim}"},
                            "odrl:refinement": [refinement_block],
                        },
                        "odrl:constraint": [constraint_block],
                    }],
                }],
            },
            {"@id": f"ab:{rm_id}", "@type": "dqv:Metric",
             "rdfs:label": f"{concept} Measurement",
             "dqv:isMeasurementOf": {"@id": f"ab:Check{concept}"}},
            {"@id": f"ab:{concept}", "@type": "dqv:Metric",
             "rdfs:label": f"{concept} Metric (Abstract)",
             "dqv:inDimension": {"@id": f"ab:{dim}Dimension", "@type": "dqv:Dimension"}},
            {"@id": f"ab:{dim}Dimension", "@type": "dqv:Dimension",
             "rdfs:label": f"{dim} ({requirement['qualityDimension']['source']})"},
            {"@id": f"ab:{attribute}", "@type": "odrl:Asset", "odrl:partOf": {"@id": ""}},
        ]
        return {"@context": template["context"], "@graph": graph_nodes}

    if "operator" in c_tmpl:
        odrl_op = c_tmpl["operator"]
    else:
        op_map  = c_tmpl.get("operatorMapping", {})
        op_sym  = params.get("operator") or params.get("comparisonOperator") or "="
        odrl_op = op_map.get(op_sym, "odrl:eq")

    ro_tmpl = c_tmpl["rightOperand"]
    thr_val = params.get(ro_tmpl["parameter"])
    if ro_tmpl["type"] == "@id":
        safe_id = str(thr_val).replace(" ", "_")
        right_operand = {"@id": f"ab:{safe_id}"}
    else:
        right_operand = {"@value": str(thr_val), "@type": ro_tmpl["type"]}

    m_id = f"{concept}Measurement"
    constraint_block = {
        "@id": f"ab:{req_id}_Constraint", "@type": "odrl:Constraint",
        "odrl:leftOperand": {"@id": f"ab:{m_id}", "@type": c_tmpl["leftOperand"]["type"]},
        "odrl:operator": odrl_op,
        "odrl:rightOperand": right_operand,
    }
    if "unit" in c_tmpl:
        u = c_tmpl["unit"]
        if "fixed" in u:
            constraint_block["odrl:unit"] = {"@id": u["fixed"]}
        elif "mapping" in u:
            tu = params.get(u["parameter"], "")
            constraint_block["odrl:unit"] = {"@id": u["mapping"].get(tu, f"qudt:{tu}")}

    comp_on = template.get("computedOn")
    if comp_on:
        ca = params.get(comp_on["parameter"], "")
        if ca:
            constraint_block["odrl:leftOperand"]["dqv:computedOn"] = {"@id": f"ab:{ca}"}

    graph_nodes = [
        {
            "@id": f"ab:{req_id}Rule", "@type": template["policy"]["type"],
            "rdfs:label": f"ab:{req_id}Rule - QualityPolicy",
            "tb:derivedFrom": req_id, "tb:qualityDimension": dim,
            "tb:sourceEntity": {"@id": f"ab:{requirement['sourceEntity']}"},
            "odrl:permission": [{
                "@id": f"ab:{req_id}_Permission", "@type": "odrl:Permission",
                "odrl:action": template["policy"]["action"],
                "odrl:assigner": {"@id": f"ab:{requirement['sourceEntity']}"},
                "odrl:assignee": {"@id": f"ab:{template['assignee']['fixed']}"},
                "odrl:target": {"@id": f"ab:{attribute}"},
                "odrl:constraint": [constraint_block],
            }],
        },
        {
            "@id": f"ab:{m_id}", "@type": "dqv:Metric",
            "rdfs:label": f"{concept} Measurement",
            "dqv:isMeasurementOf": {"@id": f"ab:Check{concept}"},
            **({"dqv:computedOn": {"@id": f"ab:{params.get(comp_on['parameter'], '')}"}}
               if comp_on and params.get(comp_on.get("parameter", "")) else {}),
        },
        {"@id": f"ab:{concept}", "@type": "dqv:Metric",
         "rdfs:label": f"{concept} Metric (Abstract)",
         "dqv:inDimension": {"@id": f"ab:{dim}Dimension", "@type": "dqv:Dimension"}},
        {"@id": f"ab:{dim}Dimension", "@type": "dqv:Dimension",
         "rdfs:label": f"{dim} ({requirement['qualityDimension']['source']})"},
        {"@id": f"ab:{attribute}", "@type": "odrl:Asset", "odrl:partOf": {"@id": ""}},
    ]
    if ro_tmpl["type"] == "@id" and thr_val:
        safe_id = str(thr_val).replace(" ", "_")
        graph_nodes.append({
            "@id": f"ab:{safe_id}", "@type": "tb:ReferenceStandard",
            "rdfs:label": str(thr_val),
        })
    return {"@context": template["context"], "@graph": graph_nodes}


# ── Coverage widget ────────────────────────────────────────────────────────────

def coverage_widget(reqs: list, patterns: list):
    all_dims   = sorted({d for p in patterns for d in pattern_dims(p)})
    dim_counts = {d: [] for d in all_dims}
    for r in reqs:
        d = r.get("qualityDimension", {}).get("dimension")
        if d in dim_counts:
            dim_counts[d].append(r["id"])

    cols = st.columns(len(all_dims))
    for col, dim in zip(cols, all_dims):
        color = DIM_COLORS.get(dim, "#6B7280")
        icon  = DIM_ICONS.get(dim, "•")
        ids   = dim_counts[dim]
        with col:
            bg = color if ids else "#e5e7eb"
            fg = "white" if ids else "#6B7280"
            st.markdown(
                f'<div class="cov-tile" style="background:{bg};color:{fg}">'
                f'<div style="font-size:1.4rem">{icon}</div>'
                f'<div style="font-weight:700;font-size:0.85rem;margin:0.2rem 0">{dim}</div>'
                f'<div style="font-size:1.3rem;font-weight:800">{len(ids)}</div>'
                f'<div style="font-size:0.7rem">DQR{"s" if len(ids) != 1 else ""}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if not ids:
                if st.button("+ Add", key=f"cov_{dim}", use_container_width=True):
                    _wizard_reset(preset_dim=dim)
                    nav("create_dqr_wizard")


# ── Sidebar ────────────────────────────────────────────────────────────────────

def render_sidebar(wiz_step: int = 0):
    patterns = load_patterns()
    reqs     = load_requirements()
    all_dims = sorted({d for p in patterns for d in pattern_dims(p)}) if patterns else []
    dim_counts = {
        d: sum(1 for r in reqs if r.get("qualityDimension", {}).get("dimension") == d)
        for d in all_dims
    }

    STEPS = [
        ("Quality Dimension", "What concern to address?"),
        ("Rule Pattern",      "Choose the rule structure"),
        ("Define the Rule",   "Fill in the specifics"),
        ("Governance",        "Source & documentation"),
    ]

    with st.sidebar:
        st.markdown(
            '<div class="sb-logo">'
            '<div class="sb-logo-mark">\U0001f6e1</div>'
            '<div>'
            '<div class="sb-logo-text">DQR Catalog</div>'
            '<div class="sb-logo-sub">Policy Builder</div>'
            '</div></div>',
            unsafe_allow_html=True,
        )

        if wiz_step > 0:
            st.markdown('<span class="sb-section-label">New policy — steps</span>',
                        unsafe_allow_html=True)
            items_html = ""
            for i, (sname, shint) in enumerate(STEPS, 1):
                if i < wiz_step:
                    cls, bubble = "done", "✓"
                elif i == wiz_step:
                    cls, bubble = "active", str(i)
                else:
                    cls, bubble = "", str(i)
                connector = '<div class="sb-connector"></div>' if i < len(STEPS) else ""
                items_html += (
                    f'<div class="sb-step {cls}">'
                    f'<div class="sb-bubble">{bubble}</div>'
                    f'<div><div class="sb-step-name">{sname}</div>'
                    f'<div class="sb-step-hint">{shint}</div></div>'
                    f'</div>{connector}'
                )
            st.markdown(items_html, unsafe_allow_html=True)
        else:
            st.markdown('<span class="sb-section-label">Navigation</span>',
                        unsafe_allow_html=True)
            if st.button("\U0001f3e0  Home",              key="sb_home",    use_container_width=True):
                nav("home")
            if st.button("\U0001f4da  Pattern Catalog",   key="sb_catalog",  use_container_width=True):
                nav("catalog")
            if st.button("\U0001f4dd  Requirements",      key="sb_reqs",     use_container_width=True):
                nav("manage_dqr")
            if st.button("⚙️  Generate Policies", key="sb_odrl",  use_container_width=True):
                nav("manage_odrl")
            st.markdown('<span class="sb-section-label" style="margin-top:12px;display:block">Maintainer</span>',
                        unsafe_allow_html=True)
            if st.button("🔧  Define Pattern",    key="sb_maint", use_container_width=True):
                nav("pattern_maintainer")

        # Coverage panel — always
        if all_dims:
            cov_rows = "".join(
                f'<div class="sb-cov-row">'
                f'<div class="sb-cov-pip" style="background:{DIM_COLORS.get(d, "#6B7280")}"></div>'
                f'<div class="sb-cov-name">{d}</div>'
                f'<div class="sb-cov-badge{"  has" if dim_counts.get(d, 0) > 0 else ""}">'
                f'{dim_counts.get(d, 0)}</div>'
                f'</div>'
                for d in all_dims
            )
            st.markdown(
                f'<div class="sb-cov-panel">'
                f'<span class="sb-section-label" style="display:block;margin-bottom:8px">Coverage</span>'
                f'{cov_rows}</div>',
                unsafe_allow_html=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# Pattern Maintainer helpers
# ══════════════════════════════════════════════════════════════════════════════

def _next_pattern_id() -> str:
    nums = []
    for p in load_patterns():
        pid = p.get("id", "")
        if pid.startswith("DQRP"):
            try:
                nums.append(int(pid[4:]))
            except ValueError:
                pass
    return f"DQRP{max(nums) + 1}" if nums else "DQRP7"


_ODRL_OP_MAP = {
    "exactly":     "odrl:eq",
    "at least":    "odrl:gteq",
    "at most":     "odrl:lteq",
    "not exceed":  "odrl:lt",
    "contain":     "odrl:isIncludedIn",
    "not contain": "odrl:isAnyOf",
    "=":           "odrl:eq",
    ">=":          "odrl:gteq",
    "<=":          "odrl:lteq",
}

_ODRL_CTX = {
    "odrl:operator": {"@type": "@id"},
    "@base": "http://www.semanticweb.org/acraf/ontologies/2024/healthmesh/",
    "rdf":  "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "xsd":  "http://www.w3.org/2001/XMLSchema#",
    "odrl": "http://www.w3.org/ns/odrl/2/",
    "dcat": "http://www.w3.org/ns/dcat#",
    "dqv":  "http://www.w3.org/ns/dqv#",
    "tb":   "http://www.semanticweb.org/acraf/ontologies/2024/healthmesh/tbox#",
    "ab":   "http://www.semanticweb.org/acraf/ontologies/2024/healthmesh/abox#",
    "prov": "http://www.w3.org/ns/prov#",
    "qudt": "http://qudt.org/schema/qudt/",
}


def _build_odrl_template(pid: str, ver: str, goal: str,
                          target_param: str, meas_label: str,
                          thresh_param: str, thresh_type: str,
                          operators: list,
                          has_refinement: bool = False,
                          ref_attr: str = "", ref_val: str = "") -> dict:
    op_map = {k: v for k, v in _ODRL_OP_MAP.items() if k in operators}
    rtype  = "xsd:integer" if thresh_type == "xsd:percentage" else thresh_type

    tmpl = {
        "patternId":      pid,
        "patternVersion": ver,
        "description":    f"ODRL template for {goal}",
        "context":        _ODRL_CTX,
        "policy":         {"type": "dqv:QualityPolicy", "action": "odrl:distribute"},
        "target":         {"parameter": target_param},
        "assigner":       {"source": "sourceEntity"},
        "assignee":       {"fixed": "DataProvider"},
        "constraint": {
            "leftOperand":   {"id": meas_label, "type": "dqv:QualityMeasurement"},
            "operatorMapping": op_map,
            "rightOperand":  {"parameter": thresh_param, "type": rtype},
        },
        "dimension":  {"sourceFromDQR": "qualityDimension.dimension"},
        "derivedFrom": {"source": "id"},
    }
    if thresh_type == "xsd:percentage":
        tmpl["constraint"]["unit"] = {"fixed": "qudt:PERCENT"}
    if has_refinement and ref_attr and ref_val:
        tmpl["refinement"] = {
            "leftOperand":  {"parameter": ref_attr},
            "operator":     "odrl:isAnyOf",
            "rightOperand": {"parameter": ref_val, "type": "xsd:string"},
        }
    return tmpl


# ══════════════════════════════════════════════════════════════════════════════
# Pages
# ══════════════════════════════════════════════════════════════════════════════

def page_home():
    st.markdown(
        '<div class="dqr-header">'
        '<h1>DQR Catalog</h1>'
        '<p>Define, manage, and enforce Data Quality Requirements across your data space</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    cards = [
        ("\U0001f4da", "Pattern Catalog",
         "Browse the library of reusable Data Quality Requirement Patterns (DQRPs) "
         "covering Completeness, Currentness, Compliance, Consistency, and Fairness.",
         "catalog"),
        ("\U0001f4dd", "Requirements",
         "Create and manage concrete Data Quality Requirements (DQRs) for your data space. "
         "Each DQR is an instance of a reusable pattern with specific parameter values.",
         "manage_dqr"),
        ("⚙️", "Generate Policies",
         "Convert DQRs into machine-executable ODRL policies and auto-generate "
         "the corresponding validation microservices.",
         "manage_odrl"),
    ]
    cols = st.columns(3)
    for col, (icon, title, desc, page) in zip(cols, cards):
        with col:
            st.markdown(
                f'<div class="tool-card">'
                f'<div class="card-icon">{icon}</div>'
                f'<div class="card-title">{title}</div>'
                f'<div class="card-desc">{desc}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            st.write("")
            if st.button("Open →", key=f"home_{page}", use_container_width=True):
                nav(page)

    reqs     = load_requirements()
    patterns = load_patterns()
    if reqs and patterns:
        st.divider()
        st.markdown("### Coverage at a glance")
        coverage_widget(reqs, patterns)


# ── Catalog ────────────────────────────────────────────────────────────────────

def page_catalog():
    st.markdown('<div class="breadcrumb">Home › <b>Pattern Catalog</b></div>',
                unsafe_allow_html=True)
    st.title("Pattern Catalog")

    patterns = load_patterns()
    if not patterns:
        st.warning("No patterns found in the patterns directory.")
        return

    all_dims = sorted({d for p in patterns for d in pattern_dims(p)})
    sel_dim  = st.radio("Filter by dimension:", ["All"] + all_dims, horizontal=True)
    filtered = patterns if sel_dim == "All" else [
        p for p in patterns if sel_dim in pattern_dims(p)
    ]
    st.caption(f"{len(filtered)} pattern(s) shown")

    for p in filtered:
        pid  = p["id"]
        name = PATTERN_NAMES.get(pid, pid)
        with st.container(border=True):
            c1, c2 = st.columns([3, 2])
            with c1:
                st.markdown(dim_badges_html(p), unsafe_allow_html=True)
                st.markdown(f"### {name}")
                st.caption(f"{pid}  ·  v{p.get('version', '1.0')}")
                st.markdown(f"*{p.get('goal', '')}*")

                if ex := PATTERN_EXAMPLES.get(pid):
                    st.markdown(
                        f'<div class="pcard-example">'
                        f'<div class="pcard-ex-label">Example</div>{ex}</div>',
                        unsafe_allow_html=True,
                    )

                rels = [r for r in p.get("relationships", []) if r.get("type") == "Conflict"]
                if rels:
                    st.markdown(
                        f'<div class="conflict-box">⚠️ <strong>Conflict note:</strong> '
                        f'{rels[0]["description"]}</div>',
                        unsafe_allow_html=True,
                    )

                ca, cb = st.columns(2)
                with ca:
                    if st.button("View details", key=f"cat_view_{pid}"):
                        st.session_state.selected_pattern = p
                        nav("pattern_detail")
                with cb:
                    if st.button("Create DQR →", key=f"cat_create_{pid}", type="primary"):
                        _wizard_reset(preset_pattern=p)
                        nav("create_dqr_wizard")
            with c2:
                show_pattern_image(p)
        st.write("")


def page_pattern_detail():
    back_btn("Back to catalog", "catalog")
    p = st.session_state.get("selected_pattern")
    if not p:
        st.error("No pattern selected.")
        return

    pid  = p["id"]
    name = PATTERN_NAMES.get(pid, pid)

    st.markdown(dim_badges_html(p), unsafe_allow_html=True)
    st.title(name)
    st.caption(f"{pid}  ·  {p.get('goal', '')}")

    dims_detail = "; ".join(
        f"{d['dimension']} ({d['source']})"
        for d in p.get("qualityDimensions", [p.get("qualityDimension", {})])
    )
    c1, c2 = st.columns([3, 2])
    with c1:
        for label, val in [
            ("Description",        p.get("description")),
            ("Quality Dimensions", dims_detail),
            ("Version",            f"v{p.get('version', '1.0')}  ·  {p.get('date', '')}"),
            ("Statement template", p.get("statementTemplate")),
        ]:
            st.markdown(f"**{label}**")
            st.info(val or "—")

        if ex := PATTERN_EXAMPLES.get(pid):
            st.markdown("**Example**")
            st.markdown(
                f'<div class="pcard-example">'
                f'<div class="pcard-ex-label">Example sentence</div>{ex}</div>',
                unsafe_allow_html=True,
            )

        params = p.get("parameters", [])
        if params:
            st.markdown("**Parameters**")
            rows = []
            for par in params:
                inv   = par.get("invariants", "")
                inv_s = _norm(" ".join(str(x) for x in inv) if isinstance(inv, list) else str(inv or "—"))
                rows.append({"Name": par["name"], "Type": par["domainType"], "Invariants": inv_s})
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

        rels = p.get("relationships", [])
        if rels:
            st.markdown("**Relationships**")
            for r in rels:
                box_cls = "conflict-box" if r.get("type") == "Conflict" else "dep-box"
                prefix  = "⚠️ Conflict" if r.get("type") == "Conflict" else f"\U0001f517 {r.get('type','')}"
                st.markdown(
                    f'<div class="{box_cls}"><strong>{prefix}</strong> '
                    f'({r.get("relatedPattern", "?")}): {r.get("description", "")}</div>',
                    unsafe_allow_html=True,
                )

    with c2:
        show_pattern_image(p)
        st.write("")
        if st.button("Create a DQR from this pattern →", type="primary", use_container_width=True):
            _wizard_reset(preset_pattern=p)
            nav("create_dqr_wizard")

    reqs      = load_requirements()
    instances = [r for r in reqs if r.get("pattern", {}).get("id") == pid]
    if instances:
        st.divider()
        st.subheader(f"Existing requirements using {pid}")
        for r in instances:
            with st.expander(f"{r['id']} — {r.get('statement', '')[:90]}…"):
                ci, cb_ = st.columns([3, 1])
                with ci:
                    show_instantiation_image(r)
                with cb_:
                    if st.button(f"View {r['id']}", key=f"inst_view_{r['id']}"):
                        st.session_state.selected_req = r
                        nav("view_dqr")


# ── Manage DQR ────────────────────────────────────────────────────────────────

def page_manage_dqr():
    st.markdown('<div class="breadcrumb">Home › <b>Requirements</b></div>',
                unsafe_allow_html=True)
    st.title("Data Quality Requirements")

    patterns = load_patterns()
    reqs     = load_requirements()

    if patterns:
        st.subheader("Coverage")
        coverage_widget(reqs if reqs else [], patterns)
        st.divider()

    if reqs:
        st.subheader(f"All requirements ({len(reqs)})")
        rows = []
        for r in reqs:
            dim  = r.get("qualityDimension", {}).get("dimension", "—")
            stmt = r.get("statement", "")
            rows.append({
                "ID":        r["id"],
                "Dimension": dim,
                "Statement": stmt[:85] + ("…" if len(stmt) > 85 else ""),
                "Source":    r.get("sourceEntity", "—"),
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    else:
        st.info("No requirements yet. Use **Create DQR** to get started.")

    st.divider()
    st.subheader("Actions")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("➕ Create DQR", use_container_width=True, type="primary"):
            _wizard_reset()
            nav("create_dqr_wizard")
    with c2:
        if st.button("✏️ Update DQR", use_container_width=True):
            nav("update_dqr")
    with c3:
        if st.button("\U0001f441 View DQR", use_container_width=True):
            nav("view_dqr")
    with c4:
        if st.button("\U0001f5d1 Delete DQR", use_container_width=True):
            nav("delete_dqr")


# ── Create DQR Wizard ─────────────────────────────────────────────────────────

def _wizard_reset(preset_pattern: dict | None = None, preset_dim: str | None = None):
    if preset_pattern:
        step = 3
        dim  = pattern_primary_dim(preset_pattern)
    elif preset_dim:
        step = 2
        dim  = preset_dim
    else:
        step = 1
        dim  = ""
    st.session_state.wiz = {
        "step":    step,
        "dim":     dim,
        "pattern": preset_pattern,
        "params":  {},
        "meta":    {},
        "saved":   False,
    }


def page_create_dqr_wizard():
    st.markdown('<div class="breadcrumb">Requirements › <b>New Policy</b></div>',
                unsafe_allow_html=True)

    if "wiz" not in st.session_state or st.session_state.wiz is None:
        _wizard_reset()
    wiz = st.session_state.wiz

    if not wiz.get("saved"):
        step_bar(["Quality Dimension", "Rule Pattern", "Define the Rule", "Governance"],
                 wiz["step"])

    if wiz["step"] == 1:
        _wiz_step1(wiz)
    elif wiz["step"] == 2:
        _wiz_step2(wiz)
    elif wiz["step"] == 3:
        _wiz_step3(wiz)
    elif wiz["step"] == 4:
        _wiz_step4(wiz)


# ── Step 1 — Dimension tiles ───────────────────────────────────────────────────

def _wiz_step1(wiz: dict):
    st.markdown("## What aspect of data quality do you want to enforce?")
    st.markdown(
        '<p style="color:#64748B;font-size:0.95rem;margin-bottom:1.5rem">'
        'Pick a quality dimension. Each one addresses a different kind of concern about your data.'
        '</p>',
        unsafe_allow_html=True,
    )

    patterns   = load_patterns()
    reqs       = load_requirements()
    all_dims   = sorted({d for p in patterns for d in pattern_dims(p)})
    dim_counts = {
        d: sum(1 for r in reqs if r.get("qualityDimension", {}).get("dimension") == d)
        for d in all_dims
    }

    cols = st.columns(len(all_dims))
    for col, dim in zip(cols, all_dims):
        color    = DIM_COLORS.get(dim, "#6B7280")
        icon     = DIM_ICONS.get(dim, "•")
        desc     = DIM_DESCS.get(dim, "")
        count    = dim_counts.get(dim, 0)
        badge_bg = color if count > 0 else "#94A3B8"

        with col:
            st.markdown(
                f'<div class="dim-tile">'
                f'<div class="dim-tile-bar" style="background:{color}"></div>'
                f'<div class="dim-count-badge" style="background:{badge_bg}">{count}</div>'
                f'<div class="dim-tile-icon">{icon}</div>'
                f'<div class="dim-tile-name">{dim}</div>'
                f'<div class="dim-tile-desc">{desc}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button("Choose →", key=f"dim_{dim}",
                         use_container_width=True, type="primary"):
                wiz["dim"]  = dim
                wiz["step"] = 2
                st.rerun()


# ── Step 2 — Pattern cards ────────────────────────────────────────────────────

def _wiz_step2(wiz: dict):
    dim      = wiz.get("dim", "")
    patterns = load_patterns()
    filtered = (
        [p for p in patterns if dim in pattern_dims(p)]
        if dim else patterns
    )

    color = DIM_COLORS.get(dim, "#6B7280")
    icon  = DIM_ICONS.get(dim, "•")

    st.markdown(
        f'<span class="dim-badge" style="background:{color};font-size:0.85rem">{icon} {dim}</span>',
        unsafe_allow_html=True,
    )
    st.markdown("## Choose the type of rule")
    st.markdown(
        '<p style="color:#64748B;font-size:0.95rem;margin-bottom:1.25rem">'
        'Each pattern defines a reusable rule structure. '
        'Pick the one that best describes your intent.'
        '</p>',
        unsafe_allow_html=True,
    )

    for p in filtered:
        pid      = p["id"]
        name     = PATTERN_NAMES.get(pid, pid)
        goal     = p.get("goal", "")
        example  = PATTERN_EXAMPLES.get(pid, "")
        conflicts = [r for r in p.get("relationships", []) if r.get("type") == "Conflict"]
        deps      = [r for r in p.get("relationships", []) if r.get("type") != "Conflict"]

        example_html = (
            f'<div class="pcard-ex-label">Example</div>'
            f'<div class="pcard-example">{example}</div>'
        ) if example else ""

        conflict_html = "".join(
            f'<div class="conflict-box">⚠️ <strong>Conflict:</strong> '
            f'{r.get("description", "")}</div>'
            for r in conflicts
        )
        dep_html = "".join(
            f'<div class="dep-box">\U0001f517 <strong>{r.get("type", "Dependency")}:</strong> '
            f'{r.get("description", "")}</div>'
            for r in deps
        )

        st.markdown(
            f'<div class="pcard">'
            f'<div class="pcard-pid">{pid}</div>'
            f'<div class="pcard-name">{name}</div>'
            f'<div class="pcard-desc">{goal}</div>'
            f'{example_html}{conflict_html}{dep_html}'
            f'</div>',
            unsafe_allow_html=True,
        )

        btn_cols = st.columns([4, 2])
        with btn_cols[1]:
            if st.button("Use this pattern →", key=f"pick_{pid}",
                         type="primary", use_container_width=True):
                wiz["pattern"] = p
                wiz["params"]  = {}
                wiz["step"]    = 3
                st.rerun()
        st.write("")

    if st.button("← Back to dimensions"):
        wiz["step"] = 1
        st.rerun()


# ── Step 3 — Mad Libs builder ─────────────────────────────────────────────────

def _wiz_step3(wiz: dict):
    p = wiz.get("pattern")
    if not p:
        st.error("No pattern selected.")
        if st.button("← Go back"):
            wiz["step"] = 2
            st.rerun()
        return

    dim      = wiz.get("dim") or pattern_primary_dim(p)
    pid      = p["id"]
    color    = DIM_COLORS.get(dim, "#6B7280")
    icon     = DIM_ICONS.get(dim, "•")
    name     = PATTERN_NAMES.get(pid, pid)
    template = p.get("statementTemplate", "")
    params   = p.get("parameters", [])
    current  = wiz.get("params", {})

    col_builder, col_preview = st.columns([3, 2])

    with col_builder:
        st.markdown(
            f'<span class="dim-badge" style="background:{color}">{icon} {dim}</span>',
            unsafe_allow_html=True,
        )
        st.markdown(f"### {name}")

        # Collect param values via smart widgets
        new_vals: dict = {}
        input_cols = st.columns(2) if len(params) > 1 else st.columns(1)
        for i, par in enumerate(params):
            with input_cols[i % len(input_cols)]:
                new_vals[par["name"]] = smart_input(
                    par,
                    key=f"wiz3_{pid}_{par['name']}",
                    current=str(current.get(par["name"], "")),
                )
        wiz["params"] = new_vals

        # Live sentence preview — updates on every widget change
        stmt_html = live_statement_html(template, new_vals)
        st.markdown(
            f'<div class="builder-card">'
            f'<div class="builder-label">Policy sentence</div>'
            f'<div class="sentence-wrap">{stmt_html}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Navigation
        all_filled = all(str(v).strip() not in ("", "{}") for v in new_vals.values())
        bc, nc = st.columns(2)
        with bc:
            if st.button("← Back to patterns"):
                wiz["step"] = 2
                st.rerun()
        with nc:
            if st.button("Next: Governance →", type="primary", disabled=not all_filled):
                wiz["step"] = 4
                st.rerun()
            if not all_filled:
                st.caption("Fill all fields to continue.")

    with col_preview:
        # Live policy box
        all_filled = all(str(v).strip() not in ("", "{}") for v in new_vals.values())
        if all_filled:
            filled_stmt = template
            for pname, val in new_vals.items():
                filled_stmt = filled_stmt.replace(f"%{pname}%", str(val))
            status_icon  = "✅"
            stmt_display = filled_stmt
            stmt_cls     = ""
        else:
            status_icon  = "\U0001f532"
            stmt_display = "Complete the sentence builder to see your policy preview here."
            stmt_cls     = " dim"

        st.markdown(
            f'<div class="policy-box">'
            f'<div class="policy-box-hdr">'
            f'<span>{status_icon}</span><span>Live policy preview</span></div>'
            f'<div class="policy-stmt-text{stmt_cls}">{stmt_display}</div>'
            f'<div class="pm-row"><span class="pm-label">Dimension</span>'
            f'<span class="pm-val" style="color:{color}">{icon} {dim}</span></div>'
            f'<div class="pm-row"><span class="pm-label">Pattern</span>'
            f'<span class="pm-val">{pid} — {name}</span></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Relationships
        for r in p.get("relationships", []):
            box = "conflict-box" if r.get("type") == "Conflict" else "dep-box"
            pfx = "⚠️ Conflict" if r.get("type") == "Conflict" else f"\U0001f517 {r.get('type','')}"
            st.markdown(
                f'<div class="{box}"><strong>{pfx}:</strong> {r.get("description","")}</div>',
                unsafe_allow_html=True,
            )

        # Pattern reference image
        show_pattern_image(p, caption="")


# ── Step 4 — Governance & Save ────────────────────────────────────────────────

def _wiz_step4(wiz: dict):
    # Success state
    if wiz.get("saved"):
        st.markdown(
            f'<div class="success-wrap">'
            f'<div class="success-ring">✅</div>'
            f'<div class="success-h">Policy created successfully!</div>'
            f'<div class="success-p">{wiz.get("saved_stmt", "")}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        ca, cb = st.columns(2)
        with ca:
            if st.button("Create another policy", use_container_width=True):
                _wizard_reset()
                st.rerun()
        with cb:
            if st.button("View all requirements →", use_container_width=True, type="primary"):
                nav("manage_dqr")
        return

    p    = wiz["pattern"]
    vals = wiz["params"]
    meta = wiz.get("meta", {})

    stmt = p.get("statementTemplate", "")
    for pname, val in vals.items():
        stmt = stmt.replace(f"%{pname}%", str(val))

    # Confirmed statement banner
    st.markdown(f'<div class="stmt-confirm">{stmt}</div>', unsafe_allow_html=True)

    col_gov, col_ref = st.columns([3, 2])

    with col_gov:
        st.markdown("### Governance & documentation")
        st.caption("Document where this requirement comes from and who is responsible.")
        st.write("")

        # Auto-suggest ID
        reqs         = load_requirements()
        existing_ids = {r["id"] for r in reqs}
        pid_num      = p["id"].replace("DQRP", "")
        default_id   = meta.get("id", "")
        if not default_id:
            i = 1
            while f"DQR{i}_{pid_num}" in existing_ids:
                i += 1
            default_id = f"DQR{i}_{pid_num}"

        fc1, fc2 = st.columns(2)
        with fc1:
            wiz["meta"]["id"] = st.text_input(
                "Requirement ID",
                value=default_id,
                help="Auto-suggested — edit if needed",
            )
        with fc2:
            source_options = [
                "EHDS Governance Authority",
                "Data Space Governance Authority",
                "Requirement Engineer",
                "Clinical Expert",
                "Legal / Compliance Team",
                "Automated Process",
                "Other",
            ]
            src     = meta.get("sourceEntity", "")
            src_idx = source_options.index(src) if src in source_options else 0
            sel_src = st.selectbox("Raised by", source_options, index=src_idx)
            if sel_src == "Other":
                wiz["meta"]["sourceEntity"] = st.text_input(
                    "Specify source entity",
                    value=meta.get("sourceEntity", "") if src not in source_options else "",
                )
            else:
                wiz["meta"]["sourceEntity"] = sel_src

        wiz["meta"]["supportingMaterials"] = st.text_area(
            "Supporting materials",
            value=meta.get("supportingMaterials", ""),
            placeholder="e.g. EHDS Regulation Art. 12 (https://…), Dataspace Rulebook p.40",
            height=80,
        )
        today_str = date.today().strftime("%d/%m/%Y")
        wiz["meta"]["history"] = st.text_input(
            "History",
            value=meta.get("history", f"Created {today_str}"),
        )

        # Resolve selected dimension entry from pattern list (fallback to ISO/IEC 25012)
        _sel_dim   = wiz.get("dim", pattern_primary_dim(p))
        _dim_entry = next(
            (d for d in p.get("qualityDimensions", []) if d["dimension"] == _sel_dim),
            {"dimension": _sel_dim, "source": "ISO/IEC 25012"},
        )
        # Policy preview card
        dqr_preview = {
            "id":                  wiz["meta"].get("id", "—"),
            "qualityDimension":    _dim_entry,
            "pattern":             {"id": p["id"]},
            "statement":           stmt,
            "sourceEntity":        wiz["meta"].get("sourceEntity", "—"),
            "supportingMaterials": wiz["meta"].get("supportingMaterials", ""),
        }
        st.write("")
        st.markdown(policy_card_html(dqr_preview), unsafe_allow_html=True)

        # ODRL expander — expert only
        tmpl_path = ODRL_TMPL / f"{p['id']}_odrl_template.json"
        if tmpl_path.exists():
            tmpl = load_json(tmpl_path)
            if tmpl:
                with st.expander("View raw ODRL policy (expert / machine-readable)"):
                    try:
                        dqr_full = {**dqr_preview, "parameters": vals}
                        st.json(build_odrl_rule(dqr_full, tmpl))
                    except Exception as e:
                        st.caption(f"Could not render: {e}")

    with col_ref:
        show_pattern_image(p, caption="Pattern reference")

    st.divider()
    bc, sc = st.columns([1, 2])
    with bc:
        if st.button("← Back"):
            wiz["step"] = 3
            st.rerun()
    with sc:
        if st.button("✓ Create Policy", type="primary", use_container_width=True):
            dqr_id = wiz["meta"].get("id", "").strip()
            if not dqr_id:
                st.error("Requirement ID cannot be empty.")
                return
            dqr = {
                "id":                  dqr_id,
                "goal":                p.get("goal", ""),
                "description":         p.get("description", ""),
                "qualityDimension":    _dim_entry,
                "pattern":             {"id": p["id"], "version": p.get("version", "1.0")},
                "parameters":          vals,
                "statement":           stmt,
                "sourceEntity":        wiz["meta"].get("sourceEntity", ""),
                "supportingMaterials": wiz["meta"].get("supportingMaterials", ""),
                "history":             wiz["meta"].get("history", ""),
            }
            path = REQS_DIR / f"{dqr_id}.json"
            if save_json(path, dqr):
                load_requirements.clear()
                _try_regen_media2(dqr)
                wiz["saved"]      = True
                wiz["saved_id"]   = dqr_id
                wiz["saved_stmt"] = stmt
                st.balloons()
                st.rerun()


# ── Update DQR ────────────────────────────────────────────────────────────────

def _select_req(label: str = "Select a requirement") -> dict | None:
    reqs = load_requirements()
    if not reqs:
        st.warning("No requirements available.")
        return None
    ids    = [r["id"] for r in reqs]
    chosen = st.selectbox(label, ids)
    return find_by_id(reqs, chosen)


def page_update_dqr():
    st.markdown('<div class="breadcrumb">Requirements › <b>Update DQR</b></div>',
                unsafe_allow_html=True)
    st.title("Update a Data Quality Requirement")
    back_btn("Back", "manage_dqr")

    req = _select_req()
    if not req:
        return

    patterns = load_patterns()
    pattern  = find_by_id(patterns, req.get("pattern", {}).get("id", ""))

    st.divider()
    c1, c2 = st.columns([3, 2])
    with c1:
        st.subheader("Edit Parameters")
        updated: dict = {}
        if pattern:
            for par in pattern.get("parameters", []):
                updated[par["name"]] = smart_input(
                    par,
                    key=f"upd_{req['id']}_{par['name']}",
                    current=str(req.get("parameters", {}).get(par["name"], "")),
                )
        else:
            for pname, pval in req.get("parameters", {}).items():
                updated[pname] = st.text_input(pname, value=str(pval), key=f"upd_{req['id']}_{pname}")

        if pattern:
            show_stmt_preview(pattern.get("statementTemplate", ""), updated, "Updated statement preview")

        st.divider()
        new_src  = st.text_input("Source Entity", value=req.get("sourceEntity", ""))
        new_mat  = st.text_area("Supporting Materials", value=req.get("supportingMaterials", ""), height=80)
        new_hist = st.text_input("History", value=req.get("history", ""))

        if st.button("\U0001f4be Save changes", type="primary"):
            stmt = (
                pattern.get("statementTemplate", req.get("statement", ""))
                if pattern else req.get("statement", "")
            )
            for k, v in updated.items():
                stmt = stmt.replace(f"%{k}%", str(v))
            req.update({
                "parameters":          updated,
                "statement":           stmt,
                "sourceEntity":        new_src,
                "supportingMaterials": new_mat,
                "history":             new_hist,
            })
            path = REQS_DIR / f"{req['id']}.json"
            if save_json(path, req):
                st.success("✅ Requirement updated.")
                load_requirements.clear()
                _try_regen_media2(req)

    with c2:
        if pattern:
            show_pattern_image(pattern)


# ── View DQR ──────────────────────────────────────────────────────────────────

def page_view_dqr():
    st.markdown('<div class="breadcrumb">Requirements › <b>View DQR</b></div>',
                unsafe_allow_html=True)
    st.title("View Data Quality Requirement")
    back_btn("Back", "manage_dqr")

    pre = st.session_state.pop("selected_req", None)
    req = pre or _select_req()
    if not req:
        return

    dim = req.get("qualityDimension", {}).get("dimension", "")
    st.markdown(dim_badge(dim), unsafe_allow_html=True)
    st.subheader(req["id"])

    c1, c2 = st.columns([3, 2])
    with c1:
        for label, val in [
            ("Goal",              req.get("goal")),
            ("Description",       req.get("description")),
            ("Quality Dimension", f"{dim} ({req.get('qualityDimension',{}).get('source','')})"),
            ("Pattern",           f"{req.get('pattern',{}).get('id','—')} "
                                  f"v{req.get('pattern',{}).get('version','1.0')}"),
        ]:
            st.markdown(f"**{label}**")
            st.info(val or "—")

        st.markdown("**Statement**")
        st.markdown(
            f'<div class="stmt-preview">{req.get("statement", "—")}</div>',
            unsafe_allow_html=True,
        )
        for label, key in [("Raised by", "sourceEntity"),
                            ("Materials", "supportingMaterials"),
                            ("History",   "history")]:
            st.caption(f"**{label}:** {req.get(key) or '—'}")

    with c2:
        inst_img = get_instantiation_image(req)
        if inst_img:
            st.image(str(inst_img), caption=f"{req['id']} card", use_container_width=True)
        else:
            patterns = load_patterns()
            p = find_by_id(patterns, req.get("pattern", {}).get("id", ""))
            if p:
                show_pattern_image(p)


# ── Delete DQR ────────────────────────────────────────────────────────────────

def page_delete_dqr():
    st.markdown('<div class="breadcrumb">Requirements › <b>Delete DQR</b></div>',
                unsafe_allow_html=True)
    st.title("Delete a Data Quality Requirement")
    back_btn("Back", "manage_dqr")

    req = _select_req()
    if not req:
        return

    st.warning(f"You are about to permanently delete **{req['id']}**.")
    st.markdown(f"> {req.get('statement', '')}")

    if st.button("\U0001f5d1 Confirm delete", type="primary"):
        path = REQS_DIR / f"{req['id']}.json"
        try:
            path.unlink()
            st.success(f"✅ {req['id']} deleted.")
            load_requirements.clear()
        except Exception as e:
            st.error(f"Error: {e}")


# ── Manage ODRL ───────────────────────────────────────────────────────────────

def page_manage_odrl():
    st.markdown('<div class="breadcrumb">Home › <b>Generate Policies</b></div>',
                unsafe_allow_html=True)
    st.title("Generate ODRL Policies and Validation Services")
    st.write("Select a Data Quality Requirement to transform into a machine-executable ODRL policy.")

    reqs = load_requirements()
    if not reqs:
        st.warning("No requirements yet. Create a DQR first.")
        if st.button("Create a DQR →"):
            _wizard_reset()
            nav("create_dqr_wizard")
        return

    rows = [
        {
            "ID":        r["id"],
            "Dimension": r.get("qualityDimension", {}).get("dimension", "—"),
            "Statement": r.get("statement", "")[:85] + ("…" if len(r.get("statement", "")) > 85 else ""),
        }
        for r in reqs
    ]
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    ids         = [r["id"] for r in reqs]
    selected_id = st.selectbox("Select a DQR to generate policy for:", ids)

    if st.button("Generate policy →", type="primary"):
        req = find_by_id(reqs, selected_id)
        if req:
            st.session_state.odrl_req = req
            nav("generate_odrl")


# ── Generate ODRL ─────────────────────────────────────────────────────────────

def page_generate_odrl():
    back_btn("Back", "manage_odrl")

    req = st.session_state.get("odrl_req")
    if not req:
        nav("manage_odrl")
        return

    st.title(f"Policy — {req['id']}")

    tmpl_path = ODRL_TMPL / f"{req.get('pattern', {}).get('id', '')}_odrl_template.json"
    if not tmpl_path.exists():
        st.error(f"No ODRL template found for pattern {req.get('pattern', {}).get('id', '')}.")
        return

    tmpl = load_json(tmpl_path)
    if not tmpl:
        return

    c1, c2 = st.columns([3, 2])
    with c1:
        st.subheader("Policy card")
        st.markdown(policy_card_html(req), unsafe_allow_html=True)

        with st.expander("View raw ODRL policy (machine-readable / expert)"):
            try:
                st.json(build_odrl_rule(req, tmpl))
            except Exception as e:
                st.error(f"Could not build ODRL: {e}")

        st.divider()
        col_save, col_gen = st.columns(2)
        with col_save:
            if st.button("\U0001f4be Save ODRL rule", use_container_width=True):
                try:
                    rule = build_odrl_rule(req, tmpl)
                    ODRL_RULES.mkdir(parents=True, exist_ok=True)
                    path = ODRL_RULES / f"{req['id']}_odrl.json"
                    if save_json(path, rule):
                        st.success(f"Saved → {path.name}")
                except Exception as e:
                    st.error(str(e))

        with col_gen:
            if st.button("⚙️ Generate validation service",
                         type="primary", use_container_width=True):
                with st.spinner("Generating validation service…"):
                    try:
                        rule = build_odrl_rule(req, tmpl)
                        ODRL_RULES.mkdir(parents=True, exist_ok=True)
                        local = ODRL_RULES / f"{req['id']}_odrl.json"
                        save_json(local, rule)

                        resp = requests.post(
                            f"{API_URL}/generate-validation-service",
                            json={"rule_id": req["id"], "data_product": "Patient_Summary"},
                            timeout=300,
                        )
                        if resp.status_code == 200:
                            st.session_state["gen_result"] = resp.json()
                            st.session_state["gen_req_id"] = req["id"]
                        else:
                            try:
                                err = resp.json()
                            except Exception:
                                err = {}
                            st.session_state["gen_result"] = {
                                "error": f"API error {resp.status_code}: "
                                         f"{err.get('error', err.get('detail', resp.text))}",
                                "logs": err.get("logs", ""),
                            }
                            st.session_state["gen_req_id"] = req["id"]

                    except requests.ConnectionError:
                        st.session_state["gen_result"] = {
                            "error": f"Cannot reach API at {API_URL}. Is the server running?"}
                        st.session_state["gen_req_id"] = req["id"]
                    except requests.Timeout:
                        st.session_state["gen_result"] = {
                            "error": "Request timed out. The process may still be running."}
                        st.session_state["gen_req_id"] = req["id"]
                    except Exception as e:
                        st.session_state["gen_result"] = {"error": str(e)}
                        st.session_state["gen_req_id"] = req["id"]

    with c2:
        inst_img = get_instantiation_image(req)
        if inst_img:
            st.image(str(inst_img), caption=f"{req['id']} card", use_container_width=True)
        else:
            patterns = load_patterns()
            p = find_by_id(patterns, req.get("pattern", {}).get("id", ""))
            if p:
                show_pattern_image(p)

    # ── Full-width result panel (rendered outside the 2-column layout) ──────────
    gen_result = st.session_state.get("gen_result")
    gen_req_id = st.session_state.get("gen_req_id")
    if gen_result and gen_req_id == req["id"]:
        st.divider()
        if "error" in gen_result:
            st.error(gen_result["error"])
            if gen_result.get("logs"):
                with st.expander("Error logs"):
                    st.text(gen_result["logs"])
        else:
            st.success(gen_result.get("message", "Validation service successfully generated."))

            code = gen_result.get("validation_code", "")
            zip_b64 = gen_result.get("zip_base64")

            # Download button first so it's prominent
            if zip_b64:
                zb  = base64.b64decode(zip_b64)
                zfn = gen_result.get("zip_filename", f"{req['id']}_service.zip")
                st.download_button(
                    "⬇ Download validation service (ZIP)",
                    data=zb, file_name=zfn, mime="application/zip",
                    type="primary",
                )

            if code:
                with st.expander("📄 Generated validation code", expanded=True):
                    st.code(code, language="python")

            if gen_result.get("logs"):
                with st.expander("Execution logs"):
                    st.text(gen_result["logs"])


# ── Pattern Maintainer ────────────────────────────────────────────────────────

def page_pattern_maintainer():
    st.markdown('<div class="breadcrumb">Home › <b>Pattern Maintainer</b></div>',
                unsafe_allow_html=True)
    st.title("Define a New Pattern")
    st.caption(
        "Catalog maintainer role — produces the pattern JSON, ODRL template, and visual card."
    )

    patterns     = load_patterns()
    existing_ids = {p["id"] for p in patterns}
    suggested_id = _next_pattern_id()
    today_str    = date.today().strftime("%d/%m/%Y")

    # ── Dynamic parameter count (must live outside st.form) ───────────────────
    if "maint_n_params" not in st.session_state:
        st.session_state["maint_n_params"] = 3

    ca, cb, _ = st.columns([1, 1, 6])
    if ca.button("＋ parameter", key="maint_add"):
        st.session_state["maint_n_params"] = min(st.session_state["maint_n_params"] + 1, 10)
        st.rerun()
    if cb.button("－ parameter", key="maint_rem"):
        st.session_state["maint_n_params"] = max(st.session_state["maint_n_params"] - 1, 1)
        st.rerun()
    n_params = st.session_state["maint_n_params"]

    with st.form("pattern_maintainer"):
        # 1. Identity
        st.markdown("### 1. Identity")
        c1, c2 = st.columns([3, 1])
        pid  = c1.text_input("Pattern ID *", value=suggested_id,
                              help="Unique identifier, e.g. DQRP7")
        ver  = c2.text_input("Version", value="1.0")
        name = st.text_input("Human-readable name *",
                              placeholder="e.g. Cross-entity Reference Integrity")
        src  = st.text_input("Source entity",
                              placeholder="e.g. EHDS Governance Authority")
        sup  = st.text_input("Supporting materials",
                              placeholder="e.g. Dataspace Rulebook (page 48)")
        st.divider()

        # 2. Description & Template
        st.markdown("### 2. Description & Statement Template")
        goal = st.text_input("Goal *",
                              placeholder="One-line problem statement the pattern addresses")
        desc = st.text_area("Description *",
                             placeholder="One sentence: what values of which attribute must do what",
                             height=70)
        tmpl = st.text_area(
            "Statement template *",
            placeholder="In the %entityName% entity, the %attributeName% attribute must …",
            height=90,
            help="Use %paramName% placeholders — they must match parameter names defined below.",
        )
        placeholders = sorted(set(re.findall(r'%(\w+)%', tmpl)))
        if placeholders:
            st.caption("Detected placeholders: " +
                       "  ·  ".join(f"`{p}`" for p in placeholders))
        st.divider()

        # 3. Parameters
        st.markdown(f"### 3. Parameters  ·  {n_params} slot(s)")
        st.caption("Use the ＋／－ buttons above the form to add or remove rows.")
        PTYPES = ["String", "Float", "Integer", "Set(Value)", "TimeUnitTypes", "Value", "Boolean"]
        param_rows: list[tuple[str, str, str]] = []
        for i in range(n_params):
            c1, c2, c3 = st.columns([2, 2, 3])
            pname = c1.text_input("Name",       key=f"pm_pname_{i}",
                                   placeholder=f"param{i+1}")
            ptype = c2.selectbox("Type", PTYPES, key=f"pm_ptype_{i}")
            pinv  = c3.text_input("Constraint", key=f"pm_pinv_{i}",
                                   placeholder="optional, e.g. value > 0")
            param_rows.append((pname, ptype, pinv))
        param_names = [n for n, _, _ in param_rows if n]
        st.divider()

        # 4. Quality Dimensions
        st.markdown("### 4. Quality Dimensions")
        known_dims  = list(DIM_COLORS.keys())
        sel_dims    = st.multiselect("Dimensions this pattern can serve *",
                                     options=known_dims, default=[known_dims[0]])
        primary_dim = st.selectbox("Primary dimension", options=sel_dims or known_dims)
        dim_src     = st.text_input("Source for primary dimension", value="ISO/IEC 25012")
        st.divider()

        # 5. ODRL Mapping
        st.markdown("### 5. ODRL Mapping")
        st.caption("Maps pattern parameters to the machine-readable policy structure "
                   "consumed by the Connector.")
        opts = param_names if param_names else ["(define parameters above)"]

        odrl_target = st.selectbox(
            "Target attribute parameter *", options=opts,
            help="Which parameter names the attribute/column being checked.")
        meas_label  = st.text_input(
            "Measurement type label *",
            placeholder="e.g. CompletenessMeasurement",
            help="Becomes the ODRL leftOperand id. Convention: {Dimension}Measurement")
        odrl_thresh = st.selectbox(
            "Threshold / value parameter *", options=opts,
            help="Which parameter carries the constraint value or threshold.")
        thresh_type = st.selectbox(
            "Threshold type",
            ["xsd:integer", "xsd:float", "xsd:string", "xsd:percentage"])

        ALL_OPS = ["exactly", "at least", "at most", "not exceed",
                   "contain", "not contain", "=", ">=", "<="]
        sel_ops = st.multiselect("Supported operators", ALL_OPS,
                                  default=["at least", "exactly"])

        has_ref  = st.checkbox("Conditional constraint (refinement)",
                                help="Enable for DQRP4-style patterns where the check applies "
                                     "only when a condition on another attribute holds.")
        ref_attr = ref_val = ""
        if has_ref:
            cr1, cr2 = st.columns(2)
            ref_attr = cr1.selectbox("Condition attribute param", opts, key="pm_ref_attr")
            ref_val  = cr2.selectbox("Condition value param",     opts, key="pm_ref_val")
        st.divider()

        # 6. Relationships
        st.markdown("### 6. Relationships  *(optional)*")
        rel_conflict = st.text_input("Conflict — describe the opposing approach or pattern")
        rel_dep      = st.text_input("Dependency — describe what this pattern relies on")
        st.divider()

        submitted = st.form_submit_button("💾  Save Pattern", type="primary",
                                          use_container_width=True)

    # ── Post-submit (outside form so nav buttons work) ────────────────────────
    if submitted:
        errors = []
        if not pid:         errors.append("Pattern ID is required.")
        if not name:        errors.append("Human-readable name is required.")
        if not goal:        errors.append("Goal is required.")
        if not desc:        errors.append("Description is required.")
        if not tmpl:        errors.append("Statement template is required.")
        if not sel_dims:    errors.append("Select at least one quality dimension.")
        if not meas_label:  errors.append("Measurement type label is required.")
        if not param_names: errors.append("At least one named parameter is required.")
        if pid in existing_ids:
            errors.append(f"Pattern ID '{pid}' already exists — choose a different ID.")

        for e in errors:
            st.error(e)

        if not errors:
            # Build parameter list
            built_params = []
            for pname, ptype, pinv in param_rows:
                if not pname:
                    continue
                entry = {"name": pname, "domainType": ptype}
                if pinv:
                    entry["invariants"] = pinv
                built_params.append(entry)

            # Build qualityDimensions
            quality_dims = []
            for d in sel_dims:
                entry = {
                    "dimension": d,
                    "source": dim_src if d == primary_dim else "ISO/IEC 25012",
                }
                if d == primary_dim:
                    entry["primary"] = True
                quality_dims.append(entry)

            # Build relationships
            rels = []
            if rel_conflict:
                rels.append({"type": "Conflict", "relatedPattern": "?",
                             "description": rel_conflict})
            if rel_dep:
                rels.append({"type": "Dependency", "relatedPattern": "?",
                             "description": rel_dep})

            pattern_json: dict = {
                "id":                  pid,
                "goal":                goal,
                "description":         desc,
                "date":                today_str,
                "version":             ver,
                "qualityDimensions":   quality_dims,
                "statementTemplate":   tmpl,
                "parameters":          built_params,
                "sourceEntity":        src or "Source Entity [...]",
                "supportingMaterials": sup or "Document [...]",
                "history":             f"Created {today_str}",
            }
            if rels:
                pattern_json["relationships"] = rels

            odrl_json = _build_odrl_template(
                pid=pid, ver=ver, goal=goal,
                target_param=odrl_target,
                meas_label=meas_label,
                thresh_param=odrl_thresh,
                thresh_type=thresh_type,
                operators=sel_ops,
                has_refinement=has_ref,
                ref_attr=ref_attr,
                ref_val=ref_val,
            )

            # Write files
            pattern_path = PATTERNS_DIR / f"{pid}.json"
            tmpl_path    = ODRL_TMPL    / f"{pid}_odrl_template.json"
            pattern_path.write_text(json.dumps(pattern_json, indent=2))
            tmpl_path.write_text(json.dumps(odrl_json, indent=2))

            st.success(f"✅ Pattern **{pid} — {name}** saved.")
            ci, cj = st.columns(2)
            ci.info(f"📄 `{pattern_path.name}`")
            cj.info(f"📄 `{tmpl_path.name}`")

            # Card generation
            gen_script = MEDIA2_DIR / "generate_media.py"
            if gen_script.exists():
                with st.spinner("Generating pattern card…"):
                    res = subprocess.run(
                        ["python3", str(gen_script), pid],
                        capture_output=True, text=True, timeout=90,
                        cwd=str(MEDIA2_DIR),
                    )
                card_path = MEDIA2_DIR / pid / f"{pid}-{primary_dim}.png"
                if card_path.exists():
                    st.image(str(card_path),
                             caption=f"{pid} — {name}",
                             use_container_width=True)
                elif res.returncode != 0:
                    st.warning(f"Card generator warnings:\n```\n{res.stderr[:400]}\n```")
                else:
                    st.info("Card generated — image will appear in the catalog.")
            else:
                st.warning("Card generator script not found — run `generate_media.py` manually.")

            st.markdown("---")
            ca2, cb2 = st.columns(2)
            if ca2.button("📚 View in catalog", type="primary", key="maint_to_cat"):
                nav("catalog")
            if cb2.button("➕ Define another pattern", key="maint_another"):
                st.session_state["maint_n_params"] = 3
                st.rerun()


# ── Router ────────────────────────────────────────────────────────────────────

PAGES = {
    "home":               page_home,
    "catalog":            page_catalog,
    "pattern_detail":     page_pattern_detail,
    "manage_dqr":         page_manage_dqr,
    "create_dqr_wizard":  page_create_dqr_wizard,
    "update_dqr":         page_update_dqr,
    "view_dqr":           page_view_dqr,
    "delete_dqr":         page_delete_dqr,
    "manage_odrl":        page_manage_odrl,
    "generate_odrl":      page_generate_odrl,
    "pattern_maintainer": page_pattern_maintainer,
}

if "page" not in st.session_state:
    st.session_state.page = "home"

_page = st.session_state.page
_wiz  = st.session_state.get("wiz")
_wiz_step = (
    _wiz.get("step", 0)
    if (_page == "create_dqr_wizard" and _wiz and not _wiz.get("saved"))
    else 0
)

render_sidebar(_wiz_step)
PAGES.get(_page, page_home)()
