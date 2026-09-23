import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path


# ============================================================
# 1. PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Korea Export Monitor",
    page_icon="🇰🇷",
    layout="wide"
)

BASE_DIR = Path(__file__).resolve().parent


# ============================================================
# 2. DATA LOAD
# ============================================================

@st.cache_data
def load_csv(filename):
    path = BASE_DIR / filename

    if not path.exists():
        return pd.DataFrame()

    return pd.read_csv(
        path,
        encoding="utf-8-sig"
    )


industry_monthly = load_csv("industry_monthly.csv")
industry_ytd = load_csv("industry_ytd.csv")

total_export = load_csv(
    "korea_total_export_monthly.csv"
)

ex_semi = load_csv(
    "ex_semiconductor_pulse.csv"
)

country_monthly = load_csv(
    "country_monthly.csv"
)

country_latest_top10 = load_csv(
    "country_latest_top10.csv"
)

country_ytd_top10 = load_csv(
    "country_ytd_top10.csv"
)

product_master = load_csv(
    "product_master.csv"
)

product_country_monthly = load_csv(
    "product_country_multi_monthly.csv"
)

product_country_latest_top10 = load_csv(
    "product_country_multi_latest_top10.csv"
)

product_country_ytd_top10 = load_csv(
    "product_country_multi_ytd_top10.csv"
)


# ============================================================
# 3. DATE CONVERSION
# ============================================================

for df in [
    industry_monthly,
    total_export,
    ex_semi,
    country_monthly,
    product_country_monthly
]:

    if (
        not df.empty
        and
        "기준월" in df.columns
    ):

        df["기준월"] = pd.to_datetime(
            df["기준월"],
            errors="coerce"
        )


# ============================================================
# 4. COMMON DATE
# ============================================================

if total_export.empty:
    st.error(
        "korea_total_export_monthly.csv가 없습니다."
    )
    st.stop()


latest_date = total_export[
    "기준월"
].max()

latest_year = latest_date.year
latest_month = latest_date.month

previous_date = (
    latest_date
    -
    pd.DateOffset(years=1)
)


# ============================================================
# 5. TOTAL EXPORT
# ============================================================

latest_total_row = (
    total_export[
        total_export["기준월"]
        ==
        latest_date
    ]
    .iloc[0]
)

latest_total_bn = (
    latest_total_row["총수출_bn"]
)

latest_total_yoy = (
    latest_total_row["YoY_%"]
)

latest_total_mom = (
    latest_total_row["MoM_%"]
)


prev_total_row = (
    total_export[
        total_export["기준월"]
        ==
        previous_date
    ]
)

if not prev_total_row.empty:
    prev_total_bn = (
        prev_total_row.iloc[0]["총수출_bn"]
    )
else:
    prev_total_bn = np.nan


total_growth_bn = (
    latest_total_bn
    -
    prev_total_bn
)


# ============================================================
# 6. TOTAL EXPORT YTD
# ============================================================

current_ytd = total_export[
    (
        total_export["기준월"].dt.year
        ==
        latest_year
    )
    &
    (
        total_export["기준월"].dt.month
        <=
        latest_month
    )
]["수출액_USD"].sum()


previous_ytd = total_export[
    (
        total_export["기준월"].dt.year
        ==
        latest_year - 1
    )
    &
    (
        total_export["기준월"].dt.month
        <=
        latest_month
    )
]["수출액_USD"].sum()


current_ytd_bn = (
    current_ytd
    /
    1_000_000_000
)


if previous_ytd != 0:

    total_ytd_yoy = (
        current_ytd
        /
        previous_ytd
        -
        1
    ) * 100

else:
    total_ytd_yoy = np.nan


# ============================================================
# 7. CORE INDUSTRY BASKET
# ============================================================

pulse = pd.DataFrame()

if not industry_monthly.empty:

    industry_latest = (
        industry_monthly[
            industry_monthly["기준월"]
            ==
            latest_date
        ]
        .copy()
    )

    industry_previous = (
        industry_monthly[
            industry_monthly["기준월"]
            ==
            previous_date
        ]
        [
            [
                "산업",
                "수출액_USD"
            ]
        ]
        .rename(
            columns={
                "수출액_USD":
                "전년동월_산업수출_USD"
            }
        )
    )


    core_basket_bn = (
        industry_latest[
            "수출액_USD"
        ].sum()
        /
        1_000_000_000
    )


    coverage_ratio = (
        core_basket_bn
        /
        latest_total_bn
        *
        100
    )


    pulse = industry_latest.merge(
        industry_previous,
        on="산업",
        how="left"
    )


    pulse["증가액_USD"] = (
        pulse["수출액_USD"]
        -
        pulse[
            "전년동월_산업수출_USD"
        ]
    )


    pulse["증가액_bn"] = (
        pulse["증가액_USD"]
        /
        1_000_000_000
    )


    if total_growth_bn != 0:

        pulse[
            "전체수출증가기여도_%"
        ] = (
            pulse["증가액_bn"]
            /
            total_growth_bn
            *
            100
        )

    else:
        pulse[
            "전체수출증가기여도_%"
        ] = np.nan


    core_growth_bn = (
        pulse["증가액_bn"]
        .sum()
    )


    if total_growth_bn != 0:

        core_growth_explained = (
            core_growth_bn
            /
            total_growth_bn
            *
            100
        )

    else:
        core_growth_explained = np.nan


    pulse["Momentum_Gap_%p"] = (
        pulse["KITA_YoY_%"]
        -
        pulse["3M_YoY_%"]
    )


    def momentum_class(row):

        yoy = row["KITA_YoY_%"]
        gap = row["Momentum_Gap_%p"]

        if pd.isna(yoy) or pd.isna(gap):
            return "N/A"

        if yoy > 0 and gap > 0:
            return "성장·가속"

        elif yoy > 0 and gap <= 0:
            return "성장·둔화"

        elif yoy <= 0 and gap > 0:
            return "부진·회복"

        else:
            return "부진·약화"


    pulse[
        "Momentum_국면"
    ] = pulse.apply(
        momentum_class,
        axis=1
    )


    x_abs = (
        pulse["KITA_YoY_%"]
        .abs()
        .dropna()
    )

    if not x_abs.empty:

        x_cap = max(
            60,
            x_abs.quantile(0.85)
        )

    else:
        x_cap = 100


    pulse["YoY_Display"] = (
        pulse["KITA_YoY_%"]
        .clip(
            lower=-x_cap,
            upper=x_cap
        )
    )

else:

    core_basket_bn = np.nan
    coverage_ratio = np.nan
    core_growth_explained = np.nan


# ============================================================
# 8. EX-SEMICONDUCTOR METRICS
# ============================================================

semi_yoy = np.nan
core_ex_semi_yoy = np.nan

semi_contribution = np.nan
core_ex_semi_contribution = np.nan

semi_change_bn = np.nan
core_ex_semi_change_bn = np.nan


if not ex_semi.empty:

    latest_ex = (
        ex_semi[
            ex_semi["기준월"]
            ==
            latest_date
        ]
    )

    prev_ex = (
        ex_semi[
            ex_semi["기준월"]
            ==
            previous_date
        ]
    )


    if not latest_ex.empty:

        latest_ex = latest_ex.iloc[0]

        semi_yoy = (
            latest_ex[
                "반도체_YoY_%"
            ]
        )

        core_ex_semi_yoy = (
            latest_ex[
                "Core_ex_Semi_YoY_%"
            ]
        )


    if (
        not latest_ex.empty
        and
        not prev_ex.empty
    ):

        prev_ex = prev_ex.iloc[0]

        semi_change_bn = (
            latest_ex["반도체_USD"]
            -
            prev_ex["반도체_USD"]
        ) / 1_000_000_000

        core_ex_semi_change_bn = (
            latest_ex["Core_ex_Semi_USD"]
            -
            prev_ex["Core_ex_Semi_USD"]
        ) / 1_000_000_000


        if total_growth_bn != 0:

            semi_contribution = (
                semi_change_bn
                /
                total_growth_bn
                *
                100
            )

            core_ex_semi_contribution = (
                core_ex_semi_change_bn
                /
                total_growth_bn
                *
                100
            )


# ============================================================
# 9. INDUSTRY NAME CLEANER
# ============================================================

def clean_industry_name(name):

    mapping = {
        "반도체 (831)": "반도체",
        "자동차 (741)": "자동차",
        "자동차부품 (742)": "자동차부품",
        "컴퓨터 (813)": "컴퓨터",
        "무선통신기기 (812)": "무선통신기기",
        "선박해양구조물및부품 (746)": "선박",
        "평판디스플레이 및 센서 (837)": "디스플레이"
    }

    return mapping.get(
        str(name),
        str(name)
    )


# ============================================================
# 10. RESEARCH INSIGHT ENGINE
# ============================================================

def generate_research_insights():

    insights = []

    # --------------------------------------------------------
    # 1. Concentration / breadth
    # --------------------------------------------------------

    if (
        not pd.isna(semi_contribution)
        and
        not pd.isna(core_ex_semi_contribution)
    ):

        if semi_contribution >= 60:

            text = (
                f"전체 수출은 YoY {latest_total_yoy:+.1f}% 증가했지만 "
                f"증가분의 {semi_contribution:.1f}%가 반도체에서 발생. "
                f"Core ex-Semiconductor도 ${core_ex_semi_change_bn:+.2f}B 증가하며 "
                f"전체 증가분의 {core_ex_semi_contribution:.1f}%를 설명해, "
                f"수출 개선의 중심은 반도체에 있으나 비반도체 확산도 일부 확인."
            )

        else:

            text = (
                f"전체 수출 증가분에서 반도체 기여도는 "
                f"{semi_contribution:.1f}%로 나타났으며, "
                f"Core ex-Semiconductor도 "
                f"{core_ex_semi_contribution:.1f}%를 설명. "
                f"수출 개선이 복수 산업으로 확산되는 흐름."
            )

        insights.append(text)


    # --------------------------------------------------------
    # 2. strongest acceleration
    # --------------------------------------------------------

    if not pulse.empty:

        accelerating = (
            pulse[
                pulse["Momentum_국면"]
                ==
                "성장·가속"
            ]
            .sort_values(
                "Momentum_Gap_%p",
                ascending=False
            )
        )

        if not accelerating.empty:

            row = accelerating.iloc[0]

            name = clean_industry_name(
                row["산업"]
            )

            insights.append(
                f"{name}는 YoY "
                f"{row['KITA_YoY_%']:+.1f}% 증가하며 "
                f"최근 3개월 추세 대비 "
                f"{row['Momentum_Gap_%p']:+.1f}%p 가속. "
                f"반도체 외 수출 모멘텀 확산 여부를 확인할 핵심 품목."
            )


    # --------------------------------------------------------
    # 3. slowing
    # --------------------------------------------------------

    if not pulse.empty:

        slowing = (
            pulse[
                pulse["Momentum_국면"]
                ==
                "성장·둔화"
            ]
            .sort_values(
                "Momentum_Gap_%p",
                ascending=True
            )
        )

        if not slowing.empty:

            row = slowing.iloc[0]

            name = clean_industry_name(
                row["산업"]
            )

            insights.append(
                f"{name}는 YoY "
                f"{row['KITA_YoY_%']:+.1f}%의 플러스 성장세를 유지하지만 "
                f"최근 3개월 추세 대비 "
                f"{abs(row['Momentum_Gap_%p']):.1f}%p 둔화. "
                f"헤드라인 성장률보다 모멘텀 방향 변화에 주목할 필요."
            )


    return insights[:3]


research_insights = generate_research_insights()


# ============================================================
# 11. HEADER
# ============================================================

st.title(
    "Korea Export Monitor"
)

st.caption(
    f"{latest_year}.{latest_month:02d} CONFIRMED "
    "| Total / Country / HS: Korea Customs Service "
    "| Industry: KITA K-stat MTI"
)


# ============================================================
# 12. TABS
# ============================================================

(
    tab_overview,
    tab_industry,
    tab_country,
    tab_product_country
) = st.tabs(
    [
        "Overview",
        "Industry",
        "Country",
        "Product × Country"
    ]
)


# ============================================================
# TAB 1 — OVERVIEW
# ============================================================

with tab_overview:

    st.subheader(
        "Korea Export Pulse"
    )


    # --------------------------------------------------------
    # KPI ROW 1
    # --------------------------------------------------------

    k1, k2, k3, k4, k5, k6 = (
        st.columns(6)
    )


    k1.metric(
        "한국 총수출",
        f"${latest_total_bn:,.2f}B",
        f"{latest_total_yoy:+.1f}% YoY"
    )

    k2.metric(
        "MoM",
        f"{latest_total_mom:+.1f}%"
    )

    k3.metric(
        f"{latest_year} YTD",
        f"${current_ytd_bn:,.1f}B",
        f"{total_ytd_yoy:+.1f}% YoY"
    )

    k4.metric(
        "Core Basket",
        f"${core_basket_bn:,.2f}B"
    )

    k5.metric(
        "Coverage",
        f"{coverage_ratio:,.1f}%"
    )

    k6.metric(
        "Growth Explained",
        f"{core_growth_explained:,.1f}%"
    )


    st.caption(
        "Core Basket = 현재 추적 중인 KITA MTI 핵심 산업 합계. "
        "Coverage는 당월 전체 수출 대비 비중, "
        "Growth Explained는 전체 수출 YoY 증가분 중 "
        "Core Basket 증가분이 설명하는 비중입니다."
    )


    # --------------------------------------------------------
    # KPI ROW 2 — SEMI / EX-SEMI
    # --------------------------------------------------------

    st.markdown(
        "### Growth Composition"
    )


    g1, g2, g3, g4 = (
        st.columns(4)
    )


    g1.metric(
        "Total Export YoY",
        f"{latest_total_yoy:+.1f}%"
    )


    g2.metric(
        "Semiconductor YoY",
        (
            f"{semi_yoy:+.1f}%"
            if not pd.isna(semi_yoy)
            else "-"
        ),
        (
            f"{semi_contribution:.1f}% of growth"
            if not pd.isna(semi_contribution)
            else None
        )
    )


    g3.metric(
        "Core ex-Semi YoY",
        (
            f"{core_ex_semi_yoy:+.1f}%"
            if not pd.isna(core_ex_semi_yoy)
            else "-"
        ),
        (
            f"{core_ex_semi_contribution:.1f}% of growth"
            if not pd.isna(core_ex_semi_contribution)
            else None
        )
    )


    g4.metric(
        "Semi Growth Contribution",
        (
            f"{semi_contribution:.1f}%"
            if not pd.isna(semi_contribution)
            else "-"
        )
    )


    st.caption(
        "Core ex-Semi = 현재 KITA Core Basket에서 반도체를 제외한 합계. "
        "같은 MTI 분류체계 안에서 계산됩니다."
    )


    # --------------------------------------------------------
    # RESEARCH INSIGHT
    # --------------------------------------------------------

    if research_insights:

        st.markdown(
            "### Research Takeaways"
        )

        for text in research_insights:

            st.markdown(
                f"- {text}"
            )


    st.divider()


    # --------------------------------------------------------
    # TOTAL EXPORT TREND
    # --------------------------------------------------------

    st.markdown(
        "### Total Export Trend"
    )


    fig_total = px.line(
        total_export.sort_values("기준월"),
        x="기준월",
        y="총수출_bn",
        markers=True
    )


    fig_total.update_layout(
        height=380,
        xaxis_title="",
        yaxis_title="USD bn",
        hovermode="x unified"
    )


    st.plotly_chart(
        fig_total,
        use_container_width=True
    )


    st.divider()


    # --------------------------------------------------------
    # MOMENTUM MAP + STATUS
    # --------------------------------------------------------

    left, right = st.columns(
        [1.45, 1]
    )


    with left:

        st.markdown(
            "### Industry Momentum Map"
        )

        st.caption(
            "X축 = 당월 YoY / Y축 = 당월 YoY − 최근 3M YoY. "
            "우상단은 성장·가속, 우하단은 성장·둔화."
        )


        if not pulse.empty:

            fig_momentum = px.scatter(
                pulse,
                x="YoY_Display",
                y="Momentum_Gap_%p",
                size="수출액_십억달러",
                text="산업",
                hover_data={
                    "산업": True,
                    "KITA_YoY_%": ":.1f",
                    "3M_YoY_%": ":.1f",
                    "Momentum_Gap_%p": ":.1f",
                    "Momentum_국면": True,
                    "YoY_Display": False
                }
            )


            fig_momentum.add_vline(
                x=0,
                line_dash="dash"
            )

            fig_momentum.add_hline(
                y=0,
                line_dash="dash"
            )


            # Quadrant annotations
            fig_momentum.add_annotation(
                x=0.78,
                y=0.95,
                xref="paper",
                yref="paper",
                text="성장·가속",
                showarrow=False
            )

            fig_momentum.add_annotation(
                x=0.78,
                y=0.08,
                xref="paper",
                yref="paper",
                text="성장·둔화",
                showarrow=False
            )

            fig_momentum.add_annotation(
                x=0.08,
                y=0.95,
                xref="paper",
                yref="paper",
                text="부진·회복",
                showarrow=False
            )

            fig_momentum.add_annotation(
                x=0.08,
                y=0.08,
                xref="paper",
                yref="paper",
                text="부진·약화",
                showarrow=False
            )


            fig_momentum.update_traces(
                textposition="top center"
            )


            fig_momentum.update_layout(
                height=520,
                xaxis_title="당월 YoY (%)",
                yaxis_title="Momentum Gap (%p)",
                showlegend=False
            )


            st.plotly_chart(
                fig_momentum,
                use_container_width=True
            )


    with right:

        st.markdown(
            "### Momentum Status"
        )


        if not pulse.empty:

            momentum_display = (
                pulse[
                    [
                        "산업",
                        "KITA_YoY_%",
                        "3M_YoY_%",
                        "Momentum_Gap_%p",
                        "Momentum_국면"
                    ]
                ]
                .sort_values(
                    "Momentum_Gap_%p",
                    ascending=False
                )
            )


            st.dataframe(
                momentum_display,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "산업":
                        "산업",

                    "KITA_YoY_%":
                        st.column_config.NumberColumn(
                            "YoY (%)",
                            format="%.1f"
                        ),

                    "3M_YoY_%":
                        st.column_config.NumberColumn(
                            "3M YoY (%)",
                            format="%.1f"
                        ),

                    "Momentum_Gap_%p":
                        st.column_config.NumberColumn(
                            "Gap (%p)",
                            format="%.1f"
                        ),

                    "Momentum_국면":
                        "국면"
                }
            )


    st.divider()


    # --------------------------------------------------------
    # CONTRIBUTION
    # --------------------------------------------------------

    st.markdown(
        "### Contribution to Total Export Growth"
    )

    st.caption(
        f"전체 수출 YoY 증가액 "
        f"${total_growth_bn:+.2f}B 대비 각 핵심 산업의 증가액 기준"
    )


    if not pulse.empty:

        contribution = (
            pulse[
                [
                    "산업",
                    "증가액_bn",
                    "전체수출증가기여도_%"
                ]
            ]
            .copy()
        )


        contribution[
            "표시값"
        ] = contribution.apply(
            lambda x:
            f"${x['증가액_bn']:+.2f}B | "
            f"{x['전체수출증가기여도_%']:.1f}%",
            axis=1
        )


        contribution = contribution.sort_values(
            "증가액_bn",
            ascending=True
        )


        fig_contribution = px.bar(
            contribution,
            x="증가액_bn",
            y="산업",
            orientation="h",
            text="표시값"
        )


        fig_contribution.update_traces(
            textposition="outside"
        )


        fig_contribution.update_layout(
            height=430,
            xaxis_title="YoY Change, USD bn",
            yaxis_title=""
        )


        st.plotly_chart(
            fig_contribution,
            use_container_width=True
        )


        contribution_table = (
            pulse[
                [
                    "산업",
                    "수출액_십억달러",
                    "KITA_YoY_%",
                    "증가액_bn",
                    "전체수출증가기여도_%",
                    "Momentum_국면"
                ]
            ]
            .sort_values(
                "증가액_bn",
                ascending=False
            )
        )


        st.dataframe(
            contribution_table,
            hide_index=True,
            use_container_width=True,
            column_config={
                "수출액_십억달러":
                    st.column_config.NumberColumn(
                        "수출액 ($bn)",
                        format="%.2f"
                    ),

                "KITA_YoY_%":
                    st.column_config.NumberColumn(
                        "YoY (%)",
                        format="%.1f"
                    ),

                "증가액_bn":
                    st.column_config.NumberColumn(
                        "YoY 증가액 ($bn)",
                        format="%+.2f"
                    ),

                "전체수출증가기여도_%":
                    st.column_config.NumberColumn(
                        "전체 증가 기여도 (%)",
                        format="%.1f"
                    ),

                "Momentum_국면":
                    "Momentum"
            }
        )


    st.divider()


    # --------------------------------------------------------
    # COUNTRY PULSE
    # --------------------------------------------------------

    st.markdown(
        "### Country Pulse"
    )


    if not country_latest_top10.empty:

        country_chart = (
            country_latest_top10
            .sort_values(
                "수출액_십억달러",
                ascending=True
            )
        )


        fig_country = px.bar(
            country_chart,
            x="수출액_십억달러",
            y="국가",
            orientation="h",
            text="수출액_십억달러"
        )


        fig_country.update_traces(
            texttemplate="%{text:.1f}",
            textposition="outside"
        )


        fig_country.update_layout(
            height=430,
            xaxis_title="USD bn",
            yaxis_title=""
        )


        st.plotly_chart(
            fig_country,
            use_container_width=True
        )


# ============================================================
# TAB 2 — INDUSTRY
# ============================================================

with tab_industry:

    st.subheader(
        "Industry View"
    )


    if industry_monthly.empty:

        st.warning(
            "industry_monthly.csv가 없습니다."
        )

    else:

        industries = (
            industry_monthly["산업"]
            .dropna()
            .unique()
            .tolist()
        )


        default_idx = (
            industries.index("반도체 (831)")
            if "반도체 (831)" in industries
            else 0
        )


        selected_industry = st.selectbox(
            "산업 선택",
            industries,
            index=default_idx,
            key="industry_select"
        )


        selected = (
            industry_monthly[
                industry_monthly["산업"]
                ==
                selected_industry
            ]
            .sort_values("기준월")
        )


        latest_row = selected.iloc[-1]


        i1, i2, i3, i4 = st.columns(4)


        i1.metric(
            "당월 수출",
            f"${latest_row['수출액_십억달러']:,.2f}B"
        )

        i2.metric(
            "YoY",
            f"{latest_row['KITA_YoY_%']:+.1f}%"
        )

        i3.metric(
            "MoM",
            f"{latest_row['MoM_%']:+.1f}%"
        )

        i4.metric(
            "3M YoY",
            f"{latest_row['3M_YoY_%']:+.1f}%"
        )


        st.divider()


        fig_industry = px.line(
            selected,
            x="기준월",
            y="수출액_십억달러",
            markers=True
        )


        fig_industry.update_layout(
            height=420,
            xaxis_title="",
            yaxis_title="USD bn",
            hovermode="x unified"
        )


        st.plotly_chart(
            fig_industry,
            use_container_width=True
        )


        st.markdown(
            f"### {latest_year}년 {latest_month}월 산업 비교"
        )


        industry_table = (
            industry_monthly[
                industry_monthly["기준월"]
                ==
                latest_date
            ]
            [
                [
                    "산업",
                    "수출액_십억달러",
                    "KITA_YoY_%",
                    "MoM_%",
                    "3M_YoY_%"
                ]
            ]
            .sort_values(
                "수출액_십억달러",
                ascending=False
            )
        )


        st.dataframe(
            industry_table,
            hide_index=True,
            use_container_width=True
        )


        st.markdown(
            f"### {latest_year} YTD"
        )


        if not industry_ytd.empty:

            st.dataframe(
                industry_ytd,
                hide_index=True,
                use_container_width=True
            )


# ============================================================
# TAB 3 — COUNTRY
# ============================================================

with tab_country:

    st.subheader(
        "Country View"
    )


    if country_monthly.empty:

        st.warning(
            "country_monthly.csv가 없습니다."
        )

    else:

        countries = (
            country_monthly["국가"]
            .dropna()
            .unique()
            .tolist()
        )


        default_idx = (
            countries.index("중국")
            if "중국" in countries
            else 0
        )


        selected_country = st.selectbox(
            "국가 선택",
            countries,
            index=default_idx,
            key="country_select"
        )


        selected = (
            country_monthly[
                country_monthly["국가"]
                ==
                selected_country
            ]
            .sort_values("기준월")
        )


        latest_row = selected.iloc[-1]


        c1, c2, c3 = st.columns(3)


        c1.metric(
            "당월 수출",
            f"${latest_row['수출액_십억달러']:,.2f}B"
        )

        c2.metric(
            "YoY",
            f"{latest_row['YoY_%']:+.1f}%"
        )

        c3.metric(
            "MoM",
            f"{latest_row['MoM_%']:+.1f}%"
        )


        st.markdown(
            f"### 한국 → {selected_country}"
        )


        fig_country_line = px.line(
            selected,
            x="기준월",
            y="수출액_십억달러",
            markers=True
        )


        fig_country_line.update_layout(
            height=420,
            xaxis_title="",
            yaxis_title="USD bn",
            hovermode="x unified"
        )


        st.plotly_chart(
            fig_country_line,
            use_container_width=True
        )


        left, right = st.columns(2)


        with left:

            st.markdown(
                "### Latest Top 10"
            )

            st.dataframe(
                country_latest_top10,
                hide_index=True,
                use_container_width=True
            )


        with right:

            st.markdown(
                "### YTD Top 10"
            )

            st.dataframe(
                country_ytd_top10,
                hide_index=True,
                use_container_width=True
            )


# ============================================================
# TAB 4 — PRODUCT × COUNTRY
# ============================================================

with tab_product_country:

    st.subheader(
        "Product × Country"
    )


    if product_country_monthly.empty:

        st.warning(
            "product_country_multi_monthly.csv가 없습니다."
        )

    else:

        if not product_master.empty:

            products = (
                product_master[
                    "대시보드품목"
                ]
                .dropna()
                .tolist()
            )

        else:

            products = (
                product_country_monthly[
                    "대시보드품목"
                ]
                .dropna()
                .unique()
                .tolist()
            )


        default_idx = (
            products.index("전자집적회로")
            if "전자집적회로" in products
            else 0
        )


        selected_product = st.selectbox(
            "품목 선택",
            products,
            index=default_idx,
            key="product_select"
        )


        product_data = (
            product_country_monthly[
                product_country_monthly[
                    "대시보드품목"
                ]
                ==
                selected_product
            ]
            .sort_values("기준월")
        )


        product_latest_date = (
            product_data[
                "기준월"
            ].max()
        )


        latest_product = (
            product_data[
                product_data["기준월"]
                ==
                product_latest_date
            ]
            .sort_values(
                "수출액_USD",
                ascending=False
            )
        )


        product_total_bn = (
            latest_product[
                "수출액_USD"
            ].sum()
            /
            1_000_000_000
        )


        top_destination = (
            latest_product.iloc[0]
        )


        top_share = (
            top_destination[
                "수출액_USD"
            ]
            /
            latest_product[
                "수출액_USD"
            ].sum()
            *
            100
        )


        p1, p2, p3 = st.columns(3)


        p1.metric(
            "당월 총수출",
            f"${product_total_bn:,.2f}B"
        )

        p2.metric(
            "Top Destination",
            top_destination["국가"]
        )

        p3.metric(
            "Top 국가 비중",
            f"{top_share:,.1f}%"
        )


        st.divider()


        selected_top10 = (
            product_country_latest_top10[
                product_country_latest_top10[
                    "대시보드품목"
                ]
                ==
                selected_product
            ]
        )


        st.markdown(
            f"### {selected_product} Top Destinations"
        )


        if not selected_top10.empty:

            chart = (
                selected_top10
                .sort_values(
                    "수출액_십억달러",
                    ascending=True
                )
            )


            fig_pc_top = px.bar(
                chart,
                x="수출액_십억달러",
                y="국가",
                orientation="h",
                text="수출액_십억달러"
            )


            fig_pc_top.update_traces(
                texttemplate="%{text:.2f}",
                textposition="outside"
            )


            fig_pc_top.update_layout(
                height=440,
                xaxis_title="USD bn",
                yaxis_title=""
            )


            st.plotly_chart(
                fig_pc_top,
                use_container_width=True
            )


        destination_list = (
            product_data[
                "국가"
            ]
            .dropna()
            .unique()
            .tolist()
        )


        default_destination = (
            destination_list.index(
                top_destination["국가"]
            )
            if top_destination["국가"]
            in destination_list
            else 0
        )


        destination = st.selectbox(
            "수출 대상국 선택",
            destination_list,
            index=default_destination,
            key="destination_select"
        )


        destination_data = (
            product_data[
                product_data["국가"]
                ==
                destination
            ]
            .sort_values("기준월")
        )


        latest_destination = (
            destination_data.iloc[-1]
        )


        d1, d2, d3 = st.columns(3)


        d1.metric(
            "대상국 당월 수출",
            f"${latest_destination['수출액_십억달러']:,.2f}B"
        )

        d2.metric(
            "대상국 YoY",
            f"{latest_destination['YoY_%']:+.1f}%"
        )

        d3.metric(
            "대상국 MoM",
            f"{latest_destination['MoM_%']:+.1f}%"
        )


        st.markdown(
            f"### {selected_product} → {destination}"
        )


        fig_pc = px.line(
            destination_data,
            x="기준월",
            y="수출액_십억달러",
            markers=True
        )


        fig_pc.update_layout(
            height=420,
            xaxis_title="",
            yaxis_title="USD bn",
            hovermode="x unified"
        )


        st.plotly_chart(
            fig_pc,
            use_container_width=True
        )


        selected_ytd_top10 = (
            product_country_ytd_top10[
                product_country_ytd_top10[
                    "대시보드품목"
                ]
                ==
                selected_product
            ]
        )


        st.markdown(
            f"### {selected_product} YTD Top 10"
        )


        st.dataframe(
            selected_ytd_top10,
            hide_index=True,
            use_container_width=True
        )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Total / Country / HS: Korea Customs Service | "
    "Industry: Korea International Trade Association "
    "(KITA K-stat, MTI classification)"
)