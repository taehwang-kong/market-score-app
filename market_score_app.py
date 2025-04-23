import os
import streamlit as st
import pandas as pd
import numpy as np
import os
import datetime as dt
import plotly.graph_objects as go


history_file = "score_history.csv"

# 파일이 없으면 초기화
if not os.path.exists(history_file):
    pd.DataFrame(columns=["날짜", "점수"]).to_csv(history_file, index=False)


def score_cape(cape: float) -> float:
    min_cape = 10
    max_cape = 45
    score = (cape - min_cape) / (max_cape - min_cape) * 100
    return max(0, min(score, 100))

def score_yield_spread(spread: float) -> float:
    min_spread = -1.5
    max_spread = 3.0
    score = (max_spread - spread) / (max_spread - min_spread) * 100
    return max(0, min(score, 100))

def score_lei(mom_change: float) -> float:
    min_change = -1.0
    max_change = 1.0
    score = (max_change - mom_change) / (max_change - min_change) * 100
    return max(0, min(score, 100))

def score_hy_spread(spread: float) -> float:
    min_spread = 2.0
    max_spread = 20.0
    score = (spread - min_spread) / (max_spread - min_spread) * 100
    return max(0, min(score, 100))

def score_jobless_claims(claims: int) -> float:
    min_claims = 200_000
    max_claims = 700_000
    score = (claims - min_claims) / (max_claims - min_claims) * 100
    return max(0, min(score, 100))

def score_200dma(current_price: float, ma200: float) -> float:
    return 100.0 if current_price < ma200 else 0.0

def score_vix(vix: float) -> float:
    min_vix = 10.0
    max_vix = 80.0
    score = (max_vix - vix) / (max_vix - min_vix) * 100
    return max(0, min(score, 100))

def score_pmi(pmi: float) -> float:
    min_pmi = 35.0
    max_pmi = 65.0
    score = (max_pmi - pmi) / (max_pmi - min_pmi) * 100
    return max(0, min(score, 100))


# 점수 함수들 (이전 코드 그대로 붙여넣기)

def calculate_all_scores(inputs: dict) -> dict:
    return {
        'CAPE 비율': score_cape(inputs['cape']),
        '장단기 금리차': score_yield_spread(inputs['spread']),
        'LEI MoM 변화율': score_lei(inputs['lei_mom']),
        '하이일드 스프레드': score_hy_spread(inputs['hy_spread']),
        '신규 실업수당 청구건수': score_jobless_claims(inputs['claims']),
        'S&P 500 200일선': score_200dma(inputs['current_price'], inputs['ma200']),
        'VIX (공포지수)': score_vix(inputs['vix']),
        'ISM 제조업 PMI': score_pmi(inputs['pmi']),
    }

# 종합 점수 계산
def calculate_market_score(inputs: dict) -> float:
    scores = [
        score_cape(inputs['cape']),
        score_yield_spread(inputs['spread']),
        score_lei(inputs['lei_mom']),
        score_hy_spread(inputs['hy_spread']),
        score_jobless_claims(inputs['claims']),
        score_200dma(inputs['current_price'], inputs['ma200']),
        score_vix(inputs['vix']),
        score_pmi(inputs['pmi'])
    ]
    return round(sum(scores) / len(scores), 2)

# 해석 함수
def interpret_score(score: float) -> str:
    if score >= 70:
        return "🔥 과열 위험 (고점 가능성)"
    elif score <= 30:
        return "📉 저점 근접 (과매도 국면)"
    else:
        return "⚖️ 중립 구간 (명확한 방향 없음)"

# Streamlit 앱 시작
st.title("📊 미국 시장 고점/저점 스코어링 시스템")

st.header("🔢 주요 지표 입력")

# 사용자 입력
inputs = {
    'cape': st.slider("CAPE 비율", 10.0, 45.0, 30.0),
    'spread': st.slider("장단기 금리차 (10Y-3M, %)", -2.0, 3.0, 0.0),
    'lei_mom': st.slider("LEI 전월대비 변화율 (%)", -2.0, 2.0, 0.0),
    'hy_spread': st.slider("하이일드 스프레드 (%)", 2.0, 20.0, 5.0),
    'claims': st.number_input("신규 실업수당 청구건수", 100_000, 800_000, 300_000, step=10_000),
    'current_price': st.number_input("S&P 500 현재 지수", 3000, 5000, 4000),
    'ma200': st.number_input("S&P 500 200일 이동평균선", 3000, 5000, 3900),
    'vix': st.slider("VIX 지수", 10.0, 80.0, 25.0),
    'pmi': st.slider("ISM 제조업 PMI", 35.0, 65.0, 50.0)
}

# 결과 계산
score = calculate_market_score(inputs)

st.subheader("📟 시장 점수 게이지")

fig = go.Figure(go.Indicator(
    mode = "gauge+number+delta",
    value = score,
    domain = {'x': [0, 1], 'y': [0, 1]},
    title = {'text': "시장 위험 점수", 'font': {'size': 20}},
    gauge = {
        'axis': {'range': [0, 100]},
        'bar': {'color': "black"},
        'steps': [
            {'range': [0, 30], 'color': "skyblue"},
            {'range': [30, 70], 'color': "lightgray"},
            {'range': [70, 100], 'color': "tomato"}
        ],
        'threshold': {
            'line': {'color': "red", 'width': 4},
            'thickness': 0.75,
            'value': score
        }
    }
))


st.plotly_chart(fig, use_container_width=True)

# 지표별 점수표
st.subheader("📊 지표별 개별 점수")
individual_scores = calculate_all_scores(inputs)
st.dataframe(individual_scores, height=300)

comment = interpret_score(score)

# 출력
st.header("📈 시장 점수")
st.metric("시장 위험 점수", f"{score} / 100", comment)

st.subheader("📈 지표별 최근 추세 (샘플)")

# 날짜 샘플 (30일)
dates = pd.date_range(end=dt.datetime.today(), periods=30)

# 샘플 지표 데이터 생성 (CAPE, VIX)
cape_data = np.clip(np.random.normal(loc=30, scale=1.5, size=30), 25, 35)
vix_data = np.clip(np.random.normal(loc=20, scale=5.0, size=30), 10, 50)

df = pd.DataFrame({
    "날짜": dates,
    "CAPE 비율": cape_data,
    "VIX 지수": vix_data
}).set_index("날짜")

# Streamlit 라인차트 출력
st.line_chart(df)

st.subheader("🗂 점수 히스토리 저장")
# 기록용
if st.button("📌 오늘 점수 저장하기"):
    today = dt.datetime.today().strftime("%Y-%m-%d")
    new_row = pd.DataFrame({"날짜": [today], "점수": [score]})
    
    history_df = pd.read_csv(history_file, encoding='euc-kr')  # ✅ 여기도!
    history_df = history_df[history_df["날짜"] != today]
    updated_df = pd.concat([history_df, new_row], ignore_index=True)
    updated_df.to_csv(history_file, index=False, encoding='euc-kr')  # ✅ 저장도 맞춰주기

    st.success("✅ 오늘 점수가 저장되었습니다!")

# 그래프용
st.subheader("📊 점수 변화 추이")
if os.path.exists(history_file):
    history_df = pd.read_csv(history_file, encoding='euc-kr')  # ✅ 여기도!
    history_df["날짜"] = pd.to_datetime(history_df["날짜"])
    history_df = history_df.sort_values("날짜")
    
    st.line_chart(history_df.set_index("날짜")["점수"])

