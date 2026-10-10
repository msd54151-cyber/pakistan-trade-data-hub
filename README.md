# Pakistan Trade Data Hub

A small web dashboard for Pakistan's imports and exports, agricultural production and prices. Every figure comes live from an official API or published file. There is **no sample, mock, or fallback data**: if a fetch fails, the panel shows an error. Every panel shows its source, dataset or indicator code, period, official page link and a raw API link.

## Tabs
- **Dashboard**: IMF IMTS monthly exports/imports and top partners; World Bank WDI annual totals and trade % of GDP; UN Comtrade top HS2 products and partners; trade balance (annual and by partner); WITS MFN tariffs (Imports mode).
- **Products**: UN Comtrade drill-down from HS2 to HS4 to HS6, with value, quantity and unit, unit value, share, change vs the previous year, top partners, trend and balance. Breadcrumb and HS search.
- **Agriculture**: FAOSTAT crop production, area, yield and producer prices; agri trade for HS 01–24 and 52.
- **Mandi Prices**: FAO GIEWS FPMA weekly retail prices (data from PBS) plus PMEX daily exchange prices. PMEX prices are futures/spot contracts, **not** physical mandi rates.
- **SPI Weekly**: PBS Sensitive Price Indicator: index, 51 items × 17 cities, fertilizer prices, about 26 weeks of history.
- **Sources**: every source in use, plus the refresh schedule and latest periods.

The global header has controls for Flow (Exports/Imports), Year and Partner country. Your choices persist in the URL and in localStorage.

## Run it
Requires Python 3.10+ (tested with 3.13). Standard library only, no `pip install`.

**Windows:** double-click `app\start-hub.bat`. It starts the server on http://localhost:8080, opens your browser, and restarts the server if it stops.

**macOS / Linux:**
```sh
cd app
python3 server.py            # http://localhost:8080  (HOST / PORT env vars to change)
```
Optional Linux auto-restart: `app/supervise.sh` runs `app/watchdog.sh` every 5 minutes. You can also use cron: `@reboot` plus `*/5 * * * * /path/app/watchdog.sh`.

The first load downloads and caches data in `app/cache/`, which takes a few minutes, mostly for Comtrade and about 50 PBS Excel files.

## Data sources
See **[DATA_SOURCES.md](DATA_SOURCES.md)**: publisher, endpoint, licence, frequency and key requirement for each source. Also included: sources that were researched but not used, and the raw research notes in [sources.md](sources.md). No API keys are needed or stored.

## Refresh schedule (in-process scheduler, Asia/Karachi)
| Source | Schedule (PKT, UTC+5) | UAE time (UTC+4) | Retry |
|---|---|---|---|
| PMEX | Mon–Fri 18:30 | 17:30 | 21:00 PKT (20:00 UAE) if no new trading date |
| PBS SPI | Thu 19:00 | 18:00 | Fri 10:00 PKT (09:00 UAE) if the new file isn't out |
| FAO FPMA | Mon 10:00 | 09:00 | none |
| FAOSTAT (QCL + PP) | Mon 10:00 | 09:00 | none |

These sources refresh only on schedule; a forced refresh bypasses the cache. Comtrade, IMF, WDI and WITS use a 24h cache. Missed slots catch up if the server comes back within 3h. Each run is logged to `app/refresh_log.json`. Panels and the Sources page show "Last refreshed / next scheduled refresh". To trigger a refresh manually from localhost: `curl -X POST "http://localhost:8080/api/refresh?source=pmex|spi|fpma|faostat"`.

## Cloudflare
Cloudflare Pages/Workers **cannot run this Python server as-is**. It needs a long-running process, a local disk cache and a background scheduler thread, and the Workers runtime has none of these. Options:
1. **Cloudflare Tunnel** (simplest): keep `server.py` running on a PC or VPS and expose it with `cloudflared tunnel`.
2. **Port to Workers**: rewrite the `/api/*` proxy in JS/TS (or Python Workers, beta), with the cache in KV/R2/D1 and the schedule in Cron Triggers (UTC: PMEX `30 13 * * 1-5`, retry `0 16 * * 1-5`; SPI `0 14 * * 4`, retry `0 5 * * 5`; FAO `0 5 * * 1`). Serve `app/static` via Pages/Workers static assets. The PBS Excel parsing (`xlsx_lite.py`) and PMEX POST calls would need porting. Some sources (PMEX, PBS) may rate-limit or block Cloudflare egress IPs, so test that first.

## Licence notes
The data stays under each publisher's terms (see DATA_SOURCES.md). PMEX publishes no data licence and is used for reference only.
