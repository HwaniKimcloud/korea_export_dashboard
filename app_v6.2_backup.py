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

    "product_country_monthly":
        BASE_DIR / "product_country_multi_monthly.csv",

    "product_country_latest":
        BASE_DIR / "product_country_multi_latest.csv",

    "product_country_ytd":
        BASE_DIR / "product_country_multi_ytd.csv",

    "product_master":
        BASE_DIR / "product_master.csv",
}


# ============================================================
# 2. CSS
# ============================================================

st.markdown(
    """
    <style>

    .block-container {
        padding-top: 3.0rem;
        padding-bottom: 4rem;
        max-width: 1500px;
    }

    html, body, [class*="css"] {
        font-size: 17px;
    }

    h1 {
        font-size: 2.65rem !important;
        font-weight: 760 !important;
        letter-spacing: -0.045em;
    }

    h2 {
        font-size: 1.75rem !important;
        font-weight: 720 !important;
        letter-spacing: -0.03em;
        margin-top: 0.8rem;
    }

    h3 {
        font-size: 1.38rem !important;
        font-weight: 700 !important;
    }

    p, li, label {
        font-size: 1rem !important;
        line-height: 1.65;
    }

    .small-muted {
        color: #747d88;
        font-size: 0.92rem;
        line-height: 1.65;
    }

    .section-note {
        color: #747d88;
        font-size: 0.90rem;
        margin-top: -0.3rem;
        margin-bottom: 0.8rem;
        line-height: 1.6;
    }

    .source-text {
        color: #8c939d;
        font-size: 0.86rem;
        line-height: 1.6;
    }

    div[data-testid="stMetric"] {
        padding-top: 0.15rem;
        padding-bottom: 0.25rem;
    }

    div[data-testid="stMetricLabel"] {
        font-size: 0.94rem !important;
    }

    div[data-testid="stMetricValue"] {
        font-size: 2.15rem !important;
    }

    div[data-testid="stMetricDelta"] {
        font-size: 0.90rem !important;
    }

    div[data-baseweb="select"] {
        font-size: 1rem !important;
    }

    div[data-testid="stDataFrame"] {
        font-size: 0.95rem;
    }

    hr {
        margin-top: 2.2rem;
        margin-bottom: 2.2rem;
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


def fmt_pct(value, digits=1, signed=True):

    if pd.isna(value):
        return "-"

    if signed:

        sign = "+" if value > 0 else ""

        return f"{sign}{value:,.{digits}f}%"

    return f"{value:,.{digits}f}%"


def fmt_pp(value, digits=1):

    if pd.isna(value):
        return "-"

    sign = "+" if value > 0 else ""

    return f"{sign}{value:,.{digits}f}pp"


def safe_div(a, b):

    if (
        pd.isna(a)
        or pd.isna(b)
        or b == 0
    ):
        return np.nan

    return a / b


def normalize_total_df(df):

    if df.empty:
        return df

    df = parse_date_column(
        df.copy()
    )

    date_col = find_column(
        df,
        [
            "기준월",
            "년월",
            "date",
            "Date",
        ],
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

        median_value = df["total_usd"].median()

        if (
            pd.notna(median_value)
            and median_value < 1e9
        ):
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

    df["total_bn"] = (
        df["total_usd"]
        / 1e9
    )

    df = (
        df[
            [
                date_col,
                "total_usd",
                "total_bn",
            ]
        ]
        .dropna(
            subset=[date_col]
        )
        .sort_values(date_col)
        .rename(
            columns={
                date_col: "기준월"
            }
        )
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


def chart_layout(
    fig,
    height=430,
):

    fig.update_layout(
        height=height,
        margin=dict(
            l=10,
            r=20,
            t=30,
            b=20,
        ),
        font=dict(
            size=15,
        ),
        hoverlabel=dict(
            font_size=14,
        ),
        hovermode="x unified",
    )

    fig.update_xaxes(
        tickfont=dict(
            size=13
        )
    )

    fig.update_yaxes(
        tickfont=dict(
            size=13
        )
    )

    return fig


def add_average_line(
    fig,
    df,
    value_col,
    months,
    label,
):

    valid = (
        df[value_col]
        .dropna()
        .tail(months)
    )

    if valid.empty:
        return fig

    avg = valid.mean()

    fig.add_hline(
        y=avg,
        line_dash="dash",
        line_width=2,
        annotation_text=(
            f"{label} Avg  "
            f"{avg:.2f}"
        ),
        annotation_position="top right",
        annotation_font_size=14,
    )

    return fig


# ============================================================
# 4. LOAD
# ============================================================

total = normalize_total_df(
    read_csv_safe(
        FILES["total"]
    )
)

industry_monthly = parse_date_column(
    read_csv_safe(
        FILES[
            "industry_monthly"
        ]
    )
)

industry_ytd_file = read_csv_safe(
    FILES["industry_ytd"]
)

industry_qc_industry = read_csv_safe(
    FILES[
        "industry_qc_industry"
    ]
)

country_monthly = parse_date_column(
    read_csv_safe(
        FILES[
            "country_monthly"
        ]
    )
)

country_ytd_file = read_csv_safe(
    FILES["country_ytd"]
)

product_country_monthly = parse_date_column(
    read_csv_safe(
        FILES[
            "product_country_monthly"
        ]
    )
)

product_country_ytd = read_csv_safe(
    FILES[
        "product_country_ytd"
    ]
)


# ============================================================
# 5. INDUSTRY PREP
# ============================================================

if not industry_monthly.empty:

    industry_monthly[
        "수출액_USD"
    ] = pd.to_numeric(
        industry_monthly[
            "수출액_USD"
        ],
        errors="coerce",
    )

    industry_monthly[
        "수출액_bn"
    ] = (
        industry_monthly[
            "수출액_USD"
        ]
        / 1e9
    )

    industry_monthly = (
        industry_monthly
        .sort_values(
            [
                "산업20",
                "기준월",
            ]
        )
    )

    if (
        "YoY_%"
        not in industry_monthly.columns
    ):

        industry_monthly[
            "YoY_%"
        ] = (
            industry_monthly
            .groupby(
                "산업20"
            )[
                "수출액_USD"
            ]
            .pct_change(12)
            * 100
        )

    if (
        "MoM_%"
        not in industry_monthly.columns
    ):

        industry_monthly[
            "MoM_%"
        ] = (
            industry_monthly
            .groupby(
                "산업20"
            )[
                "수출액_USD"
            ]
            .pct_change()
            * 100
        )

    if (
        "3M_YoY_%"
        not in industry_monthly.columns
    ):

        industry_monthly[
            "3M_YoY_%"
        ] = (
            industry_monthly
            .groupby(
                "산업20"
            )[
                "YoY_%"
            ]
            .transform(
                lambda x:
                x.rolling(
                    3,
                    min_periods=1,
                ).mean()
            )
        )

    industry_monthly[
        "Momentum_Gap_pp"
    ] = (
        industry_monthly[
            "YoY_%"
        ]
        -
        industry_monthly[
            "3M_YoY_%"
        ]
    )


# ============================================================
# 6. LATEST MONTH
# ============================================================

latest_month = None

if not industry_monthly.empty:

    latest_month = (
        industry_monthly[
            "기준월"
        ]
        .max()
    )

elif not total.empty:

    latest_month = (
        total[
            "기준월"
        ]
        .max()
    )


# ============================================================
# 7. YTD TABLE BUILDERS
# ============================================================

def build_industry_ytd(
    df,
    latest_dt,
):

    if (
        df.empty
        or latest_dt is None
    ):
        return pd.DataFrame()

    year = latest_dt.year
    month = latest_dt.month

    current = (
        df[
            (
                df["기준월"].dt.year
                ==
                year
            )
            &
            (
                df["기준월"].dt.month
                <=
                month
            )
        ]
        .groupby(
            "산업20",
            as_index=False,
        )
        .agg(
            현재YTD_USD=(
                "수출액_USD",
                "sum",
            )
        )
    )

    previous = (
        df[
            (
                df["기준월"].dt.year
                ==
                year - 1
            )
            &
            (
                df["기준월"].dt.month
                <=
                month
            )
        ]
        .groupby(
            "산업20",
            as_index=False,
        )
        .agg(
            전년YTD_USD=(
                "수출액_USD",
                "sum",
            )
        )
    )

    result = current.merge(
        previous,
        on="산업20",
        how="left",
    )

    result[
        "현재YTD_bn"
    ] = (
        result[
            "현재YTD_USD"
        ]
        / 1e9
    )

    result[
        "YTD_YoY_%"
    ] = (
        (
            result[
                "현재YTD_USD"
            ]
            /
            result[
                "전년YTD_USD"
            ]
            -
            1
        )
        * 100
    )

    return (
        result
        .sort_values(
            "현재YTD_USD",
            ascending=False,
        )
        .reset_index(drop=True)
    )


def prepare_country_data(df):

    if df.empty:
        return (
            pd.DataFrame(),
            None,
        )

    df = df.copy()

    country_col = find_column(
        df,
        [
            "국가",
            "국가명",
        ],
    )

    usd_col = find_column(
        df,
        [
            "수출액_USD",
        ],
    )

    bn_col = find_column(
        df,
        [
            "수출액_bn",
            "수출액_십억달러",
        ],
    )

    if country_col is None:

        return (
            pd.DataFrame(),
            None,
        )

    if usd_col is not None:

        df[
            "country_usd"
        ] = pd.to_numeric(
            df[usd_col],
            errors="coerce",
        )

        median_value = (
            df[
                "country_usd"
            ]
            .median()
        )

        if (
            pd.notna(median_value)
            and
            median_value < 1e7
        ):
            df[
                "country_usd"
            ] *= 1000

    elif bn_col is not None:

        df[
            "country_usd"
        ] = (
            pd.to_numeric(
                df[bn_col],
                errors="coerce",
            )
            * 1e9
        )

    else:

        return (
            pd.DataFrame(),
            None,
        )

    df[
        "country_bn"
    ] = (
        df[
            "country_usd"
        ]
        / 1e9
    )

    df = df.sort_values(
        [
            country_col,
            "기준월",
        ]
    )

    if "YoY_%" not in df.columns:

        df[
            "YoY_%"
        ] = (
            df
            .groupby(
                country_col
            )[
                "country_usd"
            ]
            .pct_change(12)
            * 100
        )

    if "MoM_%" not in df.columns:

        df[
            "MoM_%"
        ] = (
            df
            .groupby(
                country_col
            )[
                "country_usd"
            ]
            .pct_change()
            * 100
        )

    return (
        df,
        country_col,
    )


def build_country_ytd(
    df,
    country_col,
    latest_dt,
):

    if (
        df.empty
        or country_col is None
        or latest_dt is None
    ):
        return pd.DataFrame()

    year = latest_dt.year
    month = latest_dt.month

    current = (
        df[
            (
                df[
                    "기준월"
                ].dt.year
                ==
                year
            )
            &
            (
                df[
                    "기준월"
                ].dt.month
                <=
                month
            )
        ]
        .groupby(
            country_col,
            as_index=False,
        )
        .agg(
            현재YTD_USD=(
                "country_usd",
                "sum",
            )
        )
    )

    previous = (
        df[
            (
                df[
                    "기준월"
                ].dt.year
                ==
                year - 1
            )
            &
            (
                df[
                    "기준월"
                ].dt.month
                <=
                month
            )
        ]
        .groupby(
            country_col,
            as_index=False,
        )
        .agg(
            전년YTD_USD=(
                "country_usd",
                "sum",
            )
        )
    )

    result = current.merge(
        previous,
        on=country_col,
        how="left",
    )

    result[
        "현재YTD_bn"
    ] = (
        result[
            "현재YTD_USD"
        ]
        / 1e9
    )

    result[
        "YTD_YoY_%"
    ] = (
        (
            result[
                "현재YTD_USD"
            ]
            /
            result[
                "전년YTD_USD"
            ]
            -
            1
        )
        * 100
    )

    return (
        result
        .sort_values(
            "현재YTD_USD",
            ascending=False,
        )
        .reset_index(drop=True)
    )


industry_ytd = build_industry_ytd(
    industry_monthly,
    latest_month,
)

country_monthly, country_col = (
    prepare_country_data(
        country_monthly
    )
)

country_ytd = build_country_ytd(
    country_monthly,
    country_col,
    latest_month,
)


# ============================================================
# 8. HEADER
# ============================================================

st.title(
    "Korea Export Monitor"
)

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
# 9. TABS
# ============================================================

(
    tab_overview,
    tab_industry,
    tab_country,
    tab_product_country,
) = st.tabs(
    [
        "Overview",
        "Industry",
        "Country",
        "Product × Country",
    ]
)


# ============================================================
# 10. OVERVIEW
# ============================================================

with tab_overview:

    st.header(
        "Korea Export Pulse"
    )

    total_latest = None
    total_prev_year = None

    if not total.empty:

        total_latest = (
            total.iloc[-1]
        )

        current_date = (
            total_latest[
                "기준월"
            ]
        )

        prev_year_df = (
            total[
                total[
                    "기준월"
                ]
                ==
                (
                    current_date
                    -
                    pd.DateOffset(
                        years=1
                    )
                )
            ]
        )

        if not prev_year_df.empty:

            total_prev_year = (
                prev_year_df.iloc[-1]
            )


    industry_current = (
        pd.DataFrame()
    )

    industry_previous_year = (
        pd.DataFrame()
    )

    if (
        latest_month is not None
        and
        not industry_monthly.empty
    ):

        industry_current = (
            industry_monthly[
                industry_monthly[
                    "기준월"
                ]
                ==
                latest_month
            ]
            .copy()
        )

        industry_previous_year = (
            industry_monthly[
                industry_monthly[
                    "기준월"
                ]
                ==
                (
                    latest_month
                    -
                    pd.DateOffset(
                        years=1
                    )
                )
            ]
            .copy()
        )


    industry20_latest_usd = (
        industry_current[
            "수출액_USD"
        ]
        .sum()
        if not industry_current.empty
        else np.nan
    )

    industry20_latest_bn = (
        industry20_latest_usd
        / 1e9
        if pd.notna(
            industry20_latest_usd
        )
        else np.nan
    )

    total_latest_usd = (
        total_latest[
            "total_usd"
        ]
        if total_latest is not None
        else np.nan
    )

    total_latest_bn = (
        total_latest[
            "total_bn"
        ]
        if total_latest is not None
        else np.nan
    )

    total_yoy = (
        total_latest[
            "YoY_%"
        ]
        if total_latest is not None
        else np.nan
    )

    total_mom = (
        total_latest[
            "MoM_%"
        ]
        if total_latest is not None
        else np.nan
    )

    coverage = (
        safe_div(
            industry20_latest_usd,
            total_latest_usd,
        )
        * 100
    )


    # --------------------------------------------------------
    # Total YTD
    # --------------------------------------------------------

    ytd_current = np.nan
    ytd_previous = np.nan
    ytd_yoy = np.nan

    if (
        latest_month is not None
        and
        not total.empty
    ):

        year = latest_month.year
        month = latest_month.month

        ytd_current = (
            total[
                (
                    total[
                        "기준월"
                    ].dt.year
                    ==
                    year
                )
                &
                (
                    total[
                        "기준월"
                    ].dt.month
                    <=
                    month
                )
            ][
                "total_usd"
            ]
            .sum()
        )

        ytd_previous = (
            total[
                (
                    total[
                        "기준월"
                    ].dt.year
                    ==
                    year - 1
                )
                &
                (
                    total[
                        "기준월"
                    ].dt.month
                    <=
                    month
                )
            ][
                "total_usd"
            ]
            .sum()
        )

        if ytd_previous != 0:

            ytd_yoy = (
                (
                    ytd_current
                    /
                    ytd_previous
                    -
                    1
                )
                * 100
            )


    # --------------------------------------------------------
    # Growth Explained
    # --------------------------------------------------------

    total_growth_usd = np.nan
    industry_growth_usd = np.nan
    growth_explained = np.nan

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
            total_latest[
                "total_usd"
            ]
            -
            total_prev_year[
                "total_usd"
            ]
        )

        industry_growth_usd = (
            industry_current[
                "수출액_USD"
            ].sum()
            -
            industry_previous_year[
                "수출액_USD"
            ].sum()
        )

        growth_explained = (
            safe_div(
                industry_growth_usd,
                total_growth_usd,
            )
            * 100
        )


    # --------------------------------------------------------
    # KPI ROW
    # --------------------------------------------------------

    (
        k1,
        k2,
        k3,
        k4,
        k5,
        k6,
    ) = st.columns(6)

    k1.metric(
        "한국 총수출",
        fmt_bn(
            total_latest_bn
        ),
        (
            fmt_pct(
                total_yoy
            )
            +
            " YoY"
        ),
    )

    k2.metric(
        "MoM",
        fmt_pct(
            total_mom
        ),
    )

    k3.metric(
        f"{latest_month.year} YTD",
        fmt_bn(
            ytd_current
            / 1e9,
            1,
        ),
        (
            fmt_pct(
                ytd_yoy
            )
            +
            " YoY"
        ),
    )

    k4.metric(
        "20 Industry Basket",
        fmt_bn(
            industry20_latest_bn
        ),
    )

    k5.metric(
        "Coverage",
        fmt_pct(
            coverage,
            signed=False,
        ),
    )

    k6.metric(
        "Growth Explained",
        fmt_pct(
            growth_explained,
            signed=False,
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

    st.subheader(
        "Growth Composition"
    )

    semi_yoy = np.nan
    ex_semi_yoy = np.nan
    semi_growth_contribution = np.nan

    if (
        not industry_current.empty
        and
        not industry_previous_year.empty
    ):

        semi_now = (
            industry_current[
                industry_current[
                    "산업20"
                ]
                ==
                "반도체"
            ]
        )

        semi_prev = (
            industry_previous_year[
                industry_previous_year[
                    "산업20"
                ]
                ==
                "반도체"
            ]
        )

        if (
            not semi_now.empty
            and
            not semi_prev.empty
        ):

            semi_now_value = (
                semi_now[
                    "수출액_USD"
                ]
                .sum()
            )

            semi_prev_value = (
                semi_prev[
                    "수출액_USD"
                ]
                .sum()
            )

            semi_yoy = (
                (
                    semi_now_value
                    /
                    semi_prev_value
                    -
                    1
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
                        -
                        1
                    )
                    * 100
                )


    (
        g1,
        g2,
        g3,
        g4,
    ) = st.columns(4)

    g1.metric(
        "Total Export YoY",
        fmt_pct(
            total_yoy
        ),
    )

    g2.metric(
        "Semiconductor YoY",
        fmt_pct(
            semi_yoy
        ),
    )

    g3.metric(
        "Core ex-Semi YoY",
        fmt_pct(
            ex_semi_yoy
        ),
    )

    g4.metric(
        "Semi Growth Contribution",
        fmt_pct(
            semi_growth_contribution,
            signed=False,
        ),
    )


    # ========================================================
    # RESEARCH TAKEAWAYS
    # ========================================================

    st.subheader(
        "Research Takeaways"
    )

    takeaway_lines = []

    if (
        not industry_current.empty
        and
        not industry_previous_year.empty
    ):

        contrib = (
            industry_current[
                [
                    "산업20",
                    "수출액_USD",
                    "YoY_%",
                    "3M_YoY_%",
                    "Momentum_Gap_pp",
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

        semi_row = (
            contrib[
                contrib[
                    "산업20"
                ]
                ==
                "반도체"
            ]
        )

        if not semi_row.empty:

            row = semi_row.iloc[0]

            semi_share = (
                safe_div(
                    row[
                        "증감액_USD"
                    ],
                    total_growth_usd,
                )
                * 100
            )

            takeaway_lines.append(
                f"**반도체가 전체 수출 증가분의 "
                f"{semi_share:.1f}%를 설명**하고 있으나, "
                f"비반도체 20대 산업도 YoY "
                f"{ex_semi_yoy:+.1f}% 증가. "
                f"수출 회복이 반도체 단일 품목에만 "
                f"의존하는 국면은 아닌 것으로 판단됨."
            )

        acceleration = (
            contrib
            .dropna(
                subset=[
                    "Momentum_Gap_pp"
                ]
            )
            .sort_values(
                "Momentum_Gap_pp",
                ascending=False,
            )
        )

        if not acceleration.empty:

            row = (
                acceleration.iloc[0]
            )

            takeaway_lines.append(
                f"모멘텀 측면에서는 **{row['산업20']}**가 "
                f"YoY {row['YoY_%']:+.1f}%를 기록한 가운데 "
                f"최근 3개월 평균 대비 "
                f"{row['Momentum_Gap_pp']:+.1f}pp 가속."
            )

        slowdown = (
            contrib
            .dropna(
                subset=[
                    "Momentum_Gap_pp"
                ]
            )
            .sort_values(
                "Momentum_Gap_pp",
                ascending=True,
            )
        )

        if not slowdown.empty:

            row = (
                slowdown.iloc[0]
            )

            takeaway_lines.append(
                f"반면 **{row['산업20']}**는 YoY "
                f"{row['YoY_%']:+.1f}%에도 최근 3개월 평균 대비 "
                f"{row['Momentum_Gap_pp']:+.1f}pp 둔화. "
                f"헤드라인 성장률보다 모멘텀 방향 변화에 주목할 필요."
            )

    for line in takeaway_lines[:3]:

        st.markdown(
            f"- {line}"
        )


    st.divider()


    # ========================================================
    # TOTAL EXPORT TREND — HISTOGRAM
    # ========================================================

    st.subheader(
        "Total Export Trend"
    )

    avg_mode_total = st.radio(
        "Average",
        [
            "3M Average",
            "12M Average",
        ],
        horizontal=True,
        key="total_avg",
    )

    if not total.empty:

        fig_total = px.bar(
            total,
            x="기준월",
            y="total_bn",
            labels={
                "기준월": "",
                "total_bn":
                    "USD bn",
            },
        )

        if (
            avg_mode_total
            ==
            "3M Average"
        ):

            fig_total = add_average_line(
                fig_total,
                total,
                "total_bn",
                3,
                "3M",
            )

        else:

            fig_total = add_average_line(
                fig_total,
                total,
                "total_bn",
                12,
                "12M",
            )

        fig_total = chart_layout(
            fig_total,
            height=430,
        )

        st.plotly_chart(
            fig_total,
            width="stretch",
        )


    st.divider()


    # ========================================================
    # MOMENTUM MAP
    # ========================================================

    st.subheader(
        "Industry Momentum Map"
    )

    st.markdown(
        """
        <div class="section-note">
        X축 = 당월 YoY /
        Y축 = 당월 YoY - 최근 3개월 YoY 평균.
        우상단은 성장률이 높고 최근 모멘텀도 가속되는 산업.
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns(
        [
            1.4,
            1,
        ]
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

            map_mode = st.radio(
                "View",
                [
                    "Focus View",
                    "Full Range",
                ],
                horizontal=True,
                key="momentum_view",
            )

            label_names = set()

            label_names.update(
                momentum_df
                .nlargest(
                    5,
                    "수출액_bn",
                )[
                    "산업20"
                ]
                .tolist()
            )

            label_names.update(
                momentum_df
                .nlargest(
                    3,
                    "YoY_%",
                )[
                    "산업20"
                ]
                .tolist()
            )

            label_names.update(
                momentum_df
                .nlargest(
                    3,
                    "Momentum_Gap_pp",
                )[
                    "산업20"
                ]
                .tolist()
            )

            label_names.update(
                momentum_df
                .nsmallest(
                    3,
                    "Momentum_Gap_pp",
                )[
                    "산업20"
                ]
                .tolist()
            )

            momentum_df[
                "라벨"
            ] = np.where(
                momentum_df[
                    "산업20"
                ].isin(
                    label_names
                ),
                momentum_df[
                    "산업20"
                ],
                "",
            )

            fig_momentum = px.scatter(
                momentum_df,
                x="YoY_%",
                y="Momentum_Gap_pp",
                size="수출액_bn",
                text="라벨",
                hover_name="산업20",
                hover_data={
                    "YoY_%": ":.1f",
                    "3M_YoY_%": ":.1f",
                    "Momentum_Gap_pp":
                        ":.1f",
                    "수출액_bn":
                        ":.2f",
                    "라벨":
                        False,
                },
                labels={
                    "YoY_%":
                        "당월 YoY (%)",
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
                textposition="top center",
                textfont=dict(
                    size=13,
                ),
            )

            if (
                map_mode
                ==
                "Focus View"
            ):

                focus = (
                    momentum_df[
                        momentum_df[
                            "YoY_%"
                        ]
                        .between(
                            -50,
                            100,
                        )
                    ]
                )

                if not focus.empty:

                    y_abs = max(
                        20,
                        float(
                            focus[
                                "Momentum_Gap_pp"
                            ]
                            .abs()
                            .max()
                        )
                        * 1.15,
                    )

                else:

                    y_abs = 30

                fig_momentum.update_xaxes(
                    range=[
                        -50,
                        100,
                    ]
                )

                fig_momentum.update_yaxes(
                    range=[
                        -y_abs,
                        y_abs,
                    ]
                )

            fig_momentum = chart_layout(
                fig_momentum,
                height=580,
            )

            st.plotly_chart(
                fig_momentum,
                width="stretch",
            )


    with right:

        st.subheader(
            "Momentum Status"
        )

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

            status[
                "Status"
            ] = np.select(
                [
                    (
                        status[
                            "YoY_%"
                        ]
                        > 0
                    )
                    &
                    (
                        status[
                            "Momentum_Gap_pp"
                        ]
                        > 0
                    ),

                    (
                        status[
                            "YoY_%"
                        ]
                        > 0
                    )
                    &
                    (
                        status[
                            "Momentum_Gap_pp"
                        ]
                        <= 0
                    ),

                    (
                        status[
                            "YoY_%"
                        ]
                        <= 0
                    )
                    &
                    (
                        status[
                            "Momentum_Gap_pp"
                        ]
                        > 0
                    ),
                ],
                [
                    "Expansion",
                    "Growth / Slowing",
                    "Recovery",
                ],
                default="Contraction",
            )

            status.columns = [
                "산업",
                "YoY (%)",
                "3M YoY (%)",
                "Gap (pp)",
                "Status",
            ]

            st.dataframe(
                status,
                width="stretch",
                hide_index=True,
                height=570,
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
    # CONTRIBUTION / EXPORT STRUCTURE
    # ========================================================

    st.subheader(
        "Export Growth & Industry Contribution"
    )

    st.markdown(
        """
        <div class="section-note">
        막대는 산업별 수출액 규모, 라벨은 전년대비 성장률.
        Latest Month / YTD 전환을 통해 단월 모멘텀과 누적 수출 구조를 비교.
        </div>
        """,
        unsafe_allow_html=True,
    )

    contribution_mode = st.radio(
        "Period",
        [
            f"Latest Month ({latest_month.strftime('%y.%m')})",
            "YTD",
        ],
        horizontal=True,
        key="contribution_mode",
    )


    if (
        contribution_mode
        ==
        f"Latest Month ({latest_month.strftime('%y.%m')})"
    ):

        contribution_view = (
            industry_current[
                [
                    "산업20",
                    "수출액_bn",
                    "YoY_%",
                ]
            ]
            .copy()
        )

        contribution_view[
            "성장률표시"
        ] = (
            contribution_view[
                "YoY_%"
            ]
            .map(
                lambda x:
                f"{x:+.1f}%"
                if pd.notna(x)
                else "-"
            )
        )

    else:

        contribution_view = (
            industry_ytd[
                [
                    "산업20",
                    "현재YTD_bn",
                    "YTD_YoY_%",
                ]
            ]
            .copy()
            .rename(
                columns={
                    "현재YTD_bn":
                        "수출액_bn",
                    "YTD_YoY_%":
                        "YoY_%",
                }
            )
        )

        contribution_view[
            "성장률표시"
        ] = (
            contribution_view[
                "YoY_%"
            ]
            .map(
                lambda x:
                f"{x:+.1f}%"
                if pd.notna(x)
                else "-"
            )
        )


    contribution_view = (
        contribution_view
        .sort_values(
            "수출액_bn",
            ascending=True,
        )
    )

    fig_contribution = go.Figure()

    fig_contribution.add_trace(
        go.Bar(
            x=contribution_view[
                "수출액_bn"
            ],
            y=contribution_view[
                "산업20"
            ],
            orientation="h",
            text=contribution_view[
                "성장률표시"
            ],
            textposition="outside",
            customdata=np.stack(
                [
                    contribution_view[
                        "YoY_%"
                    ]
                ],
                axis=-1,
            ),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Export: $%{x:.2f}B<br>"
                "YoY: %{customdata[0]:+.1f}%"
                "<extra></extra>"
            ),
        )
    )

    fig_contribution.update_layout(
        xaxis_title="Export (USD bn)",
        yaxis_title="",
        height=650,
        margin=dict(
            l=20,
            r=80,
            t=20,
            b=20,
        ),
        font=dict(
            size=15,
        ),
    )

    st.plotly_chart(
        fig_contribution,
        width="stretch",
    )


# ============================================================
# 11. INDUSTRY TAB
# ============================================================

with tab_industry:

    st.header(
        "20 Major Export Industries"
    )

    if industry_monthly.empty:

        st.warning(
            "industry20_monthly.csv를 찾을 수 없습니다."
        )

    else:

        # ----------------------------------------------------
        # YTD 기준 정렬
        # ----------------------------------------------------

        industry_order = (
            industry_ytd[
                "산업20"
            ]
            .tolist()
        )

        ytd_lookup = (
            industry_ytd
            .set_index(
                "산업20"
            )[
                "현재YTD_bn"
            ]
            .to_dict()
        )

        industry_labels = [
            (
                f"{name}  "
                f"(${ytd_lookup.get(name, np.nan):.2f}B YTD)"
            )
            for name in industry_order
        ]

        label_to_industry = {
            label: name
            for label, name
            in zip(
                industry_labels,
                industry_order,
            )
        }

        selected_industry_label = (
            st.selectbox(
                "산업 선택 · YTD 수출액 순",
                industry_labels,
            )
        )

        selected_industry = (
            label_to_industry[
                selected_industry_label
            ]
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

        latest_ind = (
            df_ind.iloc[-1]
        )

        ytd_row = (
            industry_ytd[
                industry_ytd[
                    "산업20"
                ]
                ==
                selected_industry
            ]
        )

        (
            c1,
            c2,
            c3,
            c4,
            c5,
            c6,
        ) = st.columns(6)

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

        c5.metric(
            "Momentum Gap",
            fmt_pp(
                latest_ind[
                    "Momentum_Gap_pp"
                ]
            ),
        )

        if not ytd_row.empty:

            c6.metric(
                "YTD",
                fmt_bn(
                    ytd_row.iloc[0][
                        "현재YTD_bn"
                    ]
                ),
                (
                    fmt_pct(
                        ytd_row.iloc[0][
                            "YTD_YoY_%"
                        ]
                    )
                    +
                    " YoY"
                ),
            )


        gap_value = (
            latest_ind[
                "Momentum_Gap_pp"
            ]
        )

        yoy_value = (
            latest_ind[
                "YoY_%"
            ]
        )

        if (
            pd.notna(yoy_value)
            and
            pd.notna(gap_value)
        ):

            if (
                yoy_value > 0
                and gap_value > 0
            ):

                status_text = (
                    "성장률이 플러스인 가운데 최근 3개월 평균보다 "
                    "높아 **모멘텀 가속 구간**으로 판단됨."
                )

            elif (
                yoy_value > 0
                and gap_value <= 0
            ):

                status_text = (
                    "전년동월 대비 성장세는 유지되고 있으나 최근 "
                    "3개월 평균을 하회해 **성장 속도는 둔화**되는 모습."
                )

            elif (
                yoy_value <= 0
                and gap_value > 0
            ):

                status_text = (
                    "전년동월 대비 감소세이나 최근 3개월 평균보다 "
                    "개선돼 **회복 국면 진입 가능성**에 주목."
                )

            else:

                status_text = (
                    "전년동월 대비 감소와 모멘텀 둔화가 동시에 "
                    "나타나는 **수축 구간**으로 판단됨."
                )

            st.markdown(
                f"""
                <div class="small-muted">
                <b>Momentum Read:</b>
                {status_text}
                </div>
                """,
                unsafe_allow_html=True,
            )


        st.divider()


        # ----------------------------------------------------
        # HISTOGRAM + AVG
        # ----------------------------------------------------

        st.subheader(
            f"{selected_industry} Monthly Export"
        )

        avg_mode_industry = st.radio(
            "Average",
            [
                "3M Average",
                "12M Average",
            ],
            horizontal=True,
            key="industry_avg",
        )

        fig_ind = px.bar(
            df_ind,
            x="기준월",
            y="수출액_bn",
            labels={
                "기준월":
                    "",
                "수출액_bn":
                    "USD bn",
            },
        )

        if (
            avg_mode_industry
            ==
            "3M Average"
        ):

            fig_ind = add_average_line(
                fig_ind,
                df_ind,
                "수출액_bn",
                3,
                "3M",
            )

        else:

            fig_ind = add_average_line(
                fig_ind,
                df_ind,
                "수출액_bn",
                12,
                "12M",
            )

        fig_ind = chart_layout(
            fig_ind,
            height=450,
        )

        st.plotly_chart(
            fig_ind,
            width="stretch",
        )


        # ----------------------------------------------------
        # Growth Momentum
        # ----------------------------------------------------

        st.subheader(
            "Growth Momentum"
        )

        momentum_long = (
            df_ind[
                [
                    "기준월",
                    "YoY_%",
                    "3M_YoY_%",
                    "MoM_%",
                ]
            ]
            .melt(
                id_vars="기준월",
                var_name="지표",
                value_name="%",
            )
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

        fig_growth = chart_layout(
            fig_growth,
            height=430,
        )

        st.plotly_chart(
            fig_growth,
            width="stretch",
        )


        # ----------------------------------------------------
        # YTD Ranking
        # ----------------------------------------------------

        st.subheader(
            "Industry YTD Ranking"
        )

        ranking_ind = (
            industry_ytd[
                [
                    "산업20",
                    "현재YTD_bn",
                    "YTD_YoY_%",
                ]
            ]
            .copy()
        )

        ranking_ind.index += 1

        st.dataframe(
            ranking_ind,
            width="stretch",
            column_config={
                "현재YTD_bn":
                    st.column_config.NumberColumn(
                        "YTD Export (USD bn)",
                        format="%.2f",
                    ),

                "YTD_YoY_%":
                    st.column_config.NumberColumn(
                        "YTD YoY (%)",
                        format="%.1f",
                    ),
            },
        )


# ============================================================
# 12. COUNTRY TAB
# ============================================================

with tab_country:

    st.header(
        "Country Export Monitor"
    )

    if (
        country_monthly.empty
        or country_col is None
    ):

        st.warning(
            "country_monthly.csv 데이터를 확인해 주세요."
        )

    else:

        st.markdown(
            """
            <div class="section-note">
            국가 선택 목록은 YTD 수출액 기준 내림차순.
            검색어를 입력하면 국가명이 필터링됩니다.
            </div>
            """,
            unsafe_allow_html=True,
        )

        search_country = st.text_input(
            "국가 검색",
            placeholder=(
                "예: 미국, 중국, 베트남, Germany..."
            ),
        )

        country_order = (
            country_ytd[
                country_col
            ]
            .astype(str)
            .tolist()
        )

        if search_country.strip():

            search_key = (
                search_country
                .strip()
                .lower()
            )

            filtered_countries = [
                x
                for x in country_order
                if search_key
                in str(x).lower()
            ]

        else:

            filtered_countries = (
                country_order
            )

        if not filtered_countries:

            st.warning(
                "검색 조건에 해당하는 국가가 없습니다."
            )

        else:

            ytd_country_lookup = (
                country_ytd
                .set_index(
                    country_col
                )[
                    "현재YTD_bn"
                ]
                .to_dict()
            )

            country_labels = [
                (
                    f"{name}  "
                    f"(${ytd_country_lookup.get(name, np.nan):.2f}B YTD)"
                )
                for name in filtered_countries
            ]

            label_to_country = {
                label: name
                for label, name
                in zip(
                    country_labels,
                    filtered_countries,
                )
            }

            selected_country_label = (
                st.selectbox(
                    "수출 대상국 선택 · YTD 수출액 순",
                    country_labels,
                )
            )

            selected_country = (
                label_to_country[
                    selected_country_label
                ]
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
                    "기준월"
                )
                .copy()
            )

            latest_country = (
                df_country.iloc[-1]
            )

            ytd_country_row = (
                country_ytd[
                    country_ytd[
                        country_col
                    ]
                    ==
                    selected_country
                ]
            )

            (
                cc1,
                cc2,
                cc3,
                cc4,
            ) = st.columns(4)

            cc1.metric(
                "당월 수출",
                fmt_bn(
                    latest_country[
                        "country_bn"
                    ]
                ),
            )

            cc2.metric(
                "YoY",
                fmt_pct(
                    latest_country[
                        "YoY_%"
                    ]
                ),
            )

            cc3.metric(
                "MoM",
                fmt_pct(
                    latest_country[
                        "MoM_%"
                    ]
                ),
            )

            if not ytd_country_row.empty:

                cc4.metric(
                    "YTD",
                    fmt_bn(
                        ytd_country_row.iloc[0][
                            "현재YTD_bn"
                        ]
                    ),
                    (
                        fmt_pct(
                            ytd_country_row.iloc[0][
                                "YTD_YoY_%"
                            ]
                        )
                        +
                        " YoY"
                    ),
                )


            st.divider()


            st.subheader(
                f"{selected_country} Monthly Export"
            )

            avg_mode_country = st.radio(
                "Average",
                [
                    "3M Average",
                    "12M Average",
                ],
                horizontal=True,
                key="country_avg",
            )

            fig_country = px.bar(
                df_country,
                x="기준월",
                y="country_bn",
                labels={
                    "기준월":
                        "",
                    "country_bn":
                        "USD bn",
                },
            )

            if (
                avg_mode_country
                ==
                "3M Average"
            ):

                fig_country = (
                    add_average_line(
                        fig_country,
                        df_country,
                        "country_bn",
                        3,
                        "3M",
                    )
                )

            else:

                fig_country = (
                    add_average_line(
                        fig_country,
                        df_country,
                        "country_bn",
                        12,
                        "12M",
                    )
                )

            fig_country = chart_layout(
                fig_country,
                height=450,
            )

            st.plotly_chart(
                fig_country,
                width="stretch",
            )


            st.subheader(
                "Country YTD Ranking"
            )

            ranking_country = (
                country_ytd[
                    [
                        country_col,
                        "현재YTD_bn",
                        "YTD_YoY_%",
                    ]
                ]
                .copy()
            )

            ranking_country.index += 1

            st.dataframe(
                ranking_country,
                width="stretch",
                height=520,
                column_config={
                    "현재YTD_bn":
                        st.column_config.NumberColumn(
                            "YTD Export (USD bn)",
                            format="%.2f",
                        ),

                    "YTD_YoY_%":
                        st.column_config.NumberColumn(
                            "YTD YoY (%)",
                            format="%.1f",
                        ),
                },
            )


# ============================================================
# 13. PRODUCT × COUNTRY
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

        pc_country_col = find_column(
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
            and usd_col is not None
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

            bn_col = (
                "수출액_bn"
            )

        if (
            product_col is None
            or
            pc_country_col is None
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

            selected_product = (
                st.selectbox(
                    "품목 선택",
                    products,
                )
            )

            product_data = (
                product_country_monthly[
                    product_country_monthly[
                        product_col
                    ]
                    ==
                    selected_product
                ]
                .copy()
            )

            countries = sorted(
                product_data[
                    pc_country_col
                ]
                .dropna()
                .unique()
            )

            selected_pc_country = (
                st.selectbox(
                    "대상국 선택",
                    countries,
                )
            )

            df_pc = (
                product_data[
                    product_data[
                        pc_country_col
                    ]
                    ==
                    selected_pc_country
                ]
                .sort_values(
                    date_col
                )
                .copy()
            )

            latest_pc = (
                df_pc.iloc[-1]
            )

            yoy_col = find_column(
                df_pc,
                [
                    "YoY_%"
                ],
            )

            mom_col = find_column(
                df_pc,
                [
                    "MoM_%"
                ],
            )

            (
                pc1,
                pc2,
                pc3,
            ) = st.columns(3)

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

            fig_pc = px.bar(
                df_pc,
                x=date_col,
                y=bn_col,
                labels={
                    date_col:
                        "",
                    bn_col:
                        "USD bn",
                },
            )

            fig_pc = chart_layout(
                fig_pc,
                height=450,
            )

            st.plotly_chart(
                fig_pc,
                width="stretch",
            )


# ============================================================
# 14. FOOTER
# ============================================================

st.divider()

st.markdown(
    """
    <div class="source-text">
    Data: Korea Customs Service, KITA K-stat.<br>
    Industry classification: Official 2026 MTI-HSK linkage table.<br>
    Production QC: Master Structure / Monthly Integrity /
    KITA Independent Reconciliation / Universe Coverage /
    Mapping Coverage = PASS.
    </div>
    """,
    unsafe_allow_html=True,
)