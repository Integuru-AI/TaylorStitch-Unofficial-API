# TaylorStitch Unofficial API

Unofficial Python integrations for TaylorStitch.

## Integrations

- `taylorstitch_add_to_cart.py` - `add_to_cart`.
- `taylorstitch_list_orders.py` - `list_orders`.
- `taylorstitch_list_new_arrivals.py` - `list_new_arrivals`.

## Usage

Each file exposes a `run(input, context)` or `run(headers, input)` style entrypoint, matching the source integration runtime.
Authenticated request headers/cookies are expected to be supplied by the caller when required.

Install dependencies:

```bash
pip install -r requirements.txt
```

## Info

This unofficial API is built by [Integuru.ai](https://integuru.ai/).

For custom requests or hosted authentication, contact richard@taiki.online.

See the [complete list of APIs by Integuru](https://github.com/Integuru-AI/APIs-by-Integuru).
