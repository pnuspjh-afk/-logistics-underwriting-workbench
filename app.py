import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import calculator
import memo_engine
import dd_engine

# 1. Page Config
st.set_page_config(
    page_title="Logistics Underwriting Workbench",
    page_icon="🏗️",
    layout="wide"
)

# 2. Helper Functions
@st.cache_data
def load_sample_assets():
    try:
        # 경로 수정: 실행 위치에 따라 달라질 수 있으므로 유연하게 처리
        df = pd.read_csv("logistics-underwriting-workbench/sample_assets.csv")
        return df
    except Exception:
        try:
            df = pd.read_csv("sample_assets.csv")
            return df
        except Exception:
            return pd.DataFrame()

def format_krw(value, unit="억원"):
    if value is None: return "N/A"
    if unit == "억원":
        return f"{value / 1e8:,.1f} 억원"
    else:
        return f"{value / 1e6:,.0f} 백만원"

def format_pct(value):
    if value is None: return "N/A"
    return f"{value * 100:.1f}%"

# 3. Sidebar Inputs
st.sidebar.header("🛠️ 자산 입력 및 가정")

data_mode = st.sidebar.radio("데이터 입력 모드", ["샘플 데이터", "수기 입력"])
sample_df = load_sample_assets()

if data_mode == "샘플 데이터" and not sample_df.empty:
    asset_list = sample_df['asset_name'].tolist()
    selected_asset_name = st.sidebar.selectbox("대상 자산 선택", asset_list)
    base_data = sample_df[sample_df['asset_name'] == selected_asset_name].iloc[0].to_dict()
else:
    base_data = {
        "asset_name": "신규 프로젝트", "location": "경기도", "purchase_price": 50000000000.0,
        "leasable_area_sqm": 20000.0, "annual_rent_per_sqm": 120000.0, "vacancy_rate": 0.05,
        "opex_ratio": 0.20, "annual_capex": 200000000.0, "ltv": 0.60, "interest_rate": 0.045,
        "hold_period_years": 5, "exit_cap_rate": 0.055, "tenant_concentration": 0.30
    }

with st.sidebar.expander("📌 기본 정보", expanded=True):
    asset_name = st.text_input("자산명", base_data['asset_name'])
    location = st.text_input("위치", base_data['location'])
    purchase_price = st.number_input("매입가 (원)", value=float(base_data['purchase_price']), step=1e8)

with st.sidebar.expander("💰 임대 및 운영 가정", expanded=True):
    leasable_area_sqm = st.number_input("임대면적 (sqm)", value=float(base_data['leasable_area_sqm']))
    annual_rent_per_sqm = st.number_input("연 임대료 (원/sqm)", value=float(base_data['annual_rent_per_sqm']))
    vacancy_rate = st.slider("공실률 (%)", 0, 30, int(base_data['vacancy_rate']*100)) / 100
    opex_ratio = st.slider("운영비율 (%)", 0, 50, int(base_data['opex_ratio']*100)) / 100
    annual_capex = st.number_input("연 Capex (원)", value=float(base_data['annual_capex']))

with st.sidebar.expander("🏦 금융 및 매각 가정", expanded=True):
    ltv = st.slider("LTV (%)", 0, 80, int(base_data['ltv']*100)) / 100
    interest_rate = st.slider("금리 (%)", 0.0, 10.0, float(base_data['interest_rate']*100), step=0.1) / 100
    hold_period_years = st.slider("보유기간 (년)", 3, 10, int(base_data['hold_period_years']))
    exit_cap_rate = st.slider("매각 캡레이트 (%)", 3.0, 10.0, float(base_data['exit_cap_rate']*100), step=0.1) / 100
    tenant_concentration = st.slider("임차인 집중도 (%)", 0, 100, int(base_data.get('tenant_concentration', 0.5)*100)) / 100

inputs = {
    "asset_name": asset_name, "location": location, "purchase_price": purchase_price,
    "leasable_area_sqm": leasable_area_sqm, "annual_rent_per_sqm": annual_rent_per_sqm,
    "vacancy_rate": vacancy_rate, "opex_ratio": opex_ratio, "annual_capex": annual_capex,
    "ltv": ltv, "interest_rate": interest_rate, "hold_period_years": hold_period_years,
    "exit_cap_rate": exit_cap_rate, "tenant_concentration": tenant_concentration
}

scenario_params = {
    "downside": {
        "vacancy_rate": 0.07,
        "annual_rent_per_sqm": -0.07,
        "interest_rate": 0.005,
        "exit_cap_rate": 0.005
    },
    "upside": {
        "vacancy_rate": -0.03,
        "annual_rent_per_sqm": 0.05,
        "exit_cap_rate": -0.003
    }
}

# 5. Analysis Execution
if st.sidebar.button("분석 실행", type="primary"):
    results = calculator.run_underwriting_for_scenarios(inputs, scenario_params)
    base_res = results['base']
    
    # 엔진 호출
    memo_result = memo_engine.generate_investment_memo(results, inputs)
    dd_result = dd_engine.generate_dd_checklist(results, inputs)
    
    st.title(f"🏢 {asset_name} 투자 분석 보고서")
    st.caption(f"Location: {location} | Hold Period: {hold_period_years} years")

    tabs = st.tabs(["📊 Overview", "📑 Underwriting", "📉 Scenarios", "✍️ Investment Memo", "✅ DD Checklist"])

    # --- Tab 1: Overview ---
    with tabs[0]:
        k = base_res['kpis']
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("NOI", format_krw(k['noi']))
        col2.metric("DSCR", f"{k['dscr']}x" if k['dscr'] else "N/A")
        col3.metric("LTV", format_pct(k['ltv']))
        col4.metric("Exit Value", format_krw(k['exit_value']))
        col5.metric("Equity IRR", format_pct(k['equity_irr']))

        if k['dscr'] and k['dscr'] < 1.2:
            st.error(f"⚠️ DSCR 경보: {k['dscr']}x (가이드라인 1.2 미만)")
        elif k['dscr'] and k['dscr'] < 1.3:
            st.warning(f"🔔 DSCR 주의: {k['dscr']}x (가이드라인 1.2 ~ 1.3)")
        
        st.subheader("주요 가정 요약")
        summary_df = pd.DataFrame({
            "항목": ["매입가", "임대면적", "임대료(연)", "공실률", "LTV", "금리", "매각 캡레이트"],
            "값": [
                format_krw(purchase_price), f"{leasable_area_sqm:,.0f} sqm", 
                f"{annual_rent_per_sqm:,.0f} 원/sqm", format_pct(vacancy_rate),
                format_pct(ltv), format_pct(interest_rate), format_pct(exit_cap_rate)
            ]
        })
        st.table(summary_df)

    # --- Tab 2: Underwriting ---
    with tabs[1]:
        st.subheader("상세 수지 분석 (Base Case)")
        rb = base_res['rent_block']
        db = base_res['debt_block']
        eb = base_res['exit_block']
        
        uw_data = [
            {"Category": "Revenue", "Item": "GRI (총잠재임대수입)", "Value": format_krw(rb['gri'])},
            {"Category": "Revenue", "Item": "EGI (유효영업수입)", "Value": format_krw(rb['egi'])},
            {"Category": "Expense", "Item": "Opex (운영비용)", "Value": format_krw(rb['opex'])},
            {"Category": "Expense", "Item": "Capex (자본적지출)", "Value": format_krw(inputs['annual_capex'])},
            {"Category": "Result", "Item": "NOI (순영업소득)", "Value": format_krw(rb['noi'])},
            {"Category": "Debt", "Item": "Loan Amount (대출원금)", "Value": format_krw(db['loan_amount'])},
            {"Category": "Debt", "Item": "Annual Debt Service (연이자)", "Value": format_krw(db['annual_debt_service'])},
            {"Category": "Debt", "Item": "DSCR", "Value": f"{db['dscr']}x" if db['dscr'] else "N/A"},
            {"Category": "Exit", "Item": "Exit Value (매각가)", "Value": format_krw(eb['exit_value'])},
            {"Category": "Exit", "Item": "Equity Investment (자기자본)", "Value": format_krw(eb['equity'])},
            {"Category": "Exit", "Item": "Equity IRR (수익률)", "Value": format_pct(eb['equity_irr'])},
        ]
        st.dataframe(pd.DataFrame(uw_data), use_container_width=True)

    # --- Tab 3: Scenarios ---
    with tabs[2]:
        st.subheader("시나리오별 민감도 분석")
        sc_summary = []
        for s_name in ["base", "downside", "upside"]:
            sk = results[s_name]['kpis']
            sc_summary.append({
                "Scenario": s_name.upper(),
                "NOI (억원)": round(sk['noi']/1e8, 1),
                "DSCR": sk['dscr'],
                "Exit (억원)": round(sk['exit_value']/1e8, 1),
                "IRR (%)": round(sk['equity_irr']*100, 2) if sk['equity_irr'] else 0
            })
        st.table(pd.DataFrame(sc_summary))

        col_c1, col_c2 = st.columns(2)
        with col_c1:
            fig_dscr = go.Figure(data=[
                go.Bar(name='DSCR', x=[s['Scenario'] for s in sc_summary], y=[s['DSCR'] for s in sc_summary])
            ])
            fig_dscr.update_layout(title="Scenario vs DSCR", yaxis_title="Ratio")
            st.plotly_chart(fig_dscr, use_container_width=True)
        
        with col_c2:
            fig_irr = go.Figure(data=[
                go.Bar(name='IRR', x=[s['Scenario'] for s in sc_summary], y=[s['IRR (%)'] for s in sc_summary], marker_color='indianred')
            ])
            fig_irr.update_layout(title="Scenario vs Equity IRR (%)", yaxis_title="Percentage")
            st.plotly_chart(fig_irr, use_container_width=True)

    # --- Tab 4: Investment Memo ---
    with tabs[3]:
        st.subheader("📝 투자 메모 (자동 생성)")
        
        # Recommendation Badge
        rec = memo_result["recommendation"]
        if rec == "Proceed":
            st.success(f"✅ 추천 의견: {rec}")
        elif rec == "Need More DD":
            st.warning(f"⚠️ 추천 의견: {rec}")
        else:
            st.error(f"❌ 추천 의견: {rec}")

        st.info(f"**요약:** {memo_result['summary']}")
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.subheader("🌟 Investment Merits")
            st.markdown(memo_result["investment_merits"])
        with col_m2:
            st.subheader("🚩 Key Risks")
            st.markdown(memo_result["key_risks"])
        
        st.subheader("🔍 Follow-up Points")
        st.markdown(memo_result["follow_up_points"])
        
        st.divider()
        with st.expander("전체 텍스트 복사하기"):
            full_text = f"""[투자 분석 보고서: {asset_name}]
            
1. 요약
{memo_result['summary']}

2. 투자 포인트
{memo_result['investment_merits']}

3. 핵심 리스크
{memo_result['key_risks']}

4. 추가 확인 사항
{memo_result['follow_up_points']}

최종 의견: {rec}
            """
            st.text_area("Copy & Paste", full_text, height=300)

    # --- Tab 5: DD Checklist ---
    with tabs[4]:
        st.subheader("🔍 실사(Due Diligence) 체크리스트")
        
        if dd_result["priority_items"]:
            st.warning("⚠️ 우선 검토 항목")
            for item in dd_result["priority_items"]:
                st.write(f"- {item}")
        
        col_dd1, col_dd2 = st.columns(2)
        
        with col_dd1:
            with st.expander("💰 Financial DD", expanded=True):
                for item in dd_result["financial"]:
                    st.checkbox(item, key=f"fin_{item}")
            
            with st.expander("🏗️ Physical DD", expanded=True):
                for item in dd_result["physical"]:
                    st.checkbox(item, key=f"phy_{item}")

        with col_dd2:
            with st.expander("⚖️ Legal DD", expanded=True):
                for item in dd_result["legal"]:
                    st.checkbox(item, key=f"leg_{item}")
            
            with st.expander("📈 Market DD", expanded=True):
                for item in dd_result["market"]:
                    st.checkbox(item, key=f"mkt_{item}")

else:
    st.info("왼쪽 사이드바에서 가정을 입력하고 '분석 실행' 버튼을 클릭하세요.")
