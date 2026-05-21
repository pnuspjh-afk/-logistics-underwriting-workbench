import copy
import math
from typing import Dict, List, Optional, Union

# IRR 계산을 위한 numpy_financial 시도
try:
    import numpy_financial as npf
except ImportError:
    npf = None


def validate_inputs(inputs: Dict) -> Dict:
    """
    입력 데이터의 유효성을 검증하고 기본값을 설정합니다.
    """
    validated = copy.deepcopy(inputs)
    
    # 필수 수치 필드 리스트
    numeric_fields = [
        'purchase_price', 'leasable_area_sqm', 'annual_rent_per_sqm',
        'ltv', 'interest_rate', 'hold_period_years', 'exit_cap_rate'
    ]
    
    for field in numeric_fields:
        if field not in validated or validated[field] is None:
            validated[field] = 0.0
            
    # 비율 데이터 보정 (0~1 범위 권장)
    validated['vacancy_rate'] = max(0.0, min(1.0, validated.get('vacancy_rate', 0.0)))
    validated['opex_ratio'] = max(0.0, min(1.0, validated.get('opex_ratio', 0.0)))
    
    return validated


def compute_noi(inputs: Dict) -> Dict:
    """
    임대수익 및 상세 운영비용(Opex)을 반영하여 NOI를 산출합니다.
    """
    gri = inputs['leasable_area_sqm'] * inputs['annual_rent_per_sqm']
    egi = gri * (1 - inputs['vacancy_rate'])
    
    # 1. 재산세: 매입가 대비 요율
    property_tax = inputs.get('property_tax_ratio', 0.0015) * inputs['purchase_price']
    
    # 2. 보험료 및 PM 수수료: 면적당 단가
    insurance_pm = inputs.get('opex_per_sqm', 3000) * inputs['leasable_area_sqm']
    
    # 3. 기타 운영비: EGI 대비 요율
    other_opex = inputs.get('other_opex_ratio', 0.02) * egi
    
    total_opex = property_tax + insurance_pm + other_opex
    
    # 하위 호환성 및 수기 입력 대응
    if inputs.get('annual_opex', 0) > 0:
        total_opex = inputs['annual_opex']
    elif inputs.get('opex_ratio', 0) > 0 and (property_tax + insurance_pm + other_opex) == 0:
        total_opex = egi * inputs['opex_ratio']
        
    noi = egi - total_opex - inputs.get('annual_capex', 0)
    
    return {
        "gri": round(gri, 2),
        "egi": round(egi, 2),
        "property_tax": round(property_tax, 2),
        "insurance_pm": round(insurance_pm, 2),
        "other_opex": round(other_opex, 2),
        "total_opex": round(total_opex, 2),
        "noi": round(noi, 2)
    }


def compute_debt_metrics(inputs: Dict, noi: float) -> Dict:
    """
    대출 관련 지표(LTV, DSCR)를 산출합니다.
    """
    loan_amount = inputs['purchase_price'] * inputs['ltv']
    # Interest-only (만기일시상환) 가정
    annual_debt_service = loan_amount * inputs['interest_rate']
    
    dscr = None
    if annual_debt_service > 0:
        dscr = round(noi / annual_debt_service, 2)
    elif noi > 0:
        dscr = 99.9  # 무부채 시 매우 높은 값으로 처리
        
    ltv_effective = round(loan_amount / inputs['purchase_price'], 4) if inputs['purchase_price'] > 0 else 0
    
    return {
        "loan_amount": round(loan_amount, 2),
        "annual_debt_service": round(annual_debt_service, 2),
        "dscr": dscr,
        "ltv_effective": ltv_effective
    }


def _calculate_irr(cash_flows: List[float]) -> Optional[float]:
    """
    Cash Flow 시리즈로부터 IRR을 계산합니다. 계산 불가 시 None을 반환합니다.
    """
    if not cash_flows or len(cash_flows) < 2:
        return None
        
    if npf:
        try:
            val = float(npf.irr(cash_flows))
            return val if not math.isnan(val) else None
        except Exception:
            return None
    
    return None 


def compute_exit_and_irr(inputs: Dict, noi: float, annual_debt_service: float) -> Dict:
    """
    매각 가치, 배당수익률(CoC), 자본배율(EM), IRR을 산출합니다.
    """
    # 1. Exit Value (Cap Rate 기준)
    exit_cap = inputs['exit_cap_rate']
    exit_value = (noi / exit_cap) if exit_cap > 0 else 0
    
    # 2. Entry Cap Rate
    entry_cap = (noi / inputs['purchase_price']) if inputs['purchase_price'] > 0 else 0
    
    # 3. Capital Stack
    loan_amount = inputs['purchase_price'] * inputs['ltv']
    equity_initial = inputs['purchase_price'] - loan_amount
    
    # 4. Cash Flows
    cf_annual = noi - annual_debt_service
    sale_proceeds = exit_value - loan_amount
    
    hold_years = int(inputs['hold_period_years'])
    cash_flows = [-equity_initial]  # Year 0: Equity Out
    
    total_inflow = 0
    for year in range(1, hold_years):
        cash_flows.append(cf_annual)  # Year 1 ~ n-1
        total_inflow += cf_annual
        
    # Year n: 운영수익 + 매각수익
    final_cf = cf_annual + sale_proceeds
    cash_flows.append(final_cf)
    total_inflow += final_cf
    
    # 5. Metrics
    coc = (cf_annual / equity_initial) if equity_initial > 0 else 0
    em = (total_inflow / equity_initial) if equity_initial > 0 else 0
    irr = _calculate_irr(cash_flows)
    
    return {
        "exit_value": round(exit_value, 2),
        "entry_cap": round(entry_cap, 4),
        "equity": round(equity_initial, 2),
        "coc": round(coc, 4),
        "em": round(em, 2),
        "cash_flow_series": cash_flows,
        "equity_irr": round(irr, 4) if irr is not None else None
    }


def run_underwriting(inputs: Dict) -> Dict:
    """
    전체 언더라이팅 로직을 순차적으로 실행하여 종합 결과를 반환합니다.
    """
    val_inputs = validate_inputs(inputs)
    
    rent_block = compute_noi(val_inputs)
    debt_block = compute_debt_metrics(val_inputs, rent_block['noi'])
    exit_block = compute_exit_and_irr(val_inputs, rent_block['noi'], debt_block['annual_debt_service'])
    
    return {
        "inputs": val_inputs,
        "rent_block": rent_block,
        "debt_block": debt_block,
        "exit_block": exit_block,
        "kpis": {
            "noi": rent_block['noi'],
            "dscr": debt_block['dscr'],
            "ltv": debt_block['ltv_effective'],
            "entry_cap": exit_block['entry_cap'],
            "exit_value": exit_block['exit_value'],
            "equity_irr": exit_block['equity_irr'],
            "coc": exit_block['coc'],
            "em": exit_block['em']
        }
    }


def apply_scenario(base_inputs: Dict, scenario_params: Dict) -> Dict:
    """
    기준 입력값에 시나리오 변수를 적용하여 새로운 입력셋을 생성합니다.
    """
    new_inputs = copy.deepcopy(base_inputs)
    
    for key, adjustment in scenario_params.items():
        if key in new_inputs:
            # 특수 로직: 임대료 같은 경우 '상대적' 조정이 들어올 수 있음
            if key == "annual_rent_per_sqm" and isinstance(adjustment, float) and abs(adjustment) < 1.0:
                # 예: -0.05 면 5% 감소
                new_inputs[key] = new_inputs[key] * (1 + adjustment)
            else:
                # 그 외에는 절대적 가산 (공실률 +0.05 등)
                new_inputs[key] += adjustment
                
    return validate_inputs(new_inputs)


def run_underwriting_for_scenarios(base_inputs: Dict, scenario_param_map: Dict) -> Dict:
    """
    여러 시나리오(Base, Downside, Upside 등)에 대해 분석을 수행합니다.
    """
    results = {}
    
    # 1. Base Case
    results["base"] = run_underwriting(base_inputs)
    
    # 2. Scenarios
    for scenario_name, params in scenario_param_map.items():
        sc_inputs = apply_scenario(base_inputs, params)
        results[scenario_name] = run_underwriting(sc_inputs)
        
    return results


if __name__ == "__main__":
    # 샘플 테스트 데이터 (한국 물류센터 가상 딜)
    sample_deal = {
        "asset_name": "이천 물류센터 A",
        "location": "경기도 이천시",
        "purchase_price": 50000000000,  # 500억
        "leasable_area_sqm": 20000,     # 6,000평 규모
        "annual_rent_per_sqm": 120000,  # sqm당 연 임대료 12만
        "vacancy_rate": 0.05,           # 공실 5%
        "opex_ratio": 0.15,             # 운영비 15%
        "annual_capex": 200000000,      # 연 2억 유지보수
        "ltv": 0.60,                    # 대출 60%
        "interest_rate": 0.045,         # 금리 4.5%
        "hold_period_years": 5,         # 5년 보유
        "exit_cap_rate": 0.055          # 매각 캡레이트 5.5%
    }
    
    scenario_map = {
        "downside": {
            "vacancy_rate": 0.10,          # 공실 증가 (+5%)
            "annual_rent_per_sqm": -0.10,  # 임대료 하락 (-10%)
            "interest_rate": 0.01          # 금리 상승 (+1%)
        },
        "upside": {
            "vacancy_rate": -0.03,         # 공실 감소 (-3%)
            "exit_cap_rate": -0.005        # 매각가 상승 (Cap Rate 하락 -0.5%)
        }
    }
    
    full_results = run_underwriting_for_scenarios(sample_deal, scenario_map)
    
    print(f"=== {sample_deal['asset_name']} Underwriting Summary ===")
    for sc_name, res in full_results.items():
        k = res['kpis']
        irr_str = f"{k['equity_irr']*100:.2f}%" if k['equity_irr'] is not None else "N/A"
        print(f"[{sc_name.upper()}]")
        print(f"  NOI: {k['noi']:,.0f} KRW")
        print(f"  DSCR: {k['dscr']}")
        print(f"  Exit Value: {k['exit_value']:,.0f} KRW")
        print(f"  Equity IRR: {irr_str}")
        print("-" * 30)
