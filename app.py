import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import calculator
import memo_engine
import dd_engine
import io
from fpdf import FPDF

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

# 4. Scenario Settings
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
    },
    "stress": {
        "vacancy_rate": st_vacancy,
        "interest_rate": st_interest,
        "exit_cap_rate": st_cap
    }
}

# 5. Analysis Execution
if st.sidebar.button("분석 실행", type="primary"):
    results = calculator.run_underwriting_for_scenarios(inputs, scenario_params)
    base_res = results['base']
    
    # 엔진 호출
    memo_result = memo_engine.generate_investment_memo(results, inputs)
    dd_result = dd_engine.generate_dd_checklist(results, inputs)
    
    # --- [데이터 준비] 민감도 분석 ---
    # 1. 공실률 민감도
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

    # 2. 2D 민감도
    v_steps_2d = [v / 100 for v in range(0, 11, 2)]
    cap_offsets = [-0.01, -0.005, 0.0, 0.005, 0.01]
    matrix_data = []
    for v in v_steps_2d:
        row = {"공실률 \ 매각캡": f"{v*100:.0f}%"}
        for offset in cap_offsets:
            target_cap = inputs['exit_cap_rate'] + offset
            if target_cap < 0.001: target_cap = 0.001
            temp_inputs = inputs.copy()
            temp_inputs['vacancy_rate'] = v
            temp_inputs['exit_cap_rate'] = target_cap
            res = calculator.run_underwriting(temp_inputs)
            irr = res['kpis']['equity_irr']
            row[f"{target_cap*100:.1f}%"] = f"{irr*100:.2f}%" if irr is not None else "N/A"
        matrix_data.append(row)
    matrix_df = pd.DataFrame(matrix_data)

    # --- [엑셀 내보내기 함수] ---
    def get_excel_data():
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # 1. 가정
            pd.DataFrame(list(inputs.items()), columns=['항목', '값']).to_excel(writer, sheet_name='가정', index=False)
            # 2. 상세 수지
            rb, db, eb = base_res['rent_block'], base_res['debt_block'], base_res['exit_block']
            uw_export = [
                {"항목": "GRI", "값": rb['gri']}, {"항목": "EGI", "값": rb['egi']},
                {"항목": "재산세", "값": rb['property_tax']}, {"항목": "보험/PM", "값": rb['insurance_pm']},
                {"항목": "기타운영비", "값": rb['other_opex']}, {"항목": "Total Opex", "값": rb['total_opex']},
                {"항목": "NOI", "값": rb['noi']}, {"항목": "대출금액", "값": db['loan_amount']},
                {"항목": "연이자", "값": db['annual_debt_service']}, {"항목": "DSCR", "값": db['dscr']},
                {"항목": "매각가", "값": eb['exit_value']}, {"항목": "Entry Cap", "값": eb['entry_cap']},
                {"항목": "CoC (배당률)", "값": eb['coc']}, {"항목": "EM (배수)", "값": eb['em']},
                {"항목": "IRR", "값": eb['equity_irr']}
            ]
            pd.DataFrame(uw_export).to_excel(writer, sheet_name='수지분석', index=False)
            # 3. 시나리오 요약
            sc_summary_export = []
            for s_name in ["base", "downside", "upside", "stress"]:
                sk = results[s_name]['kpis']
                sc_summary_export.append({"시나리오": s_name.upper(), "NOI": sk['noi'], "DSCR": sk['dscr'], "IRR": sk['equity_irr'], "EM": sk['em']})
            pd.DataFrame(sc_summary_export).to_excel(writer, sheet_name='시나리오', index=False)
            # 4. 민감도
            sens_df.to_excel(writer, sheet_name='공실률_민감도', index=False)
            matrix_df.to_excel(writer, sheet_name='2D_민감도', index=False)
        return output.getvalue()

    # --- [PDF 내보내기 함수] ---
    def get_pdf_data():
        pdf = FPDF()
        pdf.add_page()
        
        # Header
        pdf.set_font("Helvetica", "B", 20)
        pdf.cell(0, 15, "INVESTMENT ANALYSIS REPORT", ln=True, align="C")
        pdf.set_font("Helvetica", "I", 10)
        pdf.cell(0, 5, f"Asset: {asset_name} | Location: {location}", ln=True, align="C")
        pdf.ln(10)
        
        # 1. Executive Summary
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, "1. Executive Summary", ln=True)
        pdf.set_font("Helvetica", "", 10)
        sum_k = base_res['kpis']
        summary_text = (
            f"The proposed investment in '{asset_name}' is projected to yield an Equity IRR of {sum_k['equity_irr']*100:.2f}% "
            f"with an Equity Multiple (EM) of {sum_k['em']}x over a {hold_period_years}-year holding period. "
            f"The Day-1 Cash-on-Cash (CoC) return is estimated at {sum_k['coc']*100:.2f}%, indicating a solid yield profile. "
            f"Debt coverage remains stable with a DSCR of {sum_k['dscr']}x."
        )
        pdf.multi_cell(0, 7, summary_text)
        pdf.ln(5)

        # 2. Key Metrics Table
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, "2. Key Financial Metrics (Base Case)", ln=True)
        
        def add_row(label, value):
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(70, 8, label, border=1)
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(70, 8, value, border=1, ln=True)

        add_row("Purchase Price", format_krw(purchase_price))
        add_row("Net Operating Income (NOI)", format_krw(sum_k['noi']))
        add_row("Entry Cap Rate", f"{sum_k['entry_cap']*100:.2f}%")
        add_row("Exit Cap Rate", f"{inputs['exit_cap_rate']*100:.2f}%")
        add_row("Cap Rate Spread", f"{(inputs['exit_cap_rate'] - sum_k['entry_cap'])*10000:.0f} bps")
        add_row("LTV / Interest Rate", f"{sum_k['ltv']*100:.0f}% / {interest_rate*100:.1f}%")
        add_row("DSCR", f"{sum_k['dscr']}x")
        add_row("Equity IRR", f"{sum_k['equity_irr']*100:.2f}%")
        add_row("Equity Multiple", f"{sum_k['em']}x")
        pdf.ln(10)

        # 3. Scenario Analysis
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, "3. Scenario & Stress Test Summary", ln=True)
        pdf.set_font("Helvetica", "B", 10)
        cols = ["Scenario", "NOI (100M)", "DSCR", "IRR (%)", "EM"]
        col_widths = [40, 30, 25, 25, 25]
        
        for i, col in enumerate(cols):
            pdf.cell(col_widths[i], 8, col, border=1, align="C")
        pdf.ln()
        
        pdf.set_font("Helvetica", "", 10)
        for s_name in ["base", "downside", "upside", "stress"]:
            sk = results[s_name]['kpis']
            pdf.cell(40, 8, s_name.upper(), border=1)
            pdf.cell(30, 8, f"{sk['noi']/1e8:.1f}", border=1, align="C")
            pdf.cell(25, 8, f"{sk['dscr']}", border=1, align="C")
            pdf.cell(25, 8, f"{sk['equity_irr']*100:.2f}%" if sk['equity_irr'] else "N/A", border=1, align="C")
            pdf.cell(25, 8, f"{sk['em']}x", border=1, align="C")
            pdf.ln()

        return pdf.output()

    st.title(f"🏢 {asset_name} 투자 분석 보고서")
    st.caption(f"Location: {location} | Hold Period: {hold_period_years} years")

    tabs = st.tabs(["📊 Overview", "📑 Underwriting", "📉 Scenarios", "✍️ Investment Memo", "✅ DD Checklist"])

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

        # Cap Rate Spread Analysis
        st.divider()
        c_col1, c_col2, c_col3 = st.columns(3)
        with c_col1:
            st.write(f"**Entry Cap Rate:** {format_pct(k['entry_cap'])}")
        with c_col2:
            st.write(f"**Exit Cap Rate:** {format_pct(inputs['exit_cap_rate'])}")
        with c_col3:
            spread = (inputs['exit_cap_rate'] - k['entry_cap']) * 10000
            st.write(f"**Cap Spread (bps):** {spread:,.0f} bps")
            if spread < 0:
                st.error("⚠️ 경고: Exit Cap이 Entry보다 낮습니다. (공격적 매각가 산정)")
            elif spread < 25:
                st.warning("🔔 주의: Cap Spread가 25bps 미만으로 좁습니다.")
            else:
                st.success("✅ 안정: 적정 수준의 Cap Spread 확보 (보수적 매각가 산정)")

        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            st.download_button(
                label="📥 분석 결과 다운로드 (Excel)",
                data=get_excel_data(),
                file_name=f"Underwriting_Report_{asset_name}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        with col_dl2:
            st.download_button(
                label="📄 투자 분석 보고서 다운로드 (PDF)",
                data=get_pdf_data(),
                file_name=f"Investment_Report_{asset_name}.pdf",
                mime="application/pdf"
            )

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
        
        col_uw1, col_dl_space = st.columns([2, 1])
        with col_uw1:
            st.write("**[운영 수지 상세]**")
            opex_details = [
                {"항목": "GRI (총잠재임대수입)", "금액": format_krw(rb['gri'])},
                {"항목": "EGI (유효영업수입)", "금액": format_krw(rb['egi'])},
                {"항목": "ㄴ 재산세 (Tax)", "금액": format_krw(rb['property_tax'])},
                {"항목": "ㄴ 보험료/PM (Insurance/PM)", "금액": format_krw(rb['insurance_pm'])},
                {"항목": "ㄴ 기타운영비 (Others)", "금액": format_krw(rb['other_opex'])},
                {"항목": "Total Opex (운영비 계)", "금액": format_krw(rb['total_opex'])},
                {"항목": "Capex (유지보수비)", "금액": format_krw(inputs['annual_capex'])},
                {"항목": "NOI (순영업소득)", "금액": format_krw(rb['noi'])},
            ]
            st.table(pd.DataFrame(opex_details))

        st.divider()
        st.write("**[금융 및 회수 지표]**")
        uw_data = [
            {"Category": "Debt", "Item": "Loan Amount (대출원금)", "Value": format_krw(db['loan_amount'])},
            {"Category": "Debt", "Item": "Annual Debt Service (연이자)", "Value": format_krw(db['annual_debt_service'])},
            {"Category": "Debt", "Item": "DSCR", "Value": f"{db['dscr']}x" if db['dscr'] else "N/A"},
            {"Category": "Exit", "Item": "Exit Value (매각가)", "Value": format_krw(eb['exit_value'])},
            {"Category": "Exit", "Item": "Equity Investment (자기자본)", "Value": format_krw(eb['equity'])},
            {"Category": "Exit", "Item": "Equity IRR (수익률)", "Value": format_pct(eb['equity_irr'])},
            {"Category": "Exit", "Item": "Equity Multiple (배수)", "Value": f"{eb['em']}x"},
        ]
        st.dataframe(pd.DataFrame(uw_data), use_container_width=True)

    # --- Tab 3: Scenarios ---
    with tabs[2]:
        st.subheader("시나리오별 민감도 분석")
        sc_summary = []
        for s_name in ["base", "downside", "upside", "stress"]:
            sk = results[s_name]['kpis']
            sc_summary.append({
                "Scenario": s_name.upper(),
                "NOI (억원)": round(sk['noi']/1e8, 1),
                "DSCR": sk['dscr'],
                "Exit (억원)": round(sk['exit_value']/1e8, 1),
                "IRR (%)": round(sk['equity_irr']*100, 2) if sk['equity_irr'] else 0,
                "EM": sk['em']
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

        # --- New Section: Vacancy Rate Sensitivity ---
        st.divider()
        st.subheader("📍 공실률 민감도 분석 (0% ~ 20%)")
        
        col_s1, col_s2 = st.columns([1, 2])
        with col_s1:
            st.table(sens_df)
            
        with col_s2:
            fig_sens = go.Figure()
            fig_sens.add_trace(go.Scatter(
                x=sens_df["공실률 (%)"],
                y=sens_df["IRR (%)"],
                mode='lines+markers',
                name='Equity IRR',
                line=dict(color='firebrick', width=3)
            ))
            fig_sens.update_layout(
                title="공실률 변동에 따른 Equity IRR 추이",
                xaxis_title="공실률 (%)",
                yaxis_title="IRR (%)",
                template="plotly_white"
            )
            st.plotly_chart(fig_sens, use_container_width=True)

        # --- New Section: 2D Sensitivity Matrix ---
        st.divider()
        st.subheader("📊 2D 민감도 분석: 공실률 vs 매각 캡레이트 (IRR %)")
        st.caption("공실률(0%~10%)과 매각 캡레이트(기준 대비 +-1.0%) 변화에 따른 Equity IRR 변화 매트릭스입니다.")
        
        st.dataframe(matrix_df, hide_index=True, use_container_width=True)

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

        st.markdown(memo_result['summary'])
        
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
