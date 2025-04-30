import os
import streamlit as st
import pandas as pd
import numpy as np
import datetime as dt
import plotly.graph_objects as go
import requests
import yfinance as yf
from bs4 import BeautifulSoup

# ========================
# 데이터 수집 함수
# ========================

history_file = "score_history.csv"

if not os.path.exists(history_file):
    pd.DataFrame(columns=["날짜", "점수"]).to_csv(history_file, index=False)

FRED_API_KEY = "a47556738a5505d18993574740b470c6"

def get_fred_data(series_id, api_key=FRED_API_KEY):
    url = f"https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 1
    }
    response = requests.get(url, params=params)
    data = response.json()
    if "observations" in data and len(data["observations"]) > 0:
        return float(data["observations"][0]["value"])
    return None

def get_latest_fred_values():
    dgs10 = get_fred_data("DGS10")
    dgs3mo = get_fred_data("DGS3MO")
    icsa = get_fred_data("ICSA")
    hy_spread = get_fred_data("BAMLH0A0HYM2")
    spread = dgs10 - dgs3mo if dgs10 and dgs3mo else 0.0
    return {"spread": spread, "claims": icsa, "hy_spread": hy_spread}

def get_latest_yfinance_values():
    sp500 = yf.Ticker("^GSPC")
    sp500_hist = sp500.history(period="1y")
    current_price = sp500_hist["Close"].iloc[-1]
    ma200 = sp500_hist["Close"].rolling(window=200).mean().iloc[-1]
    vix = yf.Ticker("^VIX").history(period="5d")["Close"].iloc[-1]
    return {"current_price": current_price, "ma200": ma200, "vix": vix}

def get_cape_ratio():
    url = "https://www.multpl.com/shiller-pe/"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(r.text, "lxml")
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and "Current Shiller PE Ratio is" in meta.get("content", ""):
        val = meta["content"].split("Current Shiller PE Ratio is")[1].split(",")[0].strip()
        return float(val)
    return None

def get_lead_mom():
    return get_fred_data("USSLIND")

def get_us_manufacturing_ip():
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": "IPMAN",
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 2
    }
    r = requests.get(url, params=params)
    obs = r.json()["observations"]
    latest = float(obs[0]["value"])
    previous = float(obs[1]["value"])
    return round((latest - previous) / previous * 100, 2)

# ========================
# 점수 계산 함수
# ========================

def score_cape(cape): return max(0, min((cape - 10) / (45 - 10) * 100, 100))
def score_yield_spread(spread): return max(0, min((3.0 - spread) / (3.0 + 1.5) * 100, 100))
def score_lei(mom): return max(0, min((1.0 - mom) / 2.0 * 100, 100))
def score_hy_spread(spread): return max(0, min((spread - 2.0) / (20.0 - 2.0) * 100, 100))
def score_jobless_claims(claims): return max(0, min((claims - 200_000) / 500_000 * 100, 100))
def score_200dma(price, ma): return 100.0 if price < ma else 0.0

def score_vix(vix): return max(0, min((80.0 - vix) / (80.0 - 10.0) * 100, 100))
def score_pmi(pmi): return max(0, min((65.0 - pmi) / 30.0 * 100, 100))

def calculate_all_scores(inputs):
    return {
        'CAPE 비율': score_cape(inputs['cape']),
        '장단기 금리차': score_yield_spread(inputs['spread']),
        'LEI MoM 변화율': score_lei(inputs['lei_mom']),
        '하이일드 스프레드': score_hy_spread(inputs['hy_spread']),
        '신규 실업수당 청구건수': score_jobless_claims(inputs['claims']),
        'S&P 500 200일선': score_200dma(inputs['current_price'], inputs['ma200']),
        'VIX (공포지수)': score_vix(inputs['vix']),
        '제조업 지수(PMI 대체)': score_pmi(inputs['pmi'])
    }

def calculate_market_score(inputs):
    scores = list(calculate_all_scores(inputs).values())
    return round(sum(scores) / len(scores), 2)

def interpret_score(score):
    if score >= 70: return "🔥 과열 구간 (매도 타이밍)", "red"
    elif score <= 30: return "📉 저점 구간 (매수 타이밍)", "lightgreen"
    return "⚖️ 중립 구간 (신중한 접근)", "orange"

# ========================
# Streamlit 앱 UI
# ========================

st.set_page_config(layout="wide")
st.title("📊 미국 시장 고점/저점 스코어링 시스템")
st.caption("🔍 이 앱은 미국 주요 경제 및 시장 지표를 기반으로 현재 주식시장의 과열 또는 저점을 진단합니다.")

if st.button("📡 최신 데이터 자동 불러오기 (ALL)"):
    fred_data = get_latest_fred_values()
    yahoo_data = get_latest_yfinance_values()
    cape_val = get_cape_ratio()
    lei_val = get_lead_mom()
    ipman_val = get_us_manufacturing_ip()

    # 자동 불러오기 시 스코어도 즉시 계산
    pmi = ipman_val
    inputs = {
        "cape": cape_val,
        "spread": fred_data.get("spread", 0.0),
        "lei_mom": lei_val,
        "hy_spread": fred_data.get("hy_spread", 0.0),
        "claims": fred_data.get("claims", 220000),
        "current_price": yahoo_data.get("current_price", 4500.0),
        "ma200": yahoo_data.get("ma200", 4400.0),
        "vix": yahoo_data.get("vix", 20.0),
        "pmi": pmi
    }
    score = calculate_market_score(inputs)
    comment, color = interpret_score(score)

    st.session_state.inputs = inputs
    st.session_state.score = score
    st.session_state.comment = comment
    st.session_state.color = color
else:
    fred_data = yahoo_data = {}
    cape_val = lei_val = ipman_val = None

st.subheader("📋 주요 지표 취합 ")
col1, col2 = st.columns(2)

with col1:
    cape = st.number_input("CAPE (Shiller PER)", value=float(cape_val) if cape_val else 30.0)
    spread = st.number_input("장단기 금리차 (10Y-3M, %)", value=fred_data.get("spread", 0.0))
    lei_mom = st.number_input("LEI MoM 변화율 (%)", value=lei_val if lei_val else 0.0)
    claims = st.number_input("신규 실업수당 청구건수", value=fred_data.get("claims", 220000))
    ipman = st.number_input("제조업 생산 증가율 (%)", value=ipman_val if ipman_val else 0.0)

with col2:
    current_price = st.number_input("S&P500 현재 지수", value=yahoo_data.get("current_price", 4500.0))
    ma200 = st.number_input("S&P500 200일 이동평균선", value=yahoo_data.get("ma200", 4400.0))
    vix = st.number_input("VIX 변동성 지수", value=yahoo_data.get("vix", 20.0))
    hy_spread = st.number_input("하이일드 스프레드 (%)", value=fred_data.get("hy_spread", 4.0))

pmi = ipman
inputs = {"cape": cape, "spread": spread, "lei_mom": lei_mom, "hy_spread": hy_spread,
          "claims": claims, "current_price": current_price, "ma200": ma200, "vix": vix, "pmi": pmi}

score = st.session_state.get("score") or calculate_market_score(inputs)
comment, color = interpret_score(score)

st.subheader("📈 시장 분석 ")
fig = go.Figure(go.Indicator(
    mode="gauge+number",
    value=score,
    domain={'x': [0, 1], 'y': [0, 1]},
    title={'text': "🔄 Market Cycle Score", 'font': {'size': 20}},
    gauge={
        'axis': {'range': [0, 100]},
        'bar': {'color': "black"},
        'steps': [
            {'range': [0, 30], 'color': "skyblue"},
            {'range': [30, 70], 'color': "lightgray"},
            {'range': [70, 100], 'color': "tomato"}
        ],
        'threshold': {'line': {'color': "red", 'width': 4}, 'value': score}
    }
))
st.plotly_chart(fig, use_container_width=True, key="market_gauge_chart")

st.markdown(
    f"""
    <div style='text-align: center; margin-top: -40px;'>
        <h2 style='font-size: 60px; color: cyan;'>{score:.2f} / 100</h2>
        <h3 style='font-size: 30px; color: {color};'>{comment}</h3>
    </div>
    """,
    unsafe_allow_html=True
)

if st.button("📌 오늘 점수 저장하기"):
    today = dt.datetime.today().strftime("%Y-%m-%d")
    new_row = pd.DataFrame({"날짜": [today], "점수": [score]})
    history_df = pd.read_csv(history_file, encoding='euc-kr')
    history_df = history_df[history_df["날짜"] != today]
    pd.concat([history_df, new_row], ignore_index=True).to_csv(history_file, index=False, encoding='utf-8')
    st.success("✅ 오늘 점수가 저장되었습니다!")

if os.path.exists(history_file):
    history_df = pd.read_csv(history_file, encoding='utf-8')
    history_df["날짜"] = pd.to_datetime(history_df["날짜"])
    history_df = history_df.sort_values("날짜")
    st.subheader("📈 점수 변화 추이 (최근)")
    st.line_chart(history_df.set_index("날짜")["점수"])
