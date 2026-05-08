from typing import Dict, List, Optional

def _get_baseline_checklist(base_inputs: Dict) -> Dict[str, List[str]]:
    financial = [
        "Rent roll 및 Lease Summary 검토 (임대차 기간, 중도해지권 등)",
        "Historical Operating Statement 검토 (과거 3개년 NOI 변동성 확인)",
        "CAM/Opex 구조 및 계정 분류 확인 (임차인 전가 비용 항목 검증)",
        "Property Tax(재산세 등) 및 보험료 실제 부과 내역 검증",
        "대출 조건 및 금융 Covenant 준수 여부 검토"
    ]
    
    legal = [
        "Title Report 및 소유권 이전 이슈 확인 (제한물권 존재 여부)",
        "Zoning 및 용도지역 제한 사항 검토 (지구단위계획 적합성)",
        "주요 Lease 계약서 원문 및 Option 조항(연장권, 우선매수권) 검토",
        "Easement, 지상권, 구분지상권 존재 여부 및 운영 영향도 확인",
        "인허가 조건 및 건축법 준수 여부 (준공 시 조건 이행 여부)"
    ]
    
    physical = [
        "Building Condition Report (구조물 결함, 지붕 누수, 기계 설비 연식)",
        "환경 실사 Phase I (토양 오염 및 유해물질 존재 여부 확인)",
        "화재·안전 관련 법규 준수 여부 (스프링클러, 소방 설비 점검)",
        "Flood Risk 및 자연재해 취약성 확인",
    ]
    
    asset_name = base_inputs.get("asset_name", "")
    if any(word in asset_name for word in ["콜드", "저온", "냉동", "Cold"]):
        physical.append("냉동·저온 설비 유지 현황 및 효율성(전력량 등) 상세 점검")

    market = [
        "인근 경쟁 물류센터 공급 현황 및 향후 Pipeline 분석",
        "권역 내 시장 임대료 및 공실률 추이 비교 (Benchmark 분석)",
        "주요 수요처(3PL, E-commerce) 이탈 및 유입 동향",
        "교통 접근성(IC 인접도) 및 인근 도로 인프라 변화 계획",
        "물류 산업 동향 및 임차인 주력 산업군 성장 전망"
    ]
    
    return {
        "financial": financial,
        "legal": legal,
        "physical": physical,
        "market": market
    }

def _get_priority_items(scenario_results: Dict, base_inputs: Dict) -> List[str]:
    priorities = []
    
    base_kpi = scenario_results.get("base", {}).get("kpis", {})
    downside_kpi = scenario_results.get("downside", {}).get("kpis", {})
    
    if (base_kpi.get("dscr") or 0) < 1.2:
        priorities.append("대출 구조(금리, 만기) 및 상환 스케줄 재검토 (DSCR 1.2 미만)")
    if (downside_kpi.get("dscr") or 0) < 1.0:
        priorities.append("다운사이드 시나리오 현금흐름 적자 가능성 대비 Lender 사전 협의")
    if base_inputs.get("tenant_concentration", 0) > 0.5:
        priorities.append("핵심 임차인 Lease Expiry 및 Credit Profile 심층 검토 (테넌트 집중도 높음)")
    if base_inputs.get("exit_cap_rate", 1.0) < 0.05:
        priorities.append("Exit Cap Rate 가정의 보수성 재검토 및 시장 거래 사례(Comps) 대조")
    if base_inputs.get("hold_period_years", 0) >= 7:
        priorities.append("장기 보유에 따른 Major Repair 계획 및 Capex Reserve 적정성 검토")
        
    return priorities

def generate_dd_checklist(scenario_results: Dict, base_inputs: Dict) -> Dict:
    baseline = _get_baseline_checklist(base_inputs)
    priorities = _get_priority_items(scenario_results, base_inputs)
    
    return {
        "financial": baseline["financial"],
        "legal": baseline["legal"],
        "physical": baseline["physical"],
        "market": baseline["market"],
        "priority_items": priorities
    }
