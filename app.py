import streamlit as st, requests, json, time, re, os, random
from collections import Counter
from datetime import datetime

st.set_page_config(page_title="Alpha Bot", layout="wide")
st.title("Alpha Researcher Bot")
st.caption("Inspect first. Research first. Simulate safely for 10 hours.")

try:
    with open("knowledge.md") as f: KNOWLEDGE = f.read()
except: KNOWLEDGE = "Use group_neutralize, decay 3-10, avoid ts_corr repetition"

for k, v in [("history", []), ("banned", set()), ("running", False), ("results", []), ("last_family", ""), ("last_fields", []), ("top_ops", []), ("top_fields", []), ("rare_fields", ["sentiment", "analyst_rating", "sales"]), ("research_note", "")]:
    if k not in st.session_state: st.session_state[k] = v

st.sidebar.header("Login")
email = st.sidebar.text_input("BRAIN Email")
password = st.sidebar.text_input("BRAIN Password", type="password")
openai_key = st.sidebar.text_input("OpenAI API Key", type="password")
region = st.sidebar.selectbox("Region", ["USA", "EUR", "ASI", "CHN"])
target = st.sidebar.slider("How many to simulate?", 10, 100, 50)
st.sidebar.info("Safe speed: 1 sim per 6 min equals 100 in 10 hours. No limit hit.")

class Brain:
    def __init__(self, email, password):
        self.s = requests.Session()
        self.base = "https://api.worldquantbrain.com"
        r = self.s.post(f"{self.base}/authentication", auth=(email, password))
        if r.status_code != 201: raise Exception("Login failed")
    def get_alphas(self, limit=300):
        out, offset = [], 0
        while len(out) < limit:
            r = self.s.get(f"{self.base}/users/self/alphas?limit=100&offset={offset}&status=SUBMITTED")
            if r.status_code != 200: break
            data = r.json().get("results", [])
            if not data: break
            out.extend(data); offset += 100
        return out[:limit]
    def simulate(self, d): return self.s.post(f"{self.base}/simulations", json=d).json()
    def get_sim(self, sid): return self.s.get(f"{self.base}/simulations/{sid}").json()
    def get_corr(self, aid):
        r = self.s.get(f"{self.base}/alphas/{aid}/correlations?limit=5")
        return r.json().get("results", []) if r.status_code == 200 else []

def fingerprint(expr):
    ops = re.findall(r"(ts_\w+|group_\w+|rank|delay|decay_linear|zscore)", expr)
    fields = re.findall(r"(close|open|high|low|volume|vwap|returns|sentiment|news_sentiment|analyst_rating|analyst_revision|sales|pe_ratio|book_value|roa|cash_flow)", expr)
    windows = re.findall(r",\s*(\d+)\)", expr)
    return tuple(sorted(set(ops))), tuple(sorted(set(fields))), tuple(sorted(set(windows)))

def similarity(a, b):
    x = set(sum([list(fingerprint(a)[i]) for i in range(3)], []))
    y = set(sum([list(fingerprint(b)[i]) for i in range(3)], []))
    return len(x & y) / len(x | y) if x and y else 0

def ask_llm(prompt):
    headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
    r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}], "max_tokens": 900, "temperature": 0.7})
    return r.json()["choices"][0]["message"]["content"]

FAMILIES = {
    "Sentiment": ["sentiment", "news_sentiment", "analyst_rating", "analyst_revision"],
    "Fundamental": ["sales", "roa", "book_value", "pe_ratio", "cash_flow"],
    "Volatility": ["returns"],
    "Volume": ["vwap", "volume"],
    "Mean Reversion": ["close", "returns"],
    "Momentum": ["close", "returns"],
}

tab1, tab2, tab3, tab4 = st.tabs(["1. Inspect", "2. Research", "3. Run 10H Bot", "4. Results"])

with tab1:
    st.subheader("Inspect your submitted alphas")
    st.write("This is the most important step. The bot learns what NOT to repeat.")
    if st.button("Pull My 300 Alphas"):
        b = Brain(email, password)
        alphas = b.get_alphas(300)
        st.session_state.history = alphas
        st.success(f"Pulled {len(alphas)} alphas")
        ops, fields, windows = Counter(), Counter(), Counter()
        for a in alphas:
            expr = a.get("regular", {}).get("code", "")
            o, f, w = fingerprint(expr)
            ops.update(o); fields.update(f); windows.update(w)
        c1, c2, c3 = st.columns(3)
        with c1:
            st.write("**Top Operators You Overuse**")
            for k, v in ops.most_common(10): st.write(f"{k}: {v}")
        with c2:
            st.write("**Top Fields You Overuse**")
            for k, v in fields.most_common(10): st.write(f"{k}: {v}")
        with c3:
            st.write("**Top Windows You Overuse**")
            for k, v in windows.most_common(10): st.write(f"{k}: {v}")
        st.session_state.top_ops = [x[0] for x in ops.most_common(3)]
        st.session_state.top_fields = [x[0] for x in fields.most_common(2)]
        st.session_state.rare_fields = [x[0] for x in fields.most_common()[-5:]] or ["sentiment", "sales", "analyst_rating"]
        st.warning(f"Bot will now AVOID: {st.session_state.top_ops} plus {st.session_state.top_fields}")
        st.success(f"Bot will now USE MORE: {st.session_state.rare_fields}")

with tab2:
    st.subheader("Research before writing")
    idea = st.text_area("What inefficiency do you want to exploit?", placeholder="Example: Analyst revisions lead price, but market underreacts in small caps")
    if st.button("Generate Research Note"):
        prompt = f"""You are a WorldQuant BRAIN researcher with deep understanding of alphas.
        Knowledge: {KNOWLEDGE}
        User overuses: {st.session_state.top_ops} and {st.session_state.top_fields}
        Rare fields to use: {st.session_state.rare_fields}
        Idea: {idea}
        Write 300 words: 1. Hypothesis 2. Economic reason it should work 3. Why it is orthogonal to price momentum 4. Data family NOT price 5. Neutralization plan 6. Decay plan for low turnover 7. 3 alpha templates with different operators, avoid ts_corr, use group_neutralize.
        Return only the research note."""
        note = ask_llm(prompt)
        st.session_state.research_note = note
        st.write(note)

with tab3:
    st.subheader("Run bot safely for 10 hours")
    col1, col2 = st.columns(2)
    if col1.button("Start Bot"): st.session_state.running = True
    if col2.button("Stop Bot"): st.session_state.running = False
    if st.session_state.running:
        b = Brain(email, password)
        progress = st.progress(0); status = st.empty()
        done = 0
        if os.path.exists("checkpoint.json"):
            with open("checkpoint.json") as f: done = len(json.load(f))
            st.write(f"Resumed: {done} already done, will not repeat")
        for i in range(done, target):
            if not st.session_state.running: break
            families = list(FAMILIES.keys())
            fam = random.choice([x for x in families if x != st.session_state.last_family] or families)
            st.session_state.last_family = fam
            field = random.choice(FAMILIES[fam] + st.session_state.rare_fields)
            if field in st.session_state.last_fields[-2:]:
                field = random.choice(st.session_state.rare_fields)
            st.session_state.last_fields.append(field)
            history_sample = "\n".join([h.get("regular", {}).get("code", "") for h in st.session_state.history[-10:]])
            gen_prompt = f"""Knowledge: {KNOWLEDGE}
            Research note: {st.session_state.research_note}
            Family for this run: {fam}. Must use field: {field}.
            Avoid operators: {st.session_state.top_ops}. Avoid fields: {st.session_state.top_fields}.
            Banned fingerprints: {list(st.session_state.banned)[:5]}
            Your last 10 alphas (DO NOT REPEAT THEM):
            {history_sample}
            Write ONE WorldQuant BRAIN REGULAR alpha expression only. No explanation. No markdown. Must start with group_neutralize or group_rank. Decay 3 to 8. Use sector neutralization. Use a different operator and window than your last alphas."""
            expr = ask_llm(gen_prompt).strip().replace("```", "").replace("python", "").strip()
            expr = " ".join(expr.splitlines()).strip()
            if str(fingerprint(expr)) in st.session_state.banned:
                status.write(f"Skipped, banned fingerprint: {expr}"); continue
            max_sim = max([similarity(expr, h.get("regular", {}).get("code", "")) for h in st.session_state.history[-50:]] or [0])
            if max_sim > 0.60:
                status.write(f"Skipped, too similar {max_sim:.2f}: {expr}"); continue
            status.write(f"Sim {i+1}/{target} Family {fam} - {expr} - Local sim: {max_sim:.2f}")
            d = random.choice([3, 5, 8])
            alpha = {"type": "REGULAR", "settings": {"instrumentType": "EQUITY", "region": region, "universe": "TOP3000", "delay": 1, "decay": d, "neutralization": "SECTOR", "truncation": 0.08, "pasteurization": "ON", "unitHandling": "VERIFY", "nanHandling": "ON", "maxTrade": "ON", "commission": "ON", "visualization": False}, "regular": expr}
            sim = b.simulate(alpha); sim_id = sim.get("id")
            for _ in range(30):
                prog = b.get_sim(sim_id)
                if prog.get("status") == "COMPLETE": break
                time.sleep(10)
            res = b.get_sim(sim_id)
            sharpe = res.get("is", {}).get("sharpe", 0) if res.get("is") else 0
            max_corr = 0
            if res.get("alpha"):
                corrs = b.get_corr(res.get("alpha"))
                if corrs: max_corr = max([c.get("correlation", 0) for c in corrs])
            if max_corr > 0.70:
                st.session_state.banned.add(str(fingerprint(expr)))
                status.write(f"Rejected, BRAIN corr {max_corr:.2f} too high, banned this fingerprint")
            else:
                saved = []
                if os.path.exists("checkpoint.json"):
                    with open("checkpoint.json") as f: saved = json.load(f)
                saved.append({"expr": expr, "family": fam, "sharpe": sharpe, "corr": max_corr, "sim": max_sim, "time": str(datetime.now())})
                with open("checkpoint.json", "w") as f: json.dump(saved, f, indent=2)
                st.session_state.results = saved
                status.write(f"Saved: Sharpe {sharpe:.2f} Corr {max_corr:.2f} | {expr}")
            progress.progress((i+1)/target)
            for sec in range(360):
                if not st.session_state.running: break
                status.write(f"Cooling down {360-sec}s before next sim to avoid limit...")
                time.sleep(1)
        st.success("Bot finished or stopped. Check Results tab.")

with tab4:
    st.subheader("Saved Results")
    if os.path.exists("checkpoint.json"):
        with open("checkpoint.json") as f: data = json.load(f)
        st.dataframe(data)
        st.download_button("Download JSON", data=json.dumps(data), file_name="alphas.json")
    else:
        st.write("No results yet. Run the bot first.")