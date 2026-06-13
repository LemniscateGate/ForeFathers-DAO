# =============================================================
# WEBERDY API SERVER
# FastAPI HTTP server — live XRPL transaction layer
# ForeFathers DAO LLC — Gabriel Ross
# =============================================================

from __future__ import annotations

import os
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from xrpl.clients import JsonRpcClient
from xrpl.wallet import Wallet
from xrpl.models.transactions import Payment, Memo
from xrpl.transaction import submit_and_wait
from xrpl.models.requests import AccountInfo
from xrpl.utils import xrp_to_drops

# =============================================================
# CONFIG
# =============================================================

XRPL_TESTNET_URL = os.getenv("XRPL_TESTNET_URL", "https://s.altnet.rippletest.net:51234")
XRPL_MAINNET_URL = os.getenv("XRPL_MAINNET_URL", "https://xrplcluster.com")

NETWORK = os.getenv("WEBERDY_NETWORK", "testnet")

def get_client() -> JsonRpcClient:
    if NETWORK == "mainnet":
        return JsonRpcClient(XRPL_MAINNET_URL)
    return JsonRpcClient(XRPL_TESTNET_URL)

def get_wallet(seed_env_key: str) -> Wallet:
    seed = os.getenv(seed_env_key)
    if not seed:
        raise HTTPException(
            status_code=500,
            detail=f"Wallet seed not found in environment: {seed_env_key}"
        )
    return Wallet.from_seed(seed)

# =============================================================
# MEMO BUILDER
# =============================================================

def build_memo(memo_type: str, memo_data: str) -> Memo:
    return Memo(
        memo_type=memo_type.encode("utf-8").hex().upper(),
        memo_data=memo_data.encode("utf-8").hex().upper(),
    )

# =============================================================
# APP
# =============================================================

app = FastAPI(
    title="Weberdy API Server",
    description="ForeFathers DAO — Constitutional XRPL Transaction Layer",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================
# MODELS
# =============================================================

class PaymentRequest(BaseModel):
    from_seed_env_key: str
    to_address: str
    amount_xrp: float
    memo_type: Optional[str] = "weberdy/payment"
    memo_data: Optional[str] = "ForeFathers DAO constitutional payment"

class AccountInfoRequest(BaseModel):
    address: str

# =============================================================
# ROUTES
# =============================================================

@app.get("/")
def root():
    return {
        "system": "Weberdy API Server",
        "entity": "ForeFathers DAO LLC",
        "network": NETWORK,
        "status": "operational",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "governance": "Mathematical Cryptographic Deterministic Constitutional Governance",
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "network": NETWORK,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

@app.get("/network")
def network_info():
    return {
        "network": NETWORK,
        "testnet_url": XRPL_TESTNET_URL,
        "mainnet_url": XRPL_MAINNET_URL,
        "active_url": XRPL_TESTNET_URL if NETWORK == "testnet" else XRPL_MAINNET_URL,
    }

@app.post("/account/info")
def account_info(request: AccountInfoRequest):
    try:
        client = get_client()
        response = client.request(AccountInfo(account=request.address))
        return {
            "status": "success",
            "address": request.address,
            "network": NETWORK,
            "account_data": response.result.get("account_data", {}),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/transaction/payment")
def send_payment(request: PaymentRequest):
    try:
        client = get_client()
        wallet = get_wallet(request.from_seed_env_key)

        memo = build_memo(request.memo_type, request.memo_data)

        tx = Payment(
            account=wallet.classic_address,
            destination=request.to_address,
            amount=xrp_to_drops(request.amount_xrp),
            memos=[memo],
        )

        response = submit_and_wait(tx, client, wallet)
        result = response.result

        return {
            "status": "success",
            "network": NETWORK,
            "from_address": wallet.classic_address,
            "to_address": request.to_address,
            "amount_xrp": request.amount_xrp,
            "tx_hash": result.get("hash"),
            "ledger_index": result.get("ledger_index"),
            "fee": result.get("Fee"),
            "memo_type": request.memo_type,
            "memo_data": request.memo_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "raw_result": result,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/wallets/roster")
def wallet_roster():
    try:
        wallet_json_path = os.path.join(
            os.path.dirname(__file__),
            "../../wallets/weberdy_wallets.testnet.json"
        )
        with open(wallet_json_path, "r") as f:
            wallets = json.load(f)
        return {
            "status": "success",
            "network": NETWORK,
            "wallet_count": len(wallets),
            "wallets": wallets,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================
# ENTRYPOINT
# =============================================================

if __name__ == "__main__":
    uvicorn.run(
        "backend.api.weberdy_api_server:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
    )
