# OCBS Sandbox Guide

This project includes a **mock OCBS sandbox contract** so the market-making, hedging, and auto-execution workflows can be exercised before the real broker API is available.

## Files

- `cw_trading_system/brokers/ocbs_sandbox.py` — in-memory mock broker contract
- `cw_trading_system/brokers/ocbs_mock_sandbox.py` — compatibility wrapper + spec loader
- `cw_trading_system/brokers/ocbs_adapter.py` — request/response mapping layer
- `docs/ocbs_sandbox_openapi.yaml` and `docs/ocbs_mock_sandbox_contract.json` — sample API contract/spec files

## Recommended local settings

Add these to your `.env` when you want to run the trading workflows against the sandbox:

```env
OCBS_ENABLED=true
OCBS_SANDBOX_MODE=true
OCBS_BASE_URL=https://sandbox.ocbs.local
OCBS_API_KEY=demo-key
OCBS_API_SECRET=demo-secret
```

## Supported sandbox endpoints

- `POST /auth/login`
- `POST /orders`
- `GET /orders/{orderId}`
- `DELETE /orders/{orderId}`
- `GET /positions`
- `GET /trades`
- `GET /balance`

## Integration notes

1. Use `OCBSClient()` as usual.
2. When `OCBS_SANDBOX_MODE=true`, the client will route requests to the in-memory sandbox contract instead of making external HTTP calls.
3. When the real OCBS API arrives, keep the trading engines unchanged and update only:
   - `brokers/ocbs_adapter.py`
   - `brokers/ocbs_client.py` config values
   - endpoint names / field maps in the sample spec

## Example

```python
from cw_trading_system.brokers.ocbs_client import OCBSClient

client = OCBSClient()
result = client.place_order({
    "symbol": "HPG24001",
    "side": "buy",
    "quantity": 100000,
    "order_type": "limit",
    "price": 1.25,
})
print(result)
```

Expected sandbox response shape:

```json
{
  "order_id": "SANDBOX-000001",
  "status": "accepted",
  "execution_price": 1.25,
  "filled_quantity": 0,
  "environment": "sandbox"
}
```
