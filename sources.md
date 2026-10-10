# Pakistan Trade Data Hub: Source Audit (tested 2026-10-10, from /workspace with curl)

Legend: ✅ tested & worked · ⚠️ partly tested · ❌ blocked/failed · UNTESTED = not verified

| Source | API? | Auth | Tested result |
|---|---|---|---|
| UN Comtrade | Yes (REST/JSON) | `/public/*` preview: no key. `/data/v1/get`: **key needed** (`Ocp-Apim-Subscription-Key`, free tier at comtradedeveloper.un.org) | ✅ preview, ❌ 401 without key |
| WITS (World Bank) | Yes (SDMX 2.1 XML + WITS XML) | None | ✅ |
| IMF IMTS (formerly DOTS) | Yes (SDMX 3.0 at api.imf.org) | None for this test | ✅ |
| World Bank WDI | Yes (REST JSON/XML) | None | ✅ |
| WTO Timeseries | Yes | **Key needed** (apiportal.wto.org, free) | ❌ 401 without key |
| OEC | Yes (Tesseract/OLAP) | No key needed for the test below (heavier use may need a token: UNTESTED) | ✅ |
| SBP EasyData | Yes (Developer Guide + metadata API listed on the portal; third-party packages use an EasyData API key) | Free registration, API key | ❌ Cloudflare 403 from box; endpoints UNTESTED |
| PBS trade releases | No API found. Monthly PDF/Excel releases on pbs.gov.pk | n/a | ❌ guessed URLs 404; UNTESTED |
| Pakistan Customs / WeBOC | No public data API found (transaction system for traders) | Login | ❌ connection failed (HTTP 000) |
| ITC Trade Map | No open API. Web UI; free registration; bulk/API access is by arrangement | Login | ⚠️ only the homepage loaded (200) |

## 1. UN Comtrade
- Base: `https://comtradeapi.un.org/` (`public/v1/preview`, `public/v1/getDA`, `data/v1/get` needs a key)
- Ran: `public/v1/preview/C/A/HS?reporterCode=586&period=2023&partnerCode=0&flowCode=M&cmdCode=TOTAL`
  → `"reporterCode":586,"flowCode":"M","classificationCode":"H6","primaryValue":50009391529.141` (PAK imports 2023 ≈ US$50.0bn)
- Ran: `data/v1/get/C/A/HS?reporterCode=586&period=2023` → `401 "Access denied due to missing subscription key"`
- Availability (`getDA`): annual data 2003–**2025** (2025 released 2026-05-29, HS H6); monthly: 193 periods, latest **2026-01** (released 2026-05-16).
- Coverage: by partner country, HS 2/4/6-digit, quantities, CIF/FOB. Preview returns at most 500 rows.
- Docs: https://comtradedeveloper.un.org , https://uncomtrade.org/docs/

## 2. WITS
- Base: `https://wits.worldbank.org/API/V1/`
- Ran: `SDMX/V21/datasource/tradestats-trade/reporter/pak/year/2022/partner/wld/product/all/indicator/XPRT-TRD-VL`
  → `<Obs TIME_PERIOD="2022" OBS_VALUE="926568.434796" DATASOURCE="WITS-CMT" />` (US$ thousand, by product group)
- Ran: `wits/datasource/trn/dataavailability/country/586/year/all` → TRAINS tariff data for PAK from 1995 (H0 onward).
- Coverage: Comtrade-derived trade stats (product groups, partners) plus TRAINS tariffs. Latest year: UNTESTED (2022 confirmed).
- Docs: https://wits.worldbank.org/witsapiintro.aspx

## 3. IMF IMTS (formerly DOTS)
- Base: `https://api.imf.org/external/sdmx/3.0/` (the old dataservices.imf.org did not respond: HTTP 000)
- Ran: `data/dataflow/IMF.STA/IMTS/+/PAK.XG_FOB_USD.G001.M?lastNObservations=3`
  → 2026-M04: 2,241,803,851; 2026-M05: 2,416,408,848; 2026-M06: 2,551,639,712 (USD, exports FOB; G001 is assumed to be World, not checked against the codelist)
- Coverage: monthly/quarterly/annual merchandise totals by partner country. **No product detail.** Latest period: **2026-M06**.
- Docs: https://data.imf.org , https://portal.api.imf.org

## 4. World Bank WDI
- Base: `https://api.worldbank.org/v2/`
- Ran: `country/PAK/indicator/TM.VAL.MRCH.CD.WT?format=json&mrv=3` → `"date":"2025","value":65849000000` (merchandise imports); `NE.EXP.GNFS.CD` 2025 = 40,670,467,311.9; lastupdated 2026-10-08.
- Coverage: annual country-level indicators only. Latest **2025**.
- Docs: https://datahelpdesk.worldbank.org/knowledgebase/articles/889392

## 5. WTO Timeseries
- Base: `https://api.wto.org/timeseries/v1/`
- Ran: `data?i=ITS_MTV_AX&r=586&ps=2023` (no key) → `401 missing subscription key`. **Needs a free key.** Content and freshness UNTESTED.
- Docs: https://apiportal.wto.org

## 6. OEC
- Base: `https://api-v2.oec.world/tesseract/` (also `oec.world/api/olap-proxy/`)
- Ran: `data.jsonrecords?cube=trade_i_baci_a_92&drilldowns=Year&measures=Trade+Value&Exporter+Country=aspak&Year=2022`
  → `{"Year":2022,"Trade Value":39795963391.0}`; dataset "HS6 REV. 1992 (1995 - 2024)" (CEPII BACI)
- Coverage: BACI is a reconciled (mirror-adjusted) dataset, not official PAK-reported figures. HS6, by partner. Latest **2024**.
- Docs: https://oec.world/en/resources/documentation

## 7. SBP EasyData
- Portal: https://easydata.sbp.org.pk (Developer Guide; news item "Dataset level metadata API is now available" dated 19-Feb-2025)
- curl got a Cloudflare "Attention Required" page (403) for both the portal and a guessed API path. Endpoint format, series codes and latest period are UNTESTED. Needs a registered account and API key; try from a normal browser or IP.
- Expected coverage (UNVERIFIED): monthly exports/imports of goods and services, BoP, country-wise and commodity-group-wise trade. This is the most timely official source.
- Unofficial clients: https://pypi.org/project/EasyDataPy/ , https://github.com/drateeb/EasyDataR

## 8. PBS
- https://www.pbs.gov.pk (trade statistics section). No API found. Releases are monthly PDF/Excel files. Guessed paths returned 404, so the exact release URLs are UNTESTED. Integrating PBS means scraping or downloading the files.

## 9. Pakistan Customs / WeBOC
- https://www.weboc.gov.pk did not respond to curl (HTTP 000). No public statistical API found. It is a transactional system and not a viable hub source. UNTESTED beyond that.

## 10. ITC Trade Map
- https://www.trademap.org loads (Angular app). No public API is documented. Data access needs a login, and bulk access is commercial or by request. UNTESTED.

# Agriculture & market price sources (tested 2026-10-10)
| Source | Result |
|---|---|
| FAOSTAT REST API (faostatservices.fao.org/api/v1) | ❌ 401 "Missing Authorization Header"; old fenixservices host returns 521 |
| FAOSTAT bulk download (bulks-faostat.fao.org) | ✅ keyless. QCL Asia zip (file date 2025-12-23): Pakistan (area 165) 1961–2024, e.g. wheat production 2024 = 31,814,444 t. PP Asia zip (file date 2026-10-09): producer prices in PKR/t, annual and monthly |
| USDA FAS PSD (api.fas.usda.gov/api/psd) | ✅ works with the public DEMO_KEY (rate-limited); the old apps.fas.usda.gov endpoint gives 403 "Bad API Key". Needs a free api.data.gov key for production use |
| FAO GIEWS FPMA (fpma.fao.org/giews/v4/price_module/api/v1) | ✅ keyless REST. 19 Pakistan series (PBS retail; 5 cities; wheat flour and rice), WEEKLY, latest 2026-09-25. Plain-wheat series ended 2021-10-29 |
| WFP food prices on HDX (CKAN package_show) | ⚠️ metadata ✅ (last modified 2026-10-04, data to 2026-08-15, CC BY-IGO), but the CSV download → S3 403 AccessDenied from the box |
| World Bank Pink Sheet (CMO monthly xlsx) | ✅ 200 (xlsx, world prices, monthly). Not used yet |
| PBS SPI weekly | No API; PDFs on pbs.gov.pk (the URL tried returned 404). FPMA republishes the PBS retail series |
| AMIS Punjab (amis.pk) | Daily wholesale mandi prices exist (ViewPrices.aspx, dated 10-10-2026 per search index). HTML pages only, no API. Connection timed out from the box. Terms page not found (404). Not integrated |
| PAR / Zarai Mandi | Daily mandi API documented (par.com.pk/api/v2, needs x-par-secret-key, commercial). UNTESTED (no key) |
| Kissan Dost, KissanCares, Sindh/KP market committees | Websites/apps only; no public API found |

# Other daily mandi / agri price sources (tested 2026-10-10 from the box)

| Rank | Source | Daily? | API? | Key / cost | Coverage | Latest seen | Terms | Tested example |
|---|---|---|---|---|---|---|---|---|
| 1 | **PMEX OHLC report** (mportal.pmex.com.pk) | ✅ daily (trading days) | Undocumented JSON endpoint behind the public report page (`POST /mt5bonew/Home/GetOHLC`, ≤3-month window) | None | Local agri futures/spot: PKWHEAT LD/SD, WHEAT, MAIZE LD/SD, LGMRRICE, SUGAR, PALMOLEIN, plus EWR warehouse-receipt contracts (maize, rice, etc.), and intl ICOTTON/IWHEAT/ICORN. Exchange prices, not mandi | 2026-10-09 | No published data licence; it is a public report but not an official API. Ask PMEX before production use. JSON keys are mislabelled (`Trader_Id`=symbol, `Post_Date`=date) | 200, 1,417 rows for 1–10 Oct; 164 agri rows, e.g. `LGMRRICE-NO26 … 8950 … 01/10/2026` |
| 2 | **PBS SPI weekly Annex (Excel)** | ❌ weekly (Thursday) | No API, but a stable xlsx per release (`/wp-content/uploads/2020/07/Annex_DD.MM.YYYY.xlsx`), linked from the release page | None | 51 essential items × 17 cities, MIN/AVG/MAX (wheat flour, rice, pulses, sugar, ghee, vegetables, etc.); Appendix B has fertilizer prices by city | week ended 2026-10-08 (published 09-10) | Official govt statistics, public | 200 xlsx 57 KB; openpyxl parses it cleanly: `Wheat Flour Bag 20 Kg, Islamabad MIN 3306.67 AVG 3364.33 MAX 3400`. The PDF also parses with pdftotext -layout, but the Excel is more reliable |
| 3 | **HDX HAPI food prices** (hapi.humdata.org) | ❌ monthly | ✅ REST JSON | Free; just a base64 `app_identifier` (no key) | WFP monthly retail prices for 5 cities, ~15 commodities incl. fuel and wages; 9,398 rows from 2017 | 2026-08-15 | CC BY-IGO | 200: `Lahore, Ghee (artificial), 632 PKR/KG, 2026-08-15`. Fixes the HDX CSV problem (that link is still S3 403) |
| 4 | **KCA official cotton spot rate** | ✅ daily (suspended Dec 2025 – Jun 2026, resumed) | ❌ (kcapk.org timed out from the box); republished daily by Business Recorder (brecorder.com/trends/kca-spot-rates) and khistocks.com | None | Cotton lint spot rate Rs/37.324 kg and /40 kg, ex-gin, upcountry | 2026-10-08 (Rs 18,680/37.324 kg) | News republication; scraping needs permission | BR and khistocks pages return 200 (HTML only) |
| 5 | **Lahore DC market rate lists** (lahore.punjab.gov.pk/vegetables-rate-list, also fruits/poultry/commodities) | ✅ daily | ❌ images only (WhatsApp JPEGs, OCR needed) | None | Official DC-notified retail rates, Lahore; other district sites are likely similar (untested) | image dated 2026-10-10 | Govt public notice | 200; files like `WhatsApp Image 2026-10-10 at 6.32.14 AM.jpeg` |
| 6 | FAO GIEWS FPMA (already integrated) | ❌ weekly | ✅ | None | Wheat flour and rice retail, 5 cities | 2026-09-25 | FAO terms | see above |
| – | Qeemat Punjab (PITB) / DG Industries, Prices (doi.punjab.gov.pk) | ✅ daily DC price lists | App only; no public API found | – | Punjab districts, fruits/vegetables/essentials | UNTESTED (app) | – | doi site 200, links only to the app |
| – | WFP DataBridges API | monthly | ✅ (new gateway) | Needs a WFP API key (OAuth). Legacy api.wfp.org returns 401 "decommissioned" | same WFP data as HDX | – | – | 401 |
| – | Commodities-API | – | ✅ | Paid key (401 without one); Pakistan local mandi coverage UNVERIFIED (world benchmarks) | – | – | commercial | 401 invalid_access_key |
| – | TradingEconomics | – | ✅ | Paid (guest account discontinued, 410) | – | – | commercial | 410 |
| – | data.gov.pk | – | CKAN API path 404 | – | – | – | – | 404 |
| – | opendata.com.pk (CKAN) | ❌ static | ✅ CKAN | None | Old one-off PBS/NCBC price datasets (e.g. "Sensitive Price Index Prices June 2017 – July 2019", wheat price 2020-21) | metadata 2021–2025 | varies | package_search 200, 40 price datasets |
| – | Punjab Agri Dept / CRS, Punjab Food Dept, Sindh Agriculture, KP Agriculture, Balochistan Agri, Punjab open data, KCA site | ? | none found | – | – | UNREACHABLE: all timed out (HTTP 000) from the box; may be geo/IP-blocked | – | 000 |
| – | ICT Administration price lists | daily notifications (per news) | none | – | – | site 200, the URL tried 404; UNTESTED | – | – |
| – | PSMA (sugar), TCP, PCGA | ❌ | none; press releases/tenders | – | – | PSMA 200, TCP 200, PCGA 406 | – | – |
| – | Kisan Ghar, Agri Mandi, Mandi Rates PK, Zameen Agri, Kissan Dost, KissanCares | claim daily | no public API found | – | aggregators; KissanCares labels rows "AMIS Verified" | UNTESTED via curl | app ToS; unverified provenance | – |
