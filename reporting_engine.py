import pandas as pd
import io
from fpdf import FPDF
from typing import Dict

def get_excel_data(inputs: Dict, results: Dict, base_res: Dict, sens_df: pd.DataFrame, matrix_df: pd.DataFrame):
    """
    분석 결과를 엑셀 파일로 생성합니다.
    """
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
            if s_name in results:
                sk = results[s_name]['kpis']
                sc_summary_export.append({"시나리오": s_name.upper(), "NOI": sk['noi'], "DSCR": sk['dscr'], "IRR": sk['equity_irr'], "EM": sk['em']})
        pd.DataFrame(sc_summary_export).to_excel(writer, sheet_name='시나리오', index=False)
        # 4. 민감도
        sens_df.to_excel(writer, sheet_name='공실률_민감도', index=False)
        matrix_df.to_excel(writer, sheet_name='2D_민감도', index=False)
    return output.getvalue()

def get_pdf_data(inputs: Dict, results: Dict, base_res: Dict):
    """
    분석 결과를 PDF 보고서로 생성합니다.
    """
    pdf = FPDF()
    pdf.add_page()
    
    asset_name = inputs.get('asset_name', 'Asset')
    location = inputs.get('location', 'Location')
    hold_period_years = inputs.get('hold_period_years', 5)
    purchase_price = inputs.get('purchase_price', 0)
    interest_rate = inputs.get('interest_rate', 0)
    
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

    add_row("Purchase Price", f"{purchase_price/1e8:,.1f} 100M KRW")
    add_row("Net Operating Income (NOI)", f"{sum_k['noi']/1e8:,.1f} 100M KRW")
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
        if s_name in results:
            sk = results[s_name]['kpis']
            pdf.cell(40, 8, s_name.upper(), border=1)
            pdf.cell(30, 8, f"{sk['noi']/1e8:.1f}", border=1, align="C")
            pdf.cell(25, 8, f"{sk['dscr']}", border=1, align="C")
            pdf.cell(25, 8, f"{sk['equity_irr']*100:.2f}%" if sk['equity_irr'] else "N/A", border=1, align="C")
            pdf.cell(25, 8, f"{sk['em']}x", border=1, align="C")
            pdf.ln()

    return pdf.output()
