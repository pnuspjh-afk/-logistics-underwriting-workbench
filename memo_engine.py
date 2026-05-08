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
    언더라이팅 결과를 바탕으로 국문 투자 메모를 생성합니다.
    """
    base_kpi = scenario_results.get("base", {}).get("kpis", {})
    down_kpi = scenario_results.get("downside", {}).get("kpis", {})
    
    asset_name = base_inputs.get("asset_name", "본 자산")
    location = base_inputs.get("location", "해당 지역")
    
    # 1. Summary
    summary = (
        f"본 건은 {location} 소재 {asset_name}에 대한 지분 투자 건으로, "
        f"Base 시나리오 기준 {_classify_irr(base_kpi.get('equity_irr'))} 및 "
        f"{_classify_dscr(base_kpi.get('dscr'))} 수준을 보입니다."
    )
    
    if (down_kpi.get("dscr", 0) or 0) < 1.0:
        summary += " 단, 다운사이드 시나리오 시 원리금 상환 부담이 존재하므로 주의가 필요합니다."
    else:
        summary += " 하락 시나리오에서도 일정 수준의 현금흐름 방어가 가능할 것으로 판단됩니다."

    # 2. Investment Merits
    merits = [
        f"안정적인 담보인정비율(LTV {base_inputs.get('ltv', 0)*100:.0f}%) 기반의 대출 구조",
        f"권역 내 임대료 시세 대비 경쟁력 있는 임대 조건 (sqm당 {base_inputs.get('annual_rent_per_sqm', 0):,.0f}원)",
        f"{base_inputs.get('hold_period_years')}년 운영 후 Cap Rate {base_inputs.get('exit_cap_rate', 0)*100:.1f}% 기반의 안정적 회수 시나리오"
    ]

    # 3. Key Risks
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

    # 4. Follow-up Points (DD Questions)
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
