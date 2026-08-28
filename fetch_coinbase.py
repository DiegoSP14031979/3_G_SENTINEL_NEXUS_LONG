import requests
import json
import datetime
import os

PORTFOLIO_CONFIG = {
    "currency": "EUR",
    "dca_end_date": "2026-11-02",
    "dca_day_of_month": 2,
    "baseline_monthly_budget": 458.76,
    "assets": {
        "DOT": {
            "name": "Polkadot",
            "balance": 1282.6527477,
            "cost_basis": 1.59,
            "dca_monthly_budget": 0.0,
            "dca_weight_pct": 0,
            "staking_enabled": True,
            "staking_apy": 11.8,
            "coingecko_id": "polkadot"
        },
        "BTC": {
            "name": "Bitcoin",
            "balance": 0.01266575,
            "cost_basis": 60021.78,
            "dca_monthly_budget": 183.50,
            "dca_weight_pct": 40,
            "staking_enabled": False,
            "staking_apy": 0.0,
            "coingecko_id": "bitcoin"
        },
        "ETH": {
            "name": "Ethereum",
            "balance": 0.34608017,
            "cost_basis": 1777.71,
            "dca_monthly_budget": 137.63,
            "dca_weight_pct": 30,
            "staking_enabled": True,
            "staking_apy": 3.2,
            "coingecko_id": "ethereum"
        },
        "SOL": {
            "name": "Solana",
            "balance": 5.84408757,
            "cost_basis": 82.01,
            "dca_monthly_budget": 91.75,
            "dca_weight_pct": 20,
            "staking_enabled": True,
            "staking_apy": 6.8,
            "coingecko_id": "solana"
        },
        "LINK": {
            "name": "Chainlink",
            "balance": 19.98997167,
            "cost_basis": 6.89,
            "dca_monthly_budget": 45.88,
            "dca_weight_pct": 10,
            "staking_enabled": False,
            "staking_apy": 0.0,
            "coingecko_id": "chainlink"
        }
    }
}

def fetch_market_data():
    prices = {}
    fng_index = {"value": 58, "classification": "Greed"}
    
    ids = ",".join([cfg["coingecko_id"] for cfg in PORTFOLIO_CONFIG["assets"].values()])
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=eur"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        for symbol, cfg in PORTFOLIO_CONFIG["assets"].items():
            cg_id = cfg["coingecko_id"]
            if cg_id in data and "eur" in data[cg_id]:
                prices[symbol] = float(data[cg_id]["eur"])
    except Exception as e:
        print(f"[WARN] Error fetching market prices: {e}")
        prices = {"DOT": 0.7479, "BTC": 68200.27, "ETH": 2141.37, "SOL": 91.37, "LINK": 10.09}

    try:
        fng_resp = requests.get("https://api.alternative.me/fng/", timeout=10)
        fng_data = fng_resp.json()
        if "data" in fng_data and len(fng_data["data"]) > 0:
            fng_index = {
                "value": int(fng_data["data"][0]["value"]),
                "classification": fng_data["data"][0]["value_classification"]
            }
    except Exception as e:
        print(f"[WARN] Error fetching Fear & Greed Index: {e}")

    return prices, fng_index

def calculate_smart_dca_multiplier(fng_value):
    if fng_value < 25:
        return 1.50, "ACCUMULATE AGGRESSIVE (150%)"
    elif fng_value < 40:
        return 1.25, "ACCUMULATE MODERATE (125%)"
    elif fng_value <= 65:
        return 1.00, "STANDARD DCA (100%)"
    elif fng_value <= 78:
        return 0.85, "PRUDENT DCA (85%)"
    else:
        return 0.70, "DEFENSIVE DCA (70%)"

def calculate_metrics():
    prices, fng_index = fetch_market_data()
    now = datetime.datetime.utcnow()

    total_value_eur = 0.0
    total_cost_eur = 0.0
    assets_summary = []

    for symbol, config in PORTFOLIO_CONFIG["assets"].items():
        curr_price = prices.get(symbol, 0.0)
        balance = config["balance"]
        avg_cost = config["cost_basis"]
        
        current_val = balance * curr_price
        invested_val = balance * avg_cost
        unrealized_pnl = current_val - invested_val
        unrealized_pnl_pct = ((curr_price - avg_cost) / avg_cost * 100) if avg_cost > 0 else 0.0

        total_value_eur += current_val
        total_cost_eur += invested_val

        monthly_staking_eur = (current_val * (config["staking_apy"] / 100.0)) / 12.0 if config["staking_enabled"] else 0.0

        assets_summary.append({
            "symbol": symbol,
            "name": config["name"],
            "balance": balance,
            "current_price": curr_price,
            "cost_basis": avg_cost,
            "current_value_eur": round(current_val, 2),
            "invested_eur": round(invested_val, 2),
            "unrealized_pnl_eur": round(unrealized_pnl, 2),
            "unrealized_pnl_pct": round(unrealized_pnl_pct, 2),
            "dca_monthly": config["dca_monthly_budget"],
            "dca_weight": config["dca_weight_pct"],
            "staking": config["staking_enabled"],
            "staking_apy": config["staking_apy"],
            "monthly_staking_eur": round(monthly_staking_eur, 2)
        })

    for asset in assets_summary:
        weight_pct = (asset["current_value_eur"] / total_value_eur * 100) if total_value_eur > 0 else 0.0
        asset["current_weight_pct"] = round(weight_pct, 2)

        pnl = asset["unrealized_pnl_pct"]
        if asset["dca_monthly"] > 0:
            if pnl > 30.0:
                advice = f"HOLD / DCA STANDARD: Rentabilidad (+{pnl:.1f}%). Mantener orden."
            elif pnl < -15.0:
                advice = f"BUY OPPORTUNITY: Cotizando {-pnl:.1f}% por debajo de Break-even."
            else:
                advice = f"DCA ACTIVE: Acumulación constante cerca de coste medio ({asset['cost_basis']} €)."
        else:
            advice = "STAKING PASSIVE: DCA pausado. Generando rendimientos pasivos."

        asset["advisory"] = advice

    net_pnl_eur = total_value_eur - total_cost_eur
    net_pnl_pct = (net_pnl_eur / total_cost_eur * 100) if total_cost_eur > 0 else 0.0

    dca_multiplier, dca_regime_label = calculate_smart_dca_multiplier(fng_index["value"])
    smart_monthly_budget = PORTFOLIO_CONFIG["baseline_monthly_budget"] * dca_multiplier

    today = datetime.date.today()
    end_date = datetime.date(2026, 11, 2)

    if today > end_date:
        next_dca = "FINALIZADO (Nov 2026)"
        days_until_dca = 0
        dca_active = False
    else:
        next_dca_date = datetime.date(today.year, today.month, 2) if today.day <= 2 else (
            datetime.date(today.year + 1, 1, 2) if today.month == 12 else datetime.date(today.year, today.month + 1, 2)
        )
        next_dca = next_dca_date.strftime("%Y-%m-%d")
        days_until_dca = (next_dca_date - today).days
        dca_active = True

    remaining_cycles = 3
    future_contributions = remaining_cycles * smart_monthly_budget
    total_projected_cost = total_cost_eur + future_contributions

    projections = {
        "bear_case_eur": round(total_projected_cost * 0.95, 2),
        "base_case_eur": round(total_projected_cost * 1.25, 2),
        "bull_case_eur": round(total_projected_cost * 1.60, 2)
    }

    total_monthly_staking = sum(a["monthly_staking_eur"] for a in assets_summary)

    portfolio_data = {
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "total_value_eur": round(total_value_eur, 2),
        "total_cost_eur": round(total_cost_eur, 2),
        "net_pnl_eur": round(net_pnl_eur, 2),
        "net_pnl_pct": round(net_pnl_pct, 2),
        "mtd_pct": 2.40,
        "ytd_pct": 14.85,
        "fng_index": fng_index,
        "smart_dca": {
            "multiplier": dca_multiplier,
            "regime": dca_regime_label,
            "baseline_budget": PORTFOLIO_CONFIG["baseline_monthly_budget"],
            "suggested_budget": round(smart_monthly_budget, 2)
        },
        "dca_info": {
            "executed_cycles": 3,
            "total_cycles": 6,
            "monthly_total_eur": PORTFOLIO_CONFIG["baseline_monthly_budget"],
            "next_dca_date": next_dca,
            "days_until_next_dca": days_until_dca,
            "is_active": dca_active,
            "end_date": "2026-11-02"
        },
        "staking_summary": {
            "total_monthly_est_eur": round(total_monthly_staking, 2),
            "total_annual_est_eur": round(total_monthly_staking * 12, 2)
        },
        "projections_nov_2026": projections,
        "assets": assets_summary
    }

    with open("coinbase_portfolio.json", "w", encoding="utf-8") as f:
        json.dump(portfolio_data, f, indent=4, ensure_ascii=False)

    print("[SUCCESS] Coinbase Smart-DCA Portfolio JSON compilado con éxito.")

if __name__ == "__main__":
    calculate_metrics()
