from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import requests
from datetime import datetime, timezone

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAMA_API_BASE = "https://universal-ml-prod.eng.mamamoney.co.za/pub/api/v1"


@app.get("/")
def home():
    return {
        "message": "MoneyRoute Rates API is running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok"
    }


def mama_headers():
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": "https://www.mamamoney.co.za",
        "Referer": "https://www.mamamoney.co.za/",
        "User-Agent": "Mozilla/5.0"
    }


def get_mama_money_quote(method: str, amount: float):
    method = method.upper().strip()
    url = f"{MAMA_API_BASE}/quote/{method}/send/{amount}"

    try:
        response = requests.get(url, headers=mama_headers(), timeout=15)
        response.raise_for_status()
    except requests.RequestException as error:
        raise HTTPException(
            status_code=502,
            detail=f"Could not fetch Mama Money quote: {str(error)}"
        )

    quote = response.json()

    send_amount = quote.get("amount")
    recipient_gets = quote.get("receivableAmount")
    fee = quote.get("customerFee")
    receive_currency = quote.get("payoutCurrency")
    send_currency = quote.get("senderCurrency")
    derived_exchange_rate = quote.get("derivedExchangeRate")

    effective_rate_after_fee = None
    estimated_rate_before_fee = None
    total_customer_cost = None

    if send_amount and recipient_gets:
        effective_rate_after_fee = recipient_gets / send_amount

    if derived_exchange_rate:
        estimated_rate_before_fee = 1 / derived_exchange_rate

    if send_amount is not None and fee is not None:
        total_customer_cost = send_amount + fee

    return {
        "method_id": method,
        "send_amount": send_amount,
        "send_currency": send_currency,
        "fee": fee,
        "fee_type": quote.get("mamaFeeType"),
        "fee_value": quote.get("mamaFeeValue"),
        "total_customer_cost": total_customer_cost,
        "recipient_gets": recipient_gets,
        "receive_currency": receive_currency,
        "effective_rate_after_fee": round(effective_rate_after_fee, 4) if effective_rate_after_fee else None,
        "estimated_rate_before_fee": round(estimated_rate_before_fee, 4) if estimated_rate_before_fee else None,
        "display_rate_after_fee": (
            f"1 {send_currency} = {round(effective_rate_after_fee, 4)} {receive_currency}"
            if effective_rate_after_fee else None
        ),
        "display_rate_before_fee": (
            f"1 {send_currency} = {round(estimated_rate_before_fee, 4)} {receive_currency}"
            if estimated_rate_before_fee else None
        )
    }


@app.get("/partners/mama-money/quote")
def quote_mama_money(
    amount: float = Query(..., gt=0),
    method: str = Query(...)
):
    quote = get_mama_money_quote(method, amount)

    return {
        "success": True,
        "provider": "Mama Money",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "quote": quote
    }
    def clean_institution(item, payout_type):
    return {
        "id": item.get("uniqueId") or item.get("id") or item.get("code"),
        "name": item.get("name"),
        "currency": item.get("currency"),
        "payout_type": payout_type,
        "min_receive_amount": item.get("minTxAmount"),
        "max_receive_amount": item.get("maxTxAmount"),
    }


@app.get("/partners/mama-money/payout-methods/{country_code}")
def get_mama_money_payout_methods(country_code: str):
    country_code = country_code.upper().strip()
    url = f"{MAMA_API_BASE}/institutions/preferred/{country_code}"

    try:
        response = requests.get(url, headers=mama_headers(), timeout=15)
        response.raise_for_status()
    except requests.RequestException as error:
        raise HTTPException(
            status_code=502,
            detail=f"Could not fetch Mama Money payout methods: {str(error)}"
        )

    data = response.json()
    payout_methods = []

    for item in data.get("walletInstitutions", []):
        payout_methods.append(clean_institution(item, "wallet"))

    for item in data.get("bankInstitutions", []):
        payout_methods.append(clean_institution(item, "bank"))

    for item in data.get("cashInstitutions", []):
        payout_methods.append(clean_institution(item, "cash"))

    return {
        "success": True,
        "provider": "Mama Money",
        "country_code": country_code,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "total_methods": len(payout_methods),
        "payout_methods": payout_methods
    }
