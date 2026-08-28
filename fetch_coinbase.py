import requests
import json
import datetime
import os

# Parametrización G-CORE basada en el estado real de Coinbase e Inversiones 2026
PORTFOLIO_CONFIG = {
    "currency": "EUR",
    "dca_end_date": "2026-11-02",
    "dca_day_of_month": 2,
    "assets": {
        "DOT": {
            "name": "Polkadot",
            "balance": 1282.6527477,
            "cost_basis": 1.59, # Coste medio ponderado Coinbase
            "dca_monthly_budget": 0.0,
            "dca_weight_pct": 0,
            "staking_enabled": True
        },
        "BTC": {
            "name": "Bitcoin",
            "balance": 0.01266575,
            "cost_basis": 60021.78,
            "dca_monthly_budget": 183.50,
            "dca_weight_pct": 40,
            "staking_enabled": False
        },
        "ETH": {
            "name": "Ethereum",
            "balance": 0.34608017,
            "cost_basis": 1777.71,
            "dca_monthly_budget": 137.63,
            "dca_weight_pct": 30,
            "staking_enabled": True
        },
        "SOL": {
            "name": "Solana",
            "balance": 5.84408757,
            "cost_basis": 82.01,
            "dca_monthly_budget": 91.75,
            "dca_weight_pct": 20,
            "staking_enabled": True
        },
        "LINK": {
            "name": "Chainlink",
            "balance": 19.98997167,
            "cost_basis": 6.89,
            "dca_monthly_budget": 45.88,
            "dca_weight_pct": 10,
            "staking_enabled": False
        }
    }
}

def fetch_prices():
    prices = {}
    tickers = {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "LINK": "chainlink", "DOT": "polkadot"}
    ids = ",".join(tickers.values())
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=eur"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        for symbol, cg_id in tickers.items():
            if cg_id in data and "eur" in data[cg_id]:
                prices[symbol] = float(data[cg_id]["eur"])
    except Exception as e:
        print(f"[WARN] Error consultando feed de precios CoinGecko: {e}")
        # Fallback de respaldo con cotizaciones actuales Coinbase
        prices = {"DOT": 0.7479, "BTC": 68200.27, "ETH": 2141.37, "SOL": 91.37, "LINK": 10.09}
    return prices

def calculate_metrics():
    prices = fetch_prices()
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
            "staking": config["staking_enabled"]
        })

    net_pnl_eur = total_value_eur - total_cost_eur
    net_pnl_pct = (net_pnl_eur / total_cost_eur * 100) if total_cost_eur > 0 else 0.0

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

    portfolio_data = {
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "total_value_eur": round(total_value_eur, 2),
        "total_cost_eur": round(total_cost_eur, 2),
        "net_pnl_eur": round(net_pnl_eur, 2),
        "net_pnl_pct": round(net_pnl_pct, 2),
        "mtd_pct": 2.40,
        "ytd_pct": 14.85,
        "dca_info": {
            "executed_cycles": 3,
            "total_cycles": 6,
            "monthly_total_eur": 458.76,
            "next_dca_date": next_dca,
            "days_until_next_dca": days_until_dca,
            "is_active": dca_active,
            "end_date": "2026-11-02"
        },
        "assets": assets_summary
    }

    with open("coinbase_portfolio.json", "w", encoding="utf-8") as f:
        json.dump(portfolio_data, f, indent=4, ensure_ascii=False)

    historial = []
    if os.path.exists("historial_coinbase.json"):
        try:
            with open("historial_coinbase.json", "r", encoding="utf-8") as hf:
                historial = json.load(hf)
        except Exception:
            historial = []

    historial.append({
        "date": now.strftime("%Y-%m-%d"),
        "value": round(total_value_eur, 2),
        "cost": round(total_cost_eur, 2),
        "pnl": round(net_pnl_eur, 2)
    })

    with open("historial_coinbase.json", "w", encoding="utf-8") as hf:
        json.dump(historial, hf, indent=4, ensure_ascii=False)

    print("[SUCCESS] Archivos json actualizados correctamente.")

if __name__ == "__main__":
    calculate_metrics()
