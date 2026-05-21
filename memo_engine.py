from typing import Dict, List, Optional

def _classify_dscr(dscr: Optional[float]) -> str:
    if dscr is None: return "분석 불가"
    if dscr >= 1.4: return f"충분한 이자보상 여력 (DSCR {dscr}x)"
    if dscr >= 1.2: return f"보통 수준의 이자보상 여력 (DSCR {dscr}x)"
    return f"이자보상 여력 부족 주의 (DSCR {dscr}x)"

def _classify_irr(irr: Optional[float]) -> str:
    if irr is None: return "분석 불가"
    pct = irr * 100
    if pct >= 15: return f"목표수익률 상회 (IRR {pct:.1f}%)"
    if pct >= 10: return f"목표수익률 근접 (IRR {pct:.1f}%)"
    return f"수익성 제한적 (IRR {pct:.1f}%)"

def _get_recommendation(results: Dict) -> str:
    base = results.get("base", {}).get("kpis", {})
    down = results.get("downside", {}).get("kpis", {})
    
    base_dscr = base.get("dscr", 0) or 0
    base_irr = base.get("equity_irr", 0) or 0
    down_dscr = down.get("dscr", 0) or 0
    
    if base_dscr >= 1.2 and base_irr >= 0.12 and down_dscr >= 1.0:
        return "Proceed"
    if base_dscr >= 1.1 and base_irr >= 0.10:
        return "Need More DD"
    return "Pass"

def generate_investment_memo(scenario_results: Dict, base_inputs: Dict) -> Dict:
    """
    언더라이팅 결과를 바탕으로 상세한 국문 투자 메모를 생성합니다.
    """
    base_kpi = scenario_results.get("base", {}).get("kpis", {})
    down_kpi = scenario_results.get("downside", {}).get("kpis", {})
    
    asset_name = base_inputs.get("asset_name", "본 자산")
    location = base_inputs.get("location", "해당 지역")
    
    irr = base_kpi.get('equity_irr', 0) or 0
    dscr = base_kpi.get('dscr', 0) or 0
    noi = base_kpi.get('noi', 0) or 0
    purchase_price = base_inputs.get('purchase_price', 0) or 0
    down_irr = down_kpi.get('equity_irr', 0) or 0
    down_dscr = down_kpi.get('dscr', 0) or 0

    # 1. 수익성 분석
    profitability = (
        f"#### 💰 수익성 분석\n"
        f"본 건은 매입가 {purchase_price/1e8:,.1f}억원 규모의 투자로, "
        f"운영 기간 중 연평균 약 {noi/1e8:,.1f}억원의 순영업소득(NOI) 창출이 기대됩니다. "
        f"Base 시나리오 기준 예상 Equity IRR은 {irr*100:.2f}%로, 이는 자산의 입지적 가치와 "
        f"임대 수익 구조를 고려할 때 { '타겟 수익률을 상회하는 우수한' if irr >= 0.12 else '적정 수준의' } 수익성으로 판단됩니다. "
        f"특히 {base_inputs.get('exit_cap_rate', 0)*100:.1f}%의 보수적인 Exit Cap Rate 적용 하에서도 "
        f"안정적인 자본 회수가 가능한 구조를 확보하고 있습니다."
    )
    
    # 2. 리스크 검토
    risk_review = (
        f"\n\n#### 🚩 리스크 검토\n"
        f"금융 구조 측면에서 DSCR은 {dscr:.2f}x 수준으로 유지되어 이자 지급 여력은 { '충분한' if dscr >= 1.3 else '양호한' } 상태입니다. "
        f"다만, 공실률 상승 및 금리 인상을 가정한 Downside 시나리오 적용 시 IRR이 {down_irr*100:.2f}%까지 "
        f"하락할 수 있으며, DSCR 또한 {down_dscr:.2f}x로 낮아져 민감도가 다소 높은 편입니다. "
        f"또한 {base_inputs.get('tenant_concentration', 0)*100:.1f}% 수준의 임차인 집중도는 향후 계약 만료 시점의 재임대 리스크 요인이므로 "
        f"이에 대한 분산 전략이나 장기 계약 확보 여부를 면밀히 검토해야 합니다."
    )
    
    # 3. 종합 의견
    opinion = (
        f"\n\n#### 🧐 종합 의견\n"
        f"결론적으로 본 프로젝트는 {location} 권역의 물류 수요 성장을 바탕으로 한 안정적 현금흐름 창출이 기대되는 건입니다. "
        f"현재의 금융 시장 변동성 하에서도 {base_inputs.get('ltv', 0)*100:.0f}%의 적정 LTV 수준을 유지하고 있어 "
        f"재무적 건전성이 확보된 것으로 사료됩니다. 실사(DD) 과정에서 물리적 상태 및 임대차 세부 조건을 최종 확인한 후 "
        f"투자를 진행하는 것이 타당할 것으로 판단됩니다."
    )
    
    summary = profitability + risk_review + opinion

    # 4. Investment Merits
    merits = [
        f"안정적인 담보인정비율(LTV {base_inputs.get('ltv', 0)*100:.0f}%) 기반의 대출 구조",
        f"권역 내 임대료 시세 대비 경쟁력 있는 임대 조건 (sqm당 {base_inputs.get('annual_rent_per_sqm', 0):,.0f}원)",
        f"{base_inputs.get('hold_period_years')}년 운영 후 Cap Rate {base_inputs.get('exit_cap_rate', 0)*100:.1f}% 기반의 안정적 회수 시나리오"
    ]

    # 5. Key Risks
    risks = []
    if base_inputs.get("tenant_concentration", 0) > 0.5:
        risks.append(f"핵심 임차인 의존도 높음(집중도 {base_inputs.get('tenant_concentration', 0)*100:.0f}%): 임차인 이탈 시 공실 리스크 존재")
    else:
        risks.append("임차인 구성 다변화를 통한 공실 분산 필요")
        
    if (down_kpi.get("dscr", 0) or 0) < 1.1:
        risks.append("금리 인상 및 공실 증가 시 DSCR 커버리지 급격히 하락 가능성")
    else:
        risks.append("시장 Cap Rate 상승에 따른 매각 가치 하락 위험")
        
    risks.append(f"연간 Capex ({base_inputs.get('annual_capex', 0)/1e6:,.0f}백만원) 과소 책정 가능성 및 노후화에 따른 유지보수비 증가")

    # 6. Follow-up Points (DD Questions)
    follow_ups = [
        "주요 임차인의 신용도 확인 및 임대차 계약 연장 의사 타진",
        "물류센터 바닥 하중 및 램프 구조의 범용성 확인을 위한 Physical DD",
        "인근 유사 자산의 최근 매각 사례(Cap Rate) 상세 비교 분석",
        "지방세 및 제세공과금 변동 가능성에 대한 세무 검토",
        "화재보험 가입 조건 및 소방 설비 적합성 판정 여부"
    ]

    return {
        "summary": summary,
        "investment_merits": "\n".join([f"{i+1}. {m}" for i, m in enumerate(merits)]),
        "key_risks": "\n".join([f"{i+1}. {r}" for i, r in enumerate(risks)]),
        "follow_up_points": "\n".join([f"{i+1}. {f}" for i, f in enumerate(follow_ups)]),
        "recommendation": _get_recommendation(scenario_results)
    }
