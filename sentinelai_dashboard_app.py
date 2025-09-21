import json
from pathlib import Path
from datetime import datetime
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="SentinelAI — SOC Dashboard", layout="wide")
st.title("SentinelAI — Banking SOC Assistant")

# --- Load incidents ---
INC_PATH = Path("incidents.jsonl")  # relative when running from same folder
if not INC_PATH.exists():
    # fallback: look in working dir used by this environment
    INC_PATH = Path("/mnt/data/incidents.jsonl")

incidents = []
if INC_PATH.exists():
    with open(INC_PATH) as f:
        for line in f:
            try:
                inc = json.loads(line)
                incidents.append(inc)
            except:
                pass

if not incidents:
    st.info("No incidents found yet. Add incidents.jsonl to see data.")
    st.stop()

# --- Sidebar Filters ---
with st.sidebar:
    st.header("Filters")
    # Risk filter
    risks = [inc.get("risk", 0) for inc in incidents]
    rmin, rmax = (min(risks), max(risks)) if risks else (0.0, 10.0)
    risk_range = st.slider("Risk score range", 0.0, 10.0, (float(rmin), float(rmax)))
    # Modules filter
    all_modules = sorted({a["module"] for inc in incidents for a in inc.get("alerts", [])})
    selected_modules = st.multiselect("Modules must include", all_modules, default=[])
    # Date filter
    def to_dt(x):
        try:
            return datetime.fromisoformat(x.replace("Z","+00:00"))
        except Exception:
            return None
    created_times = [to_dt(inc.get("created_at","")) for inc in incidents]
    created_times = [t for t in created_times if t]
    if created_times:
        start_default = min(created_times).date()
        end_default = max(created_times).date()
    else:
        start_default = end_default = datetime.utcnow().date()
    date_from = st.date_input("From", start_default)
    date_to = st.date_input("To", end_default)

# --- Apply filters ---
def passes_filters(inc):
    risk = inc.get("risk", 0.0)
    if not (risk_range[0] <= risk <= risk_range[1]):
        return False
    # date
    t = to_dt(inc.get("created_at",""))
    if t is not None and t.tzinfo:   # make naive (remove timezone)
        t = t.replace(tzinfo=None)
    if t is None or not (datetime.combine(date_from, datetime.min.time()) <= t <= datetime.combine(date_to, datetime.max.time())):
        return False
    # modules
    if selected_modules:
        mods = {a["module"] for a in inc.get("alerts", [])}
        if not set(selected_modules).issubset(mods):
            return False
    return True

filtered = [inc for inc in incidents if passes_filters(inc)]

# --- Summary Cards ---
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Total Incidents", len(filtered))
with c2:
    high = sum(1 for inc in filtered if inc.get("risk",0)>=7.0)
    st.metric("High/Critical", high)
with c3:
    avg = round(sum(inc.get("risk",0) for inc in filtered)/len(filtered), 2) if filtered else 0.0
    st.metric("Avg Risk", avg)
with c4:
    st.metric("Modules Active", f"{len(all_modules)}/{len(all_modules)}")

st.divider()

# --- Incidents Table ---
table_rows = []
for inc in filtered:
    mods = ", ".join(sorted({a["module"] for a in inc.get("alerts", [])}))
    entity = None
    if inc.get("alerts"):
        entity = inc["alerts"][0].get("entity")
    table_rows.append({
        "Time (UTC)": inc.get("created_at",""),
        "Incident ID": inc.get("id",""),
        "Entity": entity or "",
        "Modules": mods,
        "Risk": inc.get("risk",0),
        "Status": "Open"  # demo placeholder
    })
df = pd.DataFrame(table_rows)
st.subheader("Incidents")
st.dataframe(df, use_container_width=True)

# --- Drilldown ---
st.subheader("Drilldown")
selected_id = st.selectbox("Select Incident ID", options=[r["Incident ID"] for r in table_rows] if table_rows else [])
if selected_id:
    inc = next((x for x in filtered if x.get("id")==selected_id), None)
    if inc:
        st.markdown(f"**Incident {inc.get('id')} — Risk {inc.get('risk')}**")
        # Timeline
        st.markdown("**Timeline**")
        for a in sorted(inc.get("alerts", []), key=lambda x: x.get("timestamp","")):
            st.write(f"- [{a.get('timestamp','')}] [{a.get('module','')}] {a.get('severity','')} — {a.get('summary','')}")

# --- Charts ---
st.subheader("Charts")

# Risk histogram
fig1 = plt.figure()
plt.hist([inc.get("risk",0) for inc in filtered])
plt.title("Risk Score Distribution")
plt.xlabel("Risk Score")
plt.ylabel("Count")
st.pyplot(fig1)

# Alerts per module
mod_list = [a["module"] for inc in filtered for a in inc.get("alerts", [])]
if mod_list:
    import collections
    counts = collections.Counter(mod_list)
    labels = list(counts.keys())
    sizes = list(counts.values())
    fig2 = plt.figure()
    plt.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=140)
    plt.title("Alerts per Module")
    st.pyplot(fig2)
else:
    st.info("No alerts to chart.")
