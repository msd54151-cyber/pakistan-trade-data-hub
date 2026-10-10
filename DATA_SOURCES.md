# Pakistan Trade Data Hub: data sources

Generated 2026-10-10 (GST). The Sources page in the app renders from the same file (`app/static/sources.json`) and shows the latest period live from each API's response.

**No sample data:** every number on every panel comes from the live API/official file below, cached on disk (24h; PMEX 3h; SPI daily). If a fetch fails the panel shows an error. There are no stale-cache, mock, or zero-filled fallbacks.

## Sources used

### UN Comtrade: public preview API
- **Publisher:** United Nations Statistics Division
- **Used for:** Dashboard: top HS2 products and partners, balance by partner; Products: HS2/HS4/HS6 drill-down, quantities, partners, trends, product balance; Agriculture: agri trade (HS 01–24, 52)
- **Endpoint / file pattern:** `https://comtradeapi.un.org/public/v1/preview/C/A/HS?reporterCode=586&period={year}&partnerCode={p}&flowCode={X|M}&cmdCode={AG2|TOTAL|code list}  ·  /public/v1/getDA/C/A/HS?reporterCode=586  ·  reference: /files/v1/app/reference/{HS,partnerAreas,QuantityUnits}.json`
- **Official page:** https://comtradeplus.un.org/
- **Licence / terms:** UN Comtrade terms of use (free preview tier, max 500 rows per call; attribution required)
- **Frequency:** Annual (as reported by Pakistan)
- **Latest period loaded (2026-10-10):** 2025 (annual; years list from Comtrade getDA)
- **Key needed:** No (preview); full data/v1 API needs a free key

### IMF International Trade in Goods (IMTS, formerly DOTS)
- **Publisher:** International Monetary Fund
- **Used for:** Dashboard: monthly exports/imports (World or partner), top partners, annual trade balance
- **Endpoint / file pattern:** `https://api.imf.org/external/sdmx/3.0/data/dataflow/IMF.STA/IMTS/+/PAK.{XG_FOB_USD|MG_CIF_USD}.{G001|ISO3|*}.{M|A}`
- **Official page:** https://data.imf.org/en/datasets/IMF.STA:IMTS
- **Licence / terms:** IMF data terms (free use with attribution)
- **Frequency:** Monthly and annual
- **Latest period loaded (2026-10-10):** monthly to 2026-M06; annual to 2025
- **Key needed:** No

### World Bank World Development Indicators (WDI)
- **Publisher:** World Bank
- **Used for:** Dashboard: headline cards, annual trade chart, goods balance line, trade % of GDP
- **Endpoint / file pattern:** `https://api.worldbank.org/v2/country/PAK/indicator/{TX.VAL.MRCH.CD.WT|TM.VAL.MRCH.CD.WT|NE.EXP.GNFS.CD|NE.IMP.GNFS.CD|NE.TRD.GNFS.ZS}?format=json&date=1990:2030`
- **Official page:** https://data.worldbank.org/country/pakistan
- **Licence / terms:** CC BY 4.0
- **Frequency:** Annual
- **Latest period loaded (2026-10-10):** 1990–2025
- **Key needed:** No

### WITS: UNCTAD TRAINS tariffs
- **Publisher:** World Bank / UNCTAD
- **Used for:** Dashboard (Imports mode): MFN tariffs by HS2 (hub-aggregated from HS6)
- **Endpoint / file pattern:** `https://wits.worldbank.org/API/V1/SDMX/V21/datasource/TRN/reporter/586/partner/000/product/all/year/{year}/datatype/reported`
- **Official page:** https://wits.worldbank.org/CountryProfile/en/PAK
- **Licence / terms:** WITS terms (free, attribution)
- **Frequency:** Annual (lags; nearest earlier year used)
- **Latest period loaded (2026-10-10):** 2023 (latest TRAINS year)
- **Key needed:** No

### FAOSTAT Crops and livestock products (QCL), bulk file
- **Publisher:** FAO
- **Used for:** Agriculture: production, area, yield by crop
- **Endpoint / file pattern:** `https://bulks-faostat.fao.org/production/Production_Crops_Livestock_E_Asia.zip (area code 165)`
- **Official page:** https://www.fao.org/faostat/en/#data/QCL
- **Licence / terms:** CC BY 4.0 (FAO)
- **Frequency:** Annual
- **Latest period loaded (2026-10-10):** 1961–2024
- **Key needed:** No (FAOSTAT REST API now needs auth, so the bulk file is used)

### FAOSTAT Producer Prices (PP), bulk file
- **Publisher:** FAO
- **Used for:** Agriculture: farm-gate producer price (PKR/t)
- **Endpoint / file pattern:** `https://bulks-faostat.fao.org/production/Prices_E_Asia.zip (element 5530, annual value)`
- **Official page:** https://www.fao.org/faostat/en/#data/PP
- **Licence / terms:** CC BY 4.0 (FAO)
- **Frequency:** Annual
- **Latest period loaded (2026-10-10):** 1991–2024 (annual)
- **Key needed:** No

### FAO GIEWS FPMA Tool (data: PBS)
- **Publisher:** FAO GIEWS / Pakistan Bureau of Statistics
- **Used for:** Mandi Prices: weekly retail wheat flour and rice, 5 cities
- **Endpoint / file pattern:** `https://fpma.fao.org/giews/v4/price_module/api/v1/FpmaSerieDomestic/?country_iso3=PAK  ·  /FpmaSeriePrice/{uuid}/`
- **Official page:** https://fpma.fao.org/giews/fpmat4/
- **Licence / terms:** FAO terms of use (attribution)
- **Frequency:** Weekly
- **Latest period loaded (2026-10-10):** week of 2026-09-25
- **Key needed:** No

### PMEX OHLC report (exchange prices)
- **Publisher:** Pakistan Mercantile Exchange
- **Used for:** Mandi Prices: daily agri futures/spot contracts and warehouse receipts (NOT physical mandi rates)
- **Endpoint / file pattern:** `POST https://mportal.pmex.com.pk/mt5bonew/Home/GetOHLC (txtFromDate, txtEndDate; ≤1 month per call); undocumented JSON behind the public report page`
- **Official page:** https://mportal.pmex.com.pk/mt5bonew/Home/OHLCReport
- **Licence / terms:** No data licence published; used for reference only
- **Frequency:** Daily (trading days)
- **Latest period loaded (2026-10-10):** 2026-07-10 – 2026-10-09 (latest trading day 2026-10-09)
- **Key needed:** No

### PBS Sensitive Price Indicator (SPI) weekly Annex + Report (Excel)
- **Publisher:** Pakistan Bureau of Statistics
- **Used for:** SPI Weekly tab: index, 51 items × 17 cities, fertilizer prices
- **Endpoint / file pattern:** `https://www.pbs.gov.pk/wp-content/uploads/2020/07/Annex_{DD.MM.YYYY}.xlsx  ·  3.-SPI-Report-{DD.MM.YYYY}.xlsx (latest discovered from the price-statistics page)`
- **Official page:** https://www.pbs.gov.pk/price-statistics/
- **Licence / terms:** Government of Pakistan official statistics (public; attribution to PBS)
- **Frequency:** Weekly (Thursday)
- **Latest period loaded (2026-10-10):** week ending 2026-10-08 (24 weeks loaded, 2026-04-16 → 2026-10-08)
- **Key needed:** No

## Researched but not used

| Source | Why not | Link |
|---|---|---|
| UN Comtrade full API (data/v1) | Needs a free subscription key (401 without one) | https://comtradedeveloper.un.org |
| WTO Timeseries API | Needs a free key (401 without one) | https://apiportal.wto.org |
| SBP EasyData | Needs an API key; Cloudflare 403 from the server | https://easydata.sbp.org.pk |
| USDA FAS PSD | Works with the public DEMO_KEY only; needs an api.data.gov key | https://apps.fas.usda.gov/opendatawebV2/ |
| OEC (BACI) | Keyless, but mirror-reconciled (not official PAK-reported) | https://oec.world/en/resources/documentation |
| WFP food prices: HDX CSV / HDX HAPI | CSV is S3 403; HAPI works (monthly, to 2026-08-15) but was not selected | https://data.humdata.org/dataset/wfp-food-prices-for-pakistan |
| WFP DataBridges | Needs a WFP API key (legacy gateway decommissioned) | https://docs.api.wfp.org |
| World Bank Pink Sheet | Downloadable (world prices); not used yet | https://www.worldbank.org/en/research/commodity-markets |
| AMIS Punjab (amis.pk) | Daily mandi rates as web pages only; timed out from the server; no licence found | http://www.amis.pk/ |
| PAR / Zarai Mandi API | Daily mandi API; paid key (pending) | https://www.par.com.pk/apidocs/cotton/daily-prices |
| KCA cotton spot rate | Daily, but HTML via news sites only; KCA site timed out | https://www.brecorder.com/trends/kca-spot-rates |
| Lahore DC rate lists / Qeemat Punjab | Daily, but images or app only | https://lahore.punjab.gov.pk/market_rates |
| PBS trade releases, Customs/WeBOC, ITC Trade Map | No public data API | https://www.pbs.gov.pk |
| Commodities-API, TradingEconomics | Paid | https://commodities-api.com |
| data.gov.pk, opendata.com.pk, provincial agri/food sites, PSMA, TCP, PCGA, Kissan apps | No usable API (404/timeouts/static old datasets) | https://opendata.com.pk |
