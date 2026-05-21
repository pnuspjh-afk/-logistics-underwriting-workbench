import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import calculator
import memo_engine
import dd_engine
import reporting_engine
import io
import json
import os

# 1. Page Config
st.set_page_config(
    page_title="Logistics Underwriting Workbench",
    page_icon="🏗️",
    layout="wide"
)

# 2. Storage Logic
DATA_FILE = "saved_scenarios.json"

def load_stored_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except: return {}
    return {}

def save_stored_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

if 'saved_scenarios' not in st.session_state:
    st.session_state.saved_scenarios = load_stored_data()

# 3. Helper Functions
@st.cache_data
def load_sample_assets():
    try:
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

# 4. Sidebar Inputs
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
    
    st.markdown("---")
    st.caption("상세 운영비용(Opex)")
    property_tax_ratio = st.number_input("재산세율 (매입가 대비 %)", value=0.15, step=0.01) / 100
    opex_per_sqm = st.number_input("보험/PM비 (원/sqm)", value=3000, step=100)
    other_opex_ratio = st.slider("기타운영비 (EGI 대비 %)", 0, 10, 2) / 100
    annual_capex = st.number_input("연 Capex (원)", value=float(base_data['annual_capex']))

with st.sidebar.expander("🏦 금융 및 매각 가정", expanded=True):
    ltv = st.slider("LTV (%)", 0, 80, int(base_data['ltv']*100)) / 100
    interest_rate = st.slider("금리 (%)", 0.0, 10.0, float(base_data['interest_rate']*100), step=0.1) / 100
    hold_period_years = st.slider("보유기간 (년)", 3, 10, int(base_data['hold_period_years']))
    exit_cap_rate = st.slider("매각 캡레이트 (%)", 3.0, 10.0, float(base_data['exit_cap_rate']*100), step=0.1) / 100
    tenant_concentration = st.slider("임차인 집중도 (%)", 0, 100, int(base_data.get('tenant_concentration', 0.5)*100)) / 100

st.sidebar.header("☢️ Stress Test 설정")
with st.sidebar.expander("커스텀 스트레스 시나리오"):
    st_vacancy = st.slider("공실률 추가 (%)", 0, 20, 5) / 100
    st_interest = st.slider("금리 인상 (%p)", 0.0, 5.0, 1.0, step=0.1) / 100
    st_cap = st.slider("매각캡 인상 (%p)", 0.0, 2.0, 0.5, step=0.1) / 100

inputs = {
    "asset_name": asset_name, "location": location, "purchase_price": purchase_price,
    "leasable_area_sqm": leasable_area_sqm, "annual_rent_per_sqm": annual_rent_per_sqm,
    "vacancy_rate": vacancy_rate, "annual_capex": annual_capex,
    "property_tax_ratio": property_tax_ratio, "opex_per_sqm": opex_per_sqm,
    "other_opex_ratio": other_opex_ratio,
    "ltv": ltv, "interest_rate": interest_rate, "hold_period_years": hold_period_years,
    "exit_cap_rate": exit_cap_rate, "tenant_concentration": tenant_concentration
}

scenario_params = {
    "downside": {"vacancy_rate": 0.07, "annual_rent_per_sqm": -0.07, "interest_rate": 0.005, "exit_cap_rate": 0.005},
    "upside": {"vacancy_rate": -0.03, "annual_rent_per_sqm": 0.05, "exit_cap_rate": -0.003},
    "stress": {"vacancy_rate": st_vacancy, "interest_rate": st_interest, "exit_cap_rate": st_cap}
}

# 5. Analysis Execution
if st.sidebar.button("분석 실행", type="primary"):
    results = calculator.run_underwriting_for_scenarios(inputs, scenario_params)
    base_res = results['base']
    memo_result = memo_engine.generate_investment_memo(results, inputs)
    dd_result = dd_engine.generate_dd_checklist(results, inputs)
    
    # 민감도 데이터 준비
    vacancy_steps = [v / 100 for v in range(0, 21, 2)]
    sensitivity_results = []
    for v in vacancy_steps:
        temp_inputs = inputs.copy()
        temp_inputs['vacancy_rate'] = v
        res = calculator.run_underwriting(temp_inputs)
        sensitivity_results.append({
            "공실률 (%)": f"{v*100:.0f}%",
            "NOI (억원)": round(res['kpis']['noi']/1e8, 2),
            "IRR (%)": round(res['kpis']['equity_irr']*100, 2) if res['kpis']['equity_irr'] is not None else 0
        })
    sens_df = pd.DataFrame(sensitivity_results)

    v_steps_2d = [v / 100 for v in range(0, 11, 2)]
    cap_offsets = [-0.01, -0.005, 0.0, 0.005, 0.01]
    matrix_data = []
    for v in v_steps_2d:
        row = {"공실률 \ 매각캡": f"{v*100:.0f}%"}
        for offset in cap_offsets:
            target_cap = inputs['exit_cap_rate'] + offset
            temp_inputs = inputs.copy()
            temp_inputs['vacancy_rate'] = v
            temp_inputs['exit_cap_rate'] = target_cap if target_cap > 0.001 else 0.001
            res = calculator.run_underwriting(temp_inputs)
            irr = res['kpis']['equity_irr']
            row[f"{target_cap*100:.1f}%"] = f"{irr*100:.2f}%" if irr is not None else "N/A"
        matrix_data.append(row)
    matrix_df = pd.DataFrame(matrix_data)

    st.title(f"🏢 {asset_name} 투자 분석 보고서")
    st.caption(f"Location: {location} | Hold Period: {hold_period_years} years")

    tabs = st.tabs(["📊 Overview", "📑 Underwriting", "📉 Scenarios", "✍️ Investment Memo", "✅ DD Checklist", "📈 Comparison"])

    # --- Tab 1: Overview ---
    with tabs[0]:
        k = base_res['kpis']
        col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
        col1.metric("NOI", format_krw(k['noi']))
        col2.metric("DSCR", f"{k['dscr']}x" if k['dscr'] else "N/A")
        col3.metric("LTV", format_pct(k['ltv']))
        col4.metric("CoC (배당률)", format_pct(k['coc']))
        col5.metric("EM (배수)", f"{k['em']}x")
        col6.metric("Exit Value", format_krw(k['exit_value']))
        col7.metric("Equity IRR", format_pct(k['equity_irr']))

        st.divider()
        c_col1, c_col2, c_col3 = st.columns(3)
        with c_col1: st.write(f"**Entry Cap Rate:** {format_pct(k['entry_cap'])}")
        with c_col2: st.write(f"**Exit Cap Rate:** {format_pct(inputs['exit_cap_rate'])}")
        with c_col3:
            spread = (inputs['exit_cap_rate'] - k['entry_cap']) * 10000
            st.write(f"**Cap Spread (bps):** {spread:,.0f} bps")

        col_dl1, col_dl2, col_save = st.columns(3)
        with col_dl1:
            st.download_button("📥 엑셀 다운로드", reporting_engine.get_excel_data(inputs, results, base_res, sens_df, matrix_df), f"UW_{asset_name}.xlsx")
        with col_dl2:
            st.download_button("📄 PDF 보고서", reporting_engine.get_pdf_data(inputs, results, base_res), f"Report_{asset_name}.pdf")
        with col_save:
            if st.button("💾 시나리오 저장"):
                st.session_state.saved_scenarios[asset_name] = {"kpis": k, "inputs": inputs}
                save_stored_data(st.session_state.saved_scenarios)
                st.success("저장 완료!")

    # --- Tab 2: Underwriting ---
    with tabs[1]:
        rb, db, eb = base_res['rent_block'], base_res['debt_block'], base_res['exit_block']
        st.write("**[운영 수지 및 금융 상세]**")
        st.table(pd.DataFrame([
            {"항목": "GRI", "금액": format_krw(rb['gri'])}, {"항목": "EGI", "금액": format_krw(rb['egi'])},
            {"항목": "재산세", "금액": format_krw(rb['property_tax'])}, {"항목": "보험/PM", "금액": format_krw(rb['insurance_pm'])},
            {"항목": "Total Opex", "금액": format_krw(rb['total_opex'])}, {"항목": "NOI", "금액": format_krw(rb['noi'])},
            {"항목": "대출원금", "금액": format_krw(db['loan_amount'])}, {"항목": "DSCR", "금액": f"{db['dscr']}x"}
        ]))

    # --- Tab 3: Scenarios ---
    with tabs[2]:
        sc_summary = []
        for s_name in ["base", "downside", "upside", "stress"]:
            sk = results[s_name]['kpis']
            sc_summary.append({"Scenario": s_name.upper(), "NOI": round(sk['noi']/1e8, 1), "DSCR": sk['dscr'], "IRR (%)": round(sk['equity_irr']*100, 2) if sk['equity_irr'] else 0})
        st.table(pd.DataFrame(sc_summary))

        st.subheader("🔥 IRR 민감도 히트맵")
        plot_df = matrix_df.set_index("공실률 \ 매각캡")
        plot_values = plot_df.applymap(lambda x: float(x.replace('%', '')) if x != 'N/A' else None)
        fig_heat = go.Figure(data=go.Heatmap(z=plot_values.values, x=plot_values.columns, y=plot_values.index, colorscale='RdYlGn', text=plot_df.values, texttemplate="%{text}"))
        st.plotly_chart(fig_heat, use_container_width=True)

    # --- Tab 4 & 5 (Memo & DD) ---
    with tabs[3]: st.markdown(memo_result['summary'])
    with tabs[4]: st.write(dd_result)

    # --- Tab 6: Comparison ---
    with tabs[5]:
        if st.session_state.saved_scenarios:
            comp_df = pd.DataFrame([{"자산명": name, "IRR (%)": f"{data['kpis']['equity_irr']*100:.2f}%", "DSCR": f"{data['kpis']['dscr']}x", "LTV": f"{data['kpis']['ltv']*100:.0f}%"} for name, data in st.session_state.session_state.saved_scenarios.items()])
            st.dataframe(comp_df, use_container_width=True)
            if st.button("🗑️ 모든 저장 기록 삭제"):
                st.session_state.saved_scenarios = {}
                st.rerun()
        else:
            st.info("저장된 시나리오가 없습니다. Overview 탭에서 저장해 주세요.")
else:
    st.info("왼쪽 사이드바에서 '분석 실행'을 클릭하세요.")
