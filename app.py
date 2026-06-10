"""
국내 주식 대시보드
- yfinance로 국내 주식 10개 데이터를 수집
- Streamlit 기반 웹 대시보드
실행: streamlit run app.py
"""

import datetime as dt

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

# ----------------------------------------------------------------------------
# 기본 설정
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="국내 주식 대시보드",
    page_icon="📈",
    layout="wide",
)

# 국내 주식 10개 (yfinance 티커: KOSPI=.KS, KOSDAQ=.KQ)
STOCKS = {
    "삼성전자": "005930.KS",
    "SK하이닉스": "000660.KS",
    "LG에너지솔루션": "373220.KS",
    "삼성바이오로직스": "207940.KS",
    "현대차": "005380.KS",
    "기아": "000270.KS",
    "NAVER": "035420.KS",
    "카카오": "035720.KS",
    "셀트리온": "068270.KS",
    "에코프로비엠": "247540.KQ",
}


# ----------------------------------------------------------------------------
# 데이터 수집 (캐시 적용)
# ----------------------------------------------------------------------------
@st.cache_data(ttl=60 * 30)  # 30분 캐시
def load_history(ticker: str, period: str) -> pd.DataFrame:
    """단일 종목의 과거 시세를 가져온다."""
    df = yf.Ticker(ticker).history(period=period, auto_adjust=False)
    return df


@st.cache_data(ttl=60 * 30)
def load_summary() -> pd.DataFrame:
    """전 종목의 최신 시세 요약 테이블을 만든다."""
    rows = []
    for name, ticker in STOCKS.items():
        hist = yf.Ticker(ticker).history(period="5d", auto_adjust=False)
        if hist.empty or len(hist) < 2:
            rows.append(
                {
                    "종목": name,
                    "티커": ticker,
                    "현재가": None,
                    "전일대비": None,
                    "등락률(%)": None,
                    "거래량": None,
                }
            )
            continue

        last = hist["Close"].iloc[-1]
        prev = hist["Close"].iloc[-2]
        change = last - prev
        pct = (change / prev) * 100 if prev else 0.0
        rows.append(
            {
                "종목": name,
                "티커": ticker,
                "현재가": round(last, 1),
                "전일대비": round(change, 1),
                "등락률(%)": round(pct, 2),
                "거래량": int(hist["Volume"].iloc[-1]),
            }
        )
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------
# 사이드바
# ----------------------------------------------------------------------------
st.sidebar.title("⚙️ 설정")
selected_name = st.sidebar.selectbox("종목 선택", list(STOCKS.keys()))
selected_ticker = STOCKS[selected_name]

period = st.sidebar.select_slider(
    "조회 기간",
    options=["1mo", "3mo", "6mo", "1y", "2y", "5y"],
    value="6mo",
)

chart_type = st.sidebar.radio("차트 유형", ["캔들스틱", "라인"], horizontal=True)
show_ma = st.sidebar.checkbox("이동평균선(20/60일) 표시", value=True)

if st.sidebar.button("🔄 데이터 새로고침"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.caption("데이터 출처: Yahoo Finance (yfinance)")


# ----------------------------------------------------------------------------
# 헤더
# ----------------------------------------------------------------------------
st.title("📈 국내 주식 대시보드")
st.caption(f"갱신 시각: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ----------------------------------------------------------------------------
# 전체 종목 요약
# ----------------------------------------------------------------------------
st.subheader("📊 전체 종목 요약")

with st.spinner("시세를 불러오는 중..."):
    summary = load_summary()

# 등락률 상위/하위 metric
valid = summary.dropna(subset=["등락률(%)"])
if not valid.empty:
    top = valid.loc[valid["등락률(%)"].idxmax()]
    bottom = valid.loc[valid["등락률(%)"].idxmin()]
    c1, c2, c3 = st.columns(3)
    c1.metric("📈 상승률 1위", top["종목"], f"{top['등락률(%)']:+.2f}%")
    c2.metric("📉 하락률 1위", bottom["종목"], f"{bottom['등락률(%)']:+.2f}%")
    c3.metric("종목 수", f"{len(summary)} 개")

st.dataframe(
    summary.style.format(
        {
            "현재가": "{:,.0f}",
            "전일대비": "{:+,.0f}",
            "등락률(%)": "{:+.2f}",
            "거래량": "{:,.0f}",
        },
        na_rep="-",
    ).map(
        lambda v: "color: red;" if isinstance(v, (int, float)) and v > 0
        else ("color: blue;" if isinstance(v, (int, float)) and v < 0 else ""),
        subset=["전일대비", "등락률(%)"],
    ),
    use_container_width=True,
    hide_index=True,
)

st.divider()

# ----------------------------------------------------------------------------
# 개별 종목 상세
# ----------------------------------------------------------------------------
st.subheader(f"🔍 {selected_name} ({selected_ticker}) 상세")

with st.spinner("차트 데이터를 불러오는 중..."):
    hist = load_history(selected_ticker, period)

if hist.empty:
    st.error("데이터를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.")
    st.stop()

# 주요 지표
last = hist["Close"].iloc[-1]
prev = hist["Close"].iloc[-2] if len(hist) > 1 else last
change = last - prev
pct = (change / prev) * 100 if prev else 0.0

m1, m2, m3, m4 = st.columns(4)
m1.metric("현재가", f"{last:,.0f} 원", f"{change:+,.0f} ({pct:+.2f}%)")
m2.metric("기간 최고", f"{hist['High'].max():,.0f} 원")
m3.metric("기간 최저", f"{hist['Low'].min():,.0f} 원")
m4.metric("평균 거래량", f"{hist['Volume'].mean():,.0f}")

# 차트
fig = go.Figure()

if chart_type == "캔들스틱":
    fig.add_trace(
        go.Candlestick(
            x=hist.index,
            open=hist["Open"],
            high=hist["High"],
            low=hist["Low"],
            close=hist["Close"],
            name="가격",
            increasing_line_color="red",
            decreasing_line_color="blue",
        )
    )
else:
    fig.add_trace(
        go.Scatter(x=hist.index, y=hist["Close"], mode="lines", name="종가")
    )

if show_ma:
    fig.add_trace(
        go.Scatter(
            x=hist.index,
            y=hist["Close"].rolling(20).mean(),
            mode="lines",
            name="20일 이동평균",
            line=dict(width=1),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=hist.index,
            y=hist["Close"].rolling(60).mean(),
            mode="lines",
            name="60일 이동평균",
            line=dict(width=1),
        )
    )

fig.update_layout(
    height=500,
    xaxis_rangeslider_visible=False,
    margin=dict(l=10, r=10, t=30, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)
st.plotly_chart(fig, use_container_width=True)

# 거래량 차트
vol_fig = go.Figure()
vol_fig.add_trace(go.Bar(x=hist.index, y=hist["Volume"], name="거래량"))
vol_fig.update_layout(
    height=200,
    margin=dict(l=10, r=10, t=10, b=10),
    title="거래량",
)
st.plotly_chart(vol_fig, use_container_width=True)

# 원본 데이터
with st.expander("📄 원본 데이터 보기 / 다운로드"):
    show_df = hist[["Open", "High", "Low", "Close", "Volume"]].copy()
    show_df.index = show_df.index.strftime("%Y-%m-%d")
    st.dataframe(show_df, use_container_width=True)
    st.download_button(
        "CSV 다운로드",
        data=show_df.to_csv().encode("utf-8-sig"),
        file_name=f"{selected_name}_{period}.csv",
        mime="text/csv",
    )
