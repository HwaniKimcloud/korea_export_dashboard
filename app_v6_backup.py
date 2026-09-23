from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# ============================================================
# 0. PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Korea Export Monitor",
    page_icon="KR",
    layout="wide",
)


# ============================================================
# 1. PATH
# ============================================================

BASE_DIR = Path(__file__).resolve().parent


FILES = {
    "total": BASE_DIR / "korea_total_export_monthly.csv",

    "industry_monthly": BASE_DIR / "industry20_monthly.csv",
    "industry_latest": BASE_DIR / "industry20_latest.csv",
    "industry_ytd": BASE_DIR / "industry20_ytd.csv",

    "industry_qc_summary": BASE_DIR / "industry20_final_qc_summary.csv",
    "industry_qc_industry": BASE_DIR / "industry20_final_qc_industry.csv",

    "country_monthly": BASE_DIR / "country_monthly.csv",
    "country_latest": BASE_DIR / "country_latest.csv",
    "country_ytd": BASE_DIR / "country_ytd.csv",

    "product_country_monthly": BASE_DIR / "product_country_multi_monthly.csv",
    "product_country_latest": BASE_DIR / "product_country_multi_latest.csv",
    "product_country_ytd": BASE_DIR / "product_country_multi_ytd.csv",

    "product_master": BASE_DIR / "product_master.csv",
}


# ============================================================
# 2. CSS
# ============================================================

st.markdown(
    """
    <style>

    .block-container {
        padding-top: 3.2rem;
        padding-bottom: 4rem;
        max-width: 1450px;
    }

    h1 {
        font-size: 2.4rem !important;
        font-weight: 750 !important;
        letter-spacing: -0.04em;
    }

    h2 {
        font-size: 1.55rem !important;
        font-weight: 700 !important;
        letter-spacing: -0.025em;
        margin-top: 0.8rem;
    }

    h3 {
        font-size: 1.25rem !important;
        font-weight: 700 !important;
    }

    .small-muted {
        color: #7d8590;
        font-size: 0.83rem;
    }

    .source-text {
        color: #9097a1;
        font-size: 0.78rem;
    }

    div[data-testid="stMetric"] {
        padding-top: 0.15rem;
        padding-bottom: 0.15rem;
    }

    div[data-testid="stMetricLabel"] {
        font-size: 0.82rem;
    }

    div[data-testid="stMetricValue"] {
        font-size: 2rem;
    }

    hr {
        margin-top: 2rem;
        margin-bottom: 2rem;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 3. HELPERS
# ============================================================

@st.cache_data
def read_csv_safe(path):
    if not path.exists():
        return pd.DataFrame()

    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def find_column(df, candidates):
    if df.empty:
        return None

    for col in candidates:
        if col in df.columns:
            return col

    return None


def parse_date_column(df):
    if df.empty:
        return df

    date_col = find_column(
        df,
        [
            "기준월",
            "년월",
            "date",
            "Date",
            "month",
            "Month",
        ],
    )

    if date_col is not None:
        df = df.copy()
        df[date_col] = pd.to_datetime(
            df[date_col],
            errors="coerce",
        )

    return df


def fmt_bn(value, digits=2):
    if pd.isna(value):
        return "-"

    return f"${value:,.{digits}f}B"


def fmt_pct(value, digits=1):
    if pd.isna(value):
        return "-"

    sign = "+" if value > 0 else ""

    return f"{sign}{value:,.{digits}f}%"


def fmt_pp(value, digits=1):
    if pd.isna(value):
        return "-"

    sign = "+" if value > 0 else ""

    return f"{sign}{value:,.{digits}f}pp"


def safe_div(a, b):
    if pd.isna(a) or pd.isna(b) or b == 0:
        return np.nan

    return a / b


def normalize_total_df(df):
    if df.empty:
        return df

    df = parse_date_column(df.copy())

    date_col = find_column(
        df,
        ["기준월", "년월", "date", "Date"],
    )

    amount_col = find_column(
        df,
        [
            "전체수출_USD",
            "총수출_USD",
            "수출액_USD",
            "수출금액",
            "수출액",
        ],
    )

    bn_col = find_column(
        df,
        [
            "전체수출_bn",
            "총수출_bn",
            "수출액_bn",
            "수출액_십억달러",
        ],
    )

    if amount_col is not None:
        df["total_usd"] = pd.to_numeric(
            df[amount_col],
            errors="coerce",
        )

        # 천 달러 단위일 가능성 보정
        median_value = df["total_usd"].median()

        if pd.notna(median_value) and median_value < 1e9:
            df["total_usd"] *= 1000

    elif bn_col is not None:
        df["total_usd"] = (
            pd.to_numeric(
                df[bn_col],
                errors="coerce",
            )
            * 1e9
        )

    else:
        return pd.DataFrame()

    df["total_bn"] = df["total_usd"] / 1e9

    df = (
        df[
            [date_col, "total_usd", "total_bn"]
        ]
        .dropna(subset=[date_col])
        .sort_values(date_col)
        .rename(columns={date_col: "기준월"})
        .reset_index(drop=True)
    )

    df["YoY_%"] = (
        df["total_usd"]
        .pct_change(12)
        * 100
    )

    df["MoM_%"] = (
        df["total_usd"]
        .pct_change()
        * 100
    )

    return df


# ============================================================
# 4. LOAD
# ============================================================

total = normalize_total_df(
    read_csv_safe(FILES["total"])
)

industry_monthly = parse_date_column(
    read_csv_safe(FILES["industry_monthly"])
)

industry_latest = parse_date_column(
    read_csv_safe(FILES["industry_latest"])
)

industry_ytd = read_csv_safe(
    FILES["industry_ytd"]
)

industry_qc_summary = read_csv_safe(
    FILES["industry_qc_summary"]
)

industry_qc_industry = read_csv_safe(
    FILES["industry_qc_industry"]
)

country_monthly = parse_date_column(
    read_csv_safe(FILES["country_monthly"])
)

country_latest = parse_date_column(
    read_csv_safe(FILES["country_latest"])
)

country_ytd = read_csv_safe(
    FILES["country_ytd"]
)

product_country_monthly = parse_date_column(
    read_csv_safe(FILES["product_country_monthly"])
)

product_country_latest = parse_date_column(
    read_csv_safe(FILES["product_country_latest"])
)

product_country_ytd = read_csv_safe(
    FILES["product_country_ytd"]
)

product_master = read_csv_safe(
    FILES["product_master"]
)


# ============================================================
# 5. INDUSTRY PREP
# ============================================================

if not industry_monthly.empty:

    industry_monthly["수출액_USD"] = pd.to_numeric(
        industry_monthly["수출액_USD"],
        errors="coerce",
    )

    industry_monthly["수출액_bn"] = (
        industry_monthly["수출액_USD"]
        / 1e9
    )

    industry_monthly = industry_monthly.sort_values(
        ["산업20", "기준월"]
    )

    if "YoY_%" not in industry_monthly.columns:
        industry_monthly["YoY_%"] = (
            industry_monthly
            .groupby("산업20")["수출액_USD"]
            .pct_change(12)
            * 100
        )

    if "MoM_%" not in industry_monthly.columns:
        industry_monthly["MoM_%"] = (
            industry_monthly
            .groupby("산업20")["수출액_USD"]
            .pct_change()
            * 100
        )

    if "3M_YoY_%" not in industry_monthly.columns:
        industry_monthly["3M_YoY_%"] = (
            industry_monthly
            .groupby("산업20")["YoY_%"]
            .transform(
                lambda x: x.rolling(
                    3,
                    min_periods=1,
                ).mean()
            )
        )

    industry_monthly["Momentum_Gap_pp"] = (
        industry_monthly["YoY_%"]
        -
        industry_monthly["3M_YoY_%"]
    )


# ============================================================
# 6. GLOBAL LATEST MONTH
# ============================================================

latest_month = None

if not industry_monthly.empty:
    latest_month = industry_monthly["기준월"].max()

elif not total.empty:
    latest_month = total["기준월"].max()


# ============================================================
# 7. HEADER
# ============================================================

st.title("Korea Export Monitor")

if latest_month is not None:

    st.markdown(
        f"""
        <div class="small-muted">
        {latest_month.strftime("%Y.%m")} CONFIRMED |
        Total / Country / HSK: Korea Customs Service |
        Industry Classification: KITA Official MTI-HSK Mapping
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# 8. TABS
# ============================================================

tab_overview, tab_industry, tab_country, tab_product_country = st.tabs(
    [
        "Overview",
        "Industry",
        "Country",
        "Product × Country",
    ]
)


# ============================================================
# 9. OVERVIEW
# ============================================================

with tab_overview:

    st.header("Korea Export Pulse")


    # --------------------------------------------------------
    # Latest Total
    # --------------------------------------------------------

    total_latest = None
    total_prev_month = None
    total_prev_year = None

    if not total.empty:

        total_latest = total.iloc[-1]

        current_date = total_latest["기준월"]

        prev_month_df = total[
            total["기준월"]
            ==
            (
                current_date
                - pd.DateOffset(months=1)
            )
        ]

        prev_year_df = total[
            total["기준월"]
            ==
            (
                current_date
                - pd.DateOffset(years=1)
            )
        ]

        if not prev_month_df.empty:
            total_prev_month = prev_month_df.iloc[-1]

        if not prev_year_df.empty:
            total_prev_year = prev_year_df.iloc[-1]


    # --------------------------------------------------------
    # Latest 20 industry basket
    # --------------------------------------------------------

    industry_current = pd.DataFrame()
    industry_previous_year = pd.DataFrame()

    industry20_latest_usd = np.nan
    industry20_latest_bn = np.nan

    if latest_month is not None and not industry_monthly.empty:

        industry_current = industry_monthly[
            industry_monthly["기준월"]
            ==
            latest_month
        ].copy()

        industry_previous_year = industry_monthly[
            industry_monthly["기준월"]
            ==
            (
                latest_month
                - pd.DateOffset(years=1)
            )
        ].copy()

        industry20_latest_usd = (
            industry_current["수출액_USD"]
            .sum()
        )

        industry20_latest_bn = (
            industry20_latest_usd
            / 1e9
        )


    # --------------------------------------------------------
    # Coverage
    # --------------------------------------------------------

    total_latest_usd = np.nan
    total_latest_bn = np.nan
    total_mom = np.nan
    total_yoy = np.nan

    if total_latest is not None:

        total_latest_usd = total_latest[
            "total_usd"
        ]

        total_latest_bn = total_latest[
            "total_bn"
        ]

        total_mom = total_latest[
            "MoM_%"
        ]

        total_yoy = total_latest[
            "YoY_%"
        ]


    coverage = (
        safe_div(
            industry20_latest_usd,
            total_latest_usd,
        )
        * 100
    )


    # --------------------------------------------------------
    # YTD
    # --------------------------------------------------------

    ytd_current = np.nan
    ytd_previous = np.nan
    ytd_yoy = np.nan

    if (
        latest_month is not None
        and
        not total.empty
    ):

        current_year = latest_month.year
        current_month_num = latest_month.month

        ytd_current = (
            total[
                (total["기준월"].dt.year == current_year)
                &
                (total["기준월"].dt.month <= current_month_num)
            ]["total_usd"]
            .sum()
        )

        ytd_previous = (
            total[
                (total["기준월"].dt.year == current_year - 1)
                &
                (total["기준월"].dt.month <= current_month_num)
            ]["total_usd"]
            .sum()
        )

        ytd_yoy = (
            (
                ytd_current
                /
                ytd_previous
                - 1
            )
            * 100
            if ytd_previous != 0
            else np.nan
        )


    # --------------------------------------------------------
    # Growth Explained
    # --------------------------------------------------------

    growth_explained = np.nan
    total_growth_usd = np.nan
    industry_growth_usd = np.nan

    if (
        total_latest is not None
        and
        total_prev_year is not None
        and
        not industry_current.empty
        and
        not industry_previous_year.empty
    ):

        total_growth_usd = (
            total_latest["total_usd"]
            -
            total_prev_year["total_usd"]
        )

        current_industry_sum = (
            industry_current[
                "수출액_USD"
            ].sum()
        )

        previous_industry_sum = (
            industry_previous_year[
                "수출액_USD"
            ].sum()
        )

        industry_growth_usd = (
            current_industry_sum
            -
            previous_industry_sum
        )

        growth_explained = (
            safe_div(
                industry_growth_usd,
                total_growth_usd,
            )
            * 100
        )


    # --------------------------------------------------------
    # KPI
    # --------------------------------------------------------

    k1, k2, k3, k4, k5, k6 = st.columns(6)

    with k1:
        st.metric(
            "한국 총수출",
            fmt_bn(total_latest_bn),
            fmt_pct(total_yoy) + " YoY",
        )

    with k2:
        st.metric(
            "MoM",
            fmt_pct(total_mom),
        )

    with k3:
        st.metric(
            f"{latest_month.year} YTD"
            if latest_month is not None
            else "YTD",
            fmt_bn(
                ytd_current / 1e9
                if pd.notna(ytd_current)
                else np.nan,
                1,
            ),
            fmt_pct(ytd_yoy) + " YoY",
        )

    with k4:
        st.metric(
            "20 Industry Basket",
            fmt_bn(
                industry20_latest_bn
            ),
        )

    with k5:
        st.metric(
            "Coverage",
            fmt_pct(
                coverage
            ),
        )

    with k6:
        st.metric(
            "Growth Explained",
            fmt_pct(
                growth_explained
            ),
        )


    st.markdown(
        """
        <div class="small-muted">
        20 Industry Basket = KITA 공식 MTI-HSK 연계표 기준 20대 산업 합계.
        Coverage = 20대 산업 수출 / 한국 전체 수출.
        Growth Explained = 전체 수출 YoY 증가액 중 20대 산업 증가액이 설명하는 비율.
        </div>
        """,
        unsafe_allow_html=True,
    )


    # ========================================================
    # GROWTH COMPOSITION
    # ========================================================

    st.subheader("Growth Composition")

    semi_yoy = np.nan
    ex_semi_yoy = np.nan
    semi_growth_contribution = np.nan

    if (
        not industry_current.empty
        and
        not industry_previous_year.empty
    ):

        semi_now = industry_current[
            industry_current["산업20"]
            ==
            "반도체"
        ]

        semi_prev = industry_previous_year[
            industry_previous_year["산업20"]
            ==
            "반도체"
        ]

        if (
            not semi_now.empty
            and
            not semi_prev.empty
        ):

            semi_now_value = semi_now[
                "수출액_USD"
            ].sum()

            semi_prev_value = semi_prev[
                "수출액_USD"
            ].sum()

            semi_yoy = (
                (
                    semi_now_value
                    /
                    semi_prev_value
                    - 1
                )
                * 100
            )

            semi_growth_usd = (
                semi_now_value
                -
                semi_prev_value
            )

            semi_growth_contribution = (
                safe_div(
                    semi_growth_usd,
                    total_growth_usd,
                )
                * 100
            )

            ex_now = (
                industry_current[
                    "수출액_USD"
                ].sum()
                -
                semi_now_value
            )

            ex_prev = (
                industry_previous_year[
                    "수출액_USD"
                ].sum()
                -
                semi_prev_value
            )

            if ex_prev != 0:
                ex_semi_yoy = (
                    (
                        ex_now
                        /
                        ex_prev
                        - 1
                    )
                    * 100
                )


    g1, g2, g3, g4 = st.columns(4)

    g1.metric(
        "Total Export YoY",
        fmt_pct(total_yoy),
    )

    g2.metric(
        "Semiconductor YoY",
        fmt_pct(semi_yoy),
    )

    g3.metric(
        "Core ex-Semi YoY",
        fmt_pct(ex_semi_yoy),
    )

    g4.metric(
        "Semi Growth Contribution",
        fmt_pct(
            semi_growth_contribution
        ),
    )


    # ========================================================
    # RESEARCH TAKEAWAYS
    # ========================================================

    st.subheader("Research Takeaways")

    takeaway_lines = []

    if (
        not industry_current.empty
        and
        not industry_previous_year.empty
    ):

        contrib = industry_current[
            [
                "산업20",
                "수출액_USD",
                "YoY_%",
                "3M_YoY_%",
                "Momentum_Gap_pp",
            ]
        ].merge(
            industry_previous_year[
                [
                    "산업20",
                    "수출액_USD",
                ]
            ],
            on="산업20",
            how="left",
            suffixes=(
                "_현재",
                "_전년",
            ),
        )

        contrib[
            "증감액_USD"
        ] = (
            contrib[
                "수출액_USD_현재"
            ]
            -
            contrib[
                "수출액_USD_전년"
            ]
        )

        contrib[
            "증감액_bn"
        ] = (
            contrib[
                "증감액_USD"
            ]
            / 1e9
        )

        positive = contrib.sort_values(
            "증감액_USD",
            ascending=False,
        )

        momentum = contrib.sort_values(
            "Momentum_Gap_pp",
            ascending=False,
        )

        slowdown = contrib.sort_values(
            "Momentum_Gap_pp",
            ascending=True,
        )

        if not positive.empty:

            row = positive.iloc[0]

            share_of_growth = (
                safe_div(
                    row["증감액_USD"],
                    total_growth_usd,
                )
                * 100
            )

            takeaway_lines.append(
                f"**{row['산업20']}**가 전년동월 대비 "
                f"{row['증감액_bn']:+.2f}B 증가하며 "
                f"전체 수출 증가분의 약 "
                f"{share_of_growth:.1f}%를 설명."
            )

        if not momentum.empty:

            row = momentum.iloc[0]

            takeaway_lines.append(
                f"**{row['산업20']}**는 YoY "
                f"{row['YoY_%']:+.1f}%로 증가하는 가운데 "
                f"최근 3개월 추세 대비 "
                f"{row['Momentum_Gap_pp']:+.1f}pp 가속."
            )

        if not slowdown.empty:

            row = slowdown.iloc[0]

            takeaway_lines.append(
                f"**{row['산업20']}**는 YoY "
                f"{row['YoY_%']:+.1f}%이나 "
                f"최근 3개월 추세 대비 "
                f"{row['Momentum_Gap_pp']:+.1f}pp 둔화."
            )


    for line in takeaway_lines[:3]:
        st.markdown(f"- {line}")


    st.divider()


    # ========================================================
    # TOTAL EXPORT TREND
    # ========================================================

    st.subheader("Total Export Trend")

    if not total.empty:

        fig_total = px.line(
            total,
            x="기준월",
            y="total_bn",
            markers=True,
            labels={
                "기준월": "",
                "total_bn": "USD bn",
            },
        )

        fig_total.update_layout(
            height=420,
            margin=dict(
                l=10,
                r=20,
                t=20,
                b=10,
            ),
            hovermode="x unified",
        )

        fig_total.update_xaxes(
            showgrid=False
        )

        st.plotly_chart(
            fig_total,
            width="stretch",
        )


    st.divider()


    # ========================================================
    # MOMENTUM MAP
    # ========================================================

    st.subheader("Industry Momentum Map")

    st.markdown(
        """
        <div class="small-muted">
        X축 = 당월 YoY / Y축 = 당월 YoY - 최근 3개월 YoY 평균.
        우상단은 성장률이 높고 최근 모멘텀도 가속되는 산업입니다.
        </div>
        """,
        unsafe_allow_html=True,
    )


    left, right = st.columns(
        [1.35, 1]
    )


    with left:

        if not industry_current.empty:

            momentum_df = (
                industry_current[
                    [
                        "산업20",
                        "YoY_%",
                        "3M_YoY_%",
                        "Momentum_Gap_pp",
                        "수출액_bn",
                    ]
                ]
                .dropna(
                    subset=[
                        "YoY_%",
                        "Momentum_Gap_pp",
                    ]
                )
                .copy()
            )

            fig_momentum = px.scatter(
                momentum_df,
                x="YoY_%",
                y="Momentum_Gap_pp",
                size="수출액_bn",
                text="산업20",
                hover_data={
                    "산업20": True,
                    "YoY_%": ":.1f",
                    "3M_YoY_%": ":.1f",
                    "Momentum_Gap_pp": ":.1f",
                    "수출액_bn": ":.2f",
                },
                labels={
                    "YoY_%": "당월 YoY (%)",
                    "Momentum_Gap_pp":
                        "Momentum Gap (pp)",
                },
            )

            fig_momentum.add_hline(
                y=0,
                line_dash="dash",
            )

            fig_momentum.add_vline(
                x=0,
                line_dash="dash",
            )

            fig_momentum.update_traces(
                textposition="top center"
            )

            fig_momentum.update_layout(
                height=540,
                margin=dict(
                    l=10,
                    r=20,
                    t=20,
                    b=20,
                ),
            )

            st.plotly_chart(
                fig_momentum,
                width="stretch",
            )


    with right:

        st.subheader("Momentum Status")

        if not industry_current.empty:

            status = (
                industry_current[
                    [
                        "산업20",
                        "YoY_%",
                        "3M_YoY_%",
                        "Momentum_Gap_pp",
                    ]
                ]
                .sort_values(
                    "Momentum_Gap_pp",
                    ascending=False,
                )
                .copy()
            )

            status.columns = [
                "산업",
                "YoY (%)",
                "3M YoY (%)",
                "Gap (pp)",
            ]

            st.dataframe(
                status,
                width="stretch",
                hide_index=True,
                column_config={
                    "YoY (%)":
                        st.column_config.NumberColumn(
                            format="%.1f",
                        ),
                    "3M YoY (%)":
                        st.column_config.NumberColumn(
                            format="%.1f",
                        ),
                    "Gap (pp)":
                        st.column_config.NumberColumn(
                            format="%.1f",
                        ),
                },
            )


    st.divider()


    # ========================================================
    # GROWTH CONTRIBUTION
    # ========================================================

    st.subheader(
        "Contribution to Total Export Growth"
    )

    if (
        not industry_current.empty
        and
        not industry_previous_year.empty
    ):

        contribution = (
            industry_current[
                [
                    "산업20",
                    "수출액_USD",
                ]
            ]
            .merge(
                industry_previous_year[
                    [
                        "산업20",
                        "수출액_USD",
                    ]
                ],
                on="산업20",
                suffixes=(
                    "_현재",
                    "_전년",
                ),
            )
        )

        contribution[
            "증감액_bn"
        ] = (
            (
                contribution[
                    "수출액_USD_현재"
                ]
                -
                contribution[
                    "수출액_USD_전년"
                ]
            )
            / 1e9
        )

        contribution = contribution.sort_values(
            "증감액_bn",
            ascending=True,
        )

        fig_contrib = px.bar(
            contribution,
            x="증감액_bn",
            y="산업20",
            orientation="h",
            labels={
                "산업20": "",
                "증감액_bn":
                    "YoY Export Change (USD bn)",
            },
        )

        fig_contrib.update_layout(
            height=650,
            margin=dict(
                l=10,
                r=20,
                t=20,
                b=20,
            ),
        )

        st.plotly_chart(
            fig_contrib,
            width="stretch",
        )


# ============================================================
# 10. INDUSTRY TAB
# ============================================================

with tab_industry:

    st.header("20 Major Export Industries")

    if industry_monthly.empty:

        st.warning(
            "industry20_monthly.csv를 찾을 수 없습니다."
        )

    else:

        industries = sorted(
            industry_monthly[
                "산업20"
            ].dropna().unique()
        )

        selected_industry = st.selectbox(
            "산업 선택",
            industries,
        )


        df_ind = (
            industry_monthly[
                industry_monthly[
                    "산업20"
                ]
                ==
                selected_industry
            ]
            .sort_values(
                "기준월"
            )
            .copy()
        )


        latest_ind = df_ind.iloc[-1]


        # ----------------------------------------------------
        # YTD
        # ----------------------------------------------------

        ytd_row = pd.DataFrame()

        if (
            not industry_ytd.empty
            and
            "산업20"
            in industry_ytd.columns
        ):

            ytd_row = industry_ytd[
                industry_ytd[
                    "산업20"
                ]
                ==
                selected_industry
            ]


        c1, c2, c3, c4, c5 = st.columns(5)

        c1.metric(
            "당월 수출",
            fmt_bn(
                latest_ind[
                    "수출액_bn"
                ]
            ),
        )

        c2.metric(
            "YoY",
            fmt_pct(
                latest_ind[
                    "YoY_%"
                ]
            ),
        )

        c3.metric(
            "MoM",
            fmt_pct(
                latest_ind[
                    "MoM_%"
                ]
            ),
        )

        c4.metric(
            "3M YoY",
            fmt_pct(
                latest_ind[
                    "3M_YoY_%"
                ]
            ),
        )

        if not ytd_row.empty:

            ytd_value_col = find_column(
                ytd_row,
                [
                    "현재YTD_bn",
                    "2026_YTD_bn",
                ],
            )

            ytd_yoy_col = find_column(
                ytd_row,
                [
                    "YTD_YoY_%",
                ],
            )

            if ytd_value_col is not None:

                c5.metric(
                    "YTD",
                    fmt_bn(
                        ytd_row.iloc[0][
                            ytd_value_col
                        ]
                    ),
                    (
                        fmt_pct(
                            ytd_row.iloc[0][
                                ytd_yoy_col
                            ]
                        )
                        + " YoY"
                        if ytd_yoy_col
                        else None
                    ),
                )


        st.divider()


        # ----------------------------------------------------
        # Monthly Export
        # ----------------------------------------------------

        st.subheader(
            f"{selected_industry} Monthly Export"
        )

        fig_ind_export = px.line(
            df_ind,
            x="기준월",
            y="수출액_bn",
            markers=True,
            labels={
                "기준월": "",
                "수출액_bn": "USD bn",
            },
        )

        fig_ind_export.update_layout(
            height=430,
            hovermode="x unified",
        )

        st.plotly_chart(
            fig_ind_export,
            width="stretch",
        )


        # ----------------------------------------------------
        # Growth rates
        # ----------------------------------------------------

        st.subheader(
            "Growth Momentum"
        )

        momentum_long = df_ind[
            [
                "기준월",
                "YoY_%",
                "3M_YoY_%",
                "MoM_%",
            ]
        ].melt(
            id_vars="기준월",
            var_name="지표",
            value_name="%",
        )

        fig_growth = px.line(
            momentum_long,
            x="기준월",
            y="%",
            color="지표",
            markers=True,
        )

        fig_growth.add_hline(
            y=0,
            line_dash="dash",
        )

        fig_growth.update_layout(
            height=430,
            hovermode="x unified",
        )

        st.plotly_chart(
            fig_growth,
            width="stretch",
        )


        # ----------------------------------------------------
        # Industry Ranking
        # ----------------------------------------------------

        st.subheader(
            "Latest Industry Ranking"
        )

        latest_table = (
            industry_monthly[
                industry_monthly[
                    "기준월"
                ]
                ==
                latest_month
            ][
                [
                    "산업20",
                    "수출액_bn",
                    "YoY_%",
                    "MoM_%",
                    "3M_YoY_%",
                    "Momentum_Gap_pp",
                ]
            ]
            .sort_values(
                "수출액_bn",
                ascending=False,
            )
            .reset_index(drop=True)
        )

        latest_table.index += 1

        st.dataframe(
            latest_table,
            width="stretch",
            column_config={
                "수출액_bn":
                    st.column_config.NumberColumn(
                        "USD bn",
                        format="%.2f",
                    ),
                "YoY_%":
                    st.column_config.NumberColumn(
                        "YoY (%)",
                        format="%.1f",
                    ),
                "MoM_%":
                    st.column_config.NumberColumn(
                        "MoM (%)",
                        format="%.1f",
                    ),
                "3M_YoY_%":
                    st.column_config.NumberColumn(
                        "3M YoY (%)",
                        format="%.1f",
                    ),
                "Momentum_Gap_pp":
                    st.column_config.NumberColumn(
                        "Gap (pp)",
                        format="%.1f",
                    ),
            },
        )


        # ----------------------------------------------------
        # QC disclosure
        # ----------------------------------------------------

        if not industry_qc_industry.empty:

            st.divider()

            st.subheader(
                "Data Quality"
            )

            qc_row = industry_qc_industry[
                industry_qc_industry[
                    "산업20"
                ]
                ==
                selected_industry
            ]

            if not qc_row.empty:

                st.dataframe(
                    qc_row,
                    width="stretch",
                    hide_index=True,
                )


# ============================================================
# 11. COUNTRY TAB
# ============================================================

with tab_country:

    st.header("Country Export Monitor")

    if country_monthly.empty:

        st.warning(
            "country_monthly.csv를 찾을 수 없습니다."
        )

    else:

        country_col = find_column(
            country_monthly,
            [
                "국가",
                "국가명",
            ],
        )

        date_col = find_column(
            country_monthly,
            [
                "기준월",
            ],
        )

        amount_col = find_column(
            country_monthly,
            [
                "수출액_십억달러",
                "수출액_bn",
            ],
        )

        usd_col = find_column(
            country_monthly,
            [
                "수출액_USD",
            ],
        )


        if (
            amount_col is None
            and
            usd_col is not None
        ):

            country_monthly[
                "수출액_bn"
            ] = (
                pd.to_numeric(
                    country_monthly[
                        usd_col
                    ],
                    errors="coerce",
                )
                / 1e9
            )

            amount_col = "수출액_bn"


        countries = sorted(
            country_monthly[
                country_col
            ]
            .dropna()
            .unique()
        )


        selected_country = st.selectbox(
            "수출 대상국 선택",
            countries,
        )


        df_country = (
            country_monthly[
                country_monthly[
                    country_col
                ]
                ==
                selected_country
            ]
            .sort_values(
                date_col
            )
            .copy()
        )


        latest_country = df_country.iloc[-1]


        yoy_col = find_column(
            df_country,
            ["YoY_%"],
        )

        mom_col = find_column(
            df_country,
            ["MoM_%"],
        )


        cc1, cc2, cc3 = st.columns(3)

        cc1.metric(
            "대상국 당월 수출",
            fmt_bn(
                latest_country[
                    amount_col
                ]
            ),
        )

        if yoy_col:
            cc2.metric(
                "대상국 YoY",
                fmt_pct(
                    latest_country[
                        yoy_col
                    ]
                ),
            )

        if mom_col:
            cc3.metric(
                "대상국 MoM",
                fmt_pct(
                    latest_country[
                        mom_col
                    ]
                ),
            )


        st.subheader(
            f"{selected_country} 월별 수출"
        )


        fig_country = px.line(
            df_country,
            x=date_col,
            y=amount_col,
            markers=True,
            labels={
                date_col: "",
                amount_col: "USD bn",
            },
        )

        fig_country.update_layout(
            height=450,
        )

        st.plotly_chart(
            fig_country,
            width="stretch",
        )


        if not country_ytd.empty:

            st.subheader(
                "Country YTD Ranking"
            )

            st.dataframe(
                country_ytd,
                width="stretch",
                hide_index=True,
            )


# ============================================================
# 12. PRODUCT × COUNTRY TAB
# ============================================================

with tab_product_country:

    st.header(
        "Product × Country Monitor"
    )


    if product_country_monthly.empty:

        st.warning(
            "product_country_multi_monthly.csv를 "
            "찾을 수 없습니다."
        )

    else:

        product_col = find_column(
            product_country_monthly,
            [
                "대상품목",
                "품목",
                "품목명",
            ],
        )

        country_col = find_column(
            product_country_monthly,
            [
                "국가",
                "국가명",
            ],
        )

        date_col = find_column(
            product_country_monthly,
            [
                "기준월",
            ],
        )

        usd_col = find_column(
            product_country_monthly,
            [
                "수출액_USD",
            ],
        )

        bn_col = find_column(
            product_country_monthly,
            [
                "수출액_bn",
                "수출액_십억달러",
            ],
        )


        if (
            bn_col is None
            and
            usd_col is not None
        ):

            product_country_monthly[
                "수출액_bn"
            ] = (
                pd.to_numeric(
                    product_country_monthly[
                        usd_col
                    ],
                    errors="coerce",
                )
                / 1e9
            )

            bn_col = "수출액_bn"


        if (
            product_col is None
            or
            country_col is None
        ):

            st.error(
                "Product × Country CSV의 "
                "품목/국가 컬럼을 찾지 못했습니다."
            )

        else:

            products = sorted(
                product_country_monthly[
                    product_col
                ]
                .dropna()
                .unique()
            )


            selected_product = st.selectbox(
                "품목 선택",
                products,
            )


            product_data = product_country_monthly[
                product_country_monthly[
                    product_col
                ]
                ==
                selected_product
            ].copy()


            countries = sorted(
                product_data[
                    country_col
                ]
                .dropna()
                .unique()
            )


            selected_pc_country = st.selectbox(
                "대상국 선택",
                countries,
            )


            df_pc = (
                product_data[
                    product_data[
                        country_col
                    ]
                    ==
                    selected_pc_country
                ]
                .sort_values(
                    date_col
                )
                .copy()
            )


            latest_pc = df_pc.iloc[-1]


            yoy_col = find_column(
                df_pc,
                ["YoY_%"],
            )

            mom_col = find_column(
                df_pc,
                ["MoM_%"],
            )


            pc1, pc2, pc3 = st.columns(3)

            pc1.metric(
                "대상국 당월 수출",
                fmt_bn(
                    latest_pc[
                        bn_col
                    ]
                ),
            )

            if yoy_col:
                pc2.metric(
                    "대상국 YoY",
                    fmt_pct(
                        latest_pc[
                            yoy_col
                        ]
                    ),
                )

            if mom_col:
                pc3.metric(
                    "대상국 MoM",
                    fmt_pct(
                        latest_pc[
                            mom_col
                        ]
                    ),
                )


            st.subheader(
                f"{selected_product} → "
                f"{selected_pc_country} 월별 수출"
            )


            fig_pc = px.line(
                df_pc,
                x=date_col,
                y=bn_col,
                markers=True,
                labels={
                    date_col: "",
                    bn_col: "USD bn",
                },
            )

            fig_pc.update_layout(
                height=450,
            )

            st.plotly_chart(
                fig_pc,
                width="stretch",
            )


            if not product_country_ytd.empty:

                ytd_product_col = find_column(
                    product_country_ytd,
                    [
                        "대상품목",
                        "품목",
                        "품목명",
                    ],
                )

                if ytd_product_col:

                    ytd_subset = product_country_ytd[
                        product_country_ytd[
                            ytd_product_col
                        ]
                        ==
                        selected_product
                    ]

                else:

                    ytd_subset = (
                        product_country_ytd
                    )


                st.subheader(
                    f"{selected_product} YTD Top Countries"
                )

                st.dataframe(
                    ytd_subset,
                    width="stretch",
                    hide_index=True,
                )


# ============================================================
# 13. FOOTER
# ============================================================

st.divider()

st.markdown(
    """
    <div class="source-text">
    Data: Korea Customs Service, KITA K-stat.
    Industry classification uses the official 2026 MTI-HSK linkage table.
    Production QC: official 20-industry master / monthly integrity /
    KITA independent reconciliation / universe coverage.
    </div>
    """,
    unsafe_allow_html=True,
)