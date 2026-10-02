# Business case

### Beyond Earth — cycle-aware irrigation screening
Arab Youth Space Hackathon 2026, 813 Challenge · Criterion 7

**Every figure below is marked.** `MEASURED` comes from our own run over Wadi as-Sirhan and can be reproduced from the notebook. `ASSUMPTION` is a stated modelling choice with its reasoning; it is not researched market data and should be replaced with the operator's real numbers before anyone signs anything. We would rather show the shape of the model with honest labels than present invented precision.

---

## 1. The problem someone will pay to fix

Wadi as-Sirhan runs on fossil groundwater that does not recharge. Water is the binding input, and the operational question every week is the same: **of the fields that look bad from the office, which ones actually need me?**

Satellite vegetation indices are already used for this. They answer the question wrongly here, because alfalfa is cut on a ~30-day cycle and a freshly mown field is indistinguishable from a failing one in NDVI.

`MEASURED` Across a full season over 518 detected pivots, a decline-ranked queue puts **between 11 and 17 of its top 20** on fields that had simply been cut, at every date tested. On 22 July 2026, **57 of the 518 fields were mid-cut**. A decline-ranked irrigation queue would have placed every one of them at the top. They needed nothing.

That 16% is the waste our product removes. It is not a projection; it is a count from one date in one box.

---

## 2. Who buys it

| Segment | What they get | Why they pay |
|---|---|---|
| **Pivot operators** (the farms themselves) | A weekly queue: which fields to inspect first, and why | Scouting time is the scarce resource; sending an agronomist to a mown field costs a day |
| **Water regulators** (e.g. Saudi MEWA, UAE ADAFSA) | Area-wide view of which hectares are being irrigated while already failing | Allocation and enforcement need evidence, per field, repeatable |
| **Agricultural lenders and insurers** | Portfolio crop condition without site visits | Underwriting and loss adjustment on land they cannot walk |
| **Farm-management platforms** | The `/priority` endpoint behind their existing UI | They own the customer; they lack the cycle model |

The first two are the buyers for a pilot. The fourth is how this scales without building a sales force — the API exists precisely so the ranking can live inside software a farm already uses.

---

## 3. What it costs to run

`MEASURED` One AOI-season — 67 × 61 km, 518 fields, 82 Sentinel-2 dates, 33,078 field-days. The Sentinel-2 pipeline completed in **under 7 minutes** on a free-tier cloud notebook including all imagery reads; on a home connection the same work is bound by download speed rather than compute and takes considerably longer.

`MEASURED` Sentinel-2 and EMIT are free and openly licensed. There is no data cost.

`ASSUMPTION` On commodity cloud compute at roughly $0.10/hour equivalent, the marginal cost of one AOI-season is **well under $1**, dominated by object-storage reads rather than CPU. Weekly incremental updates cost a fraction of that, because only new dates are processed.

The economics are unusual and worth stating plainly: **the marginal cost of adding a field is effectively zero.** Cost scales with area processed, not customers served, and area processed is cheap. That is a gross-margin profile closer to software than to agronomy services.

`ASSUMPTION` Fixed costs are the real ones: engineering, validation fieldwork, and support. A two-person team can run the platform for a region; a validation programme with one cooperating operator is the one genuinely expensive line item.

---

## 4. Pricing

`ASSUMPTION` Per hectare per season, the standard shape in precision agriculture, because it scales with the value delivered and is a line item buyers already understand.

| Tier | Shape | Rationale |
|---|---|---|
| **Operator** | per hectare per season, with a floor | Aligns price to farmed area; a 23,000 ha operator pays more than a 500 ha one |
| **Regulator / enterprise** | annual licence per monitored region | They need area coverage, not per-field billing |
| **Platform / API** | per call or per monitored hectare, wholesale | They resell; margin is shared |

We have deliberately not put a number on the hectare rate. Setting it requires knowing what one avoided inspection is worth to a specific operator, and we do not have that from a farm yet. Establishing it is the first commercial question a pilot answers, and it is a question with a concrete method: run the queue for one season alongside the operator's existing scouting and count the visits saved.

---

## 5. Why this is defensible

**It is not the model, it is the discipline.** Anyone can compute NDVI. What is hard to copy is having tested the obvious approach and found it wrong, in public, with the leakage check attached. Our methodology report includes a result that overturned our own headline finding (§5.3 there). That is the asset: a product whose claims survive being checked.

**The cycle model is crop-specific and transferable.** The phase logic — peaks, prominence, expected-value-at-phase, deficit — is not alfalfa-only. Any crop with a repeating harvest or cutting rhythm (forage grasses, some vegetables, cut flowers) has the same confound and the same fix.

**No proprietary data dependency.** We are not reselling imagery and have no supplier who can change terms. Sentinel-2's free licence is the moat's floor.

---

## 6. What we would do with an incubation place

1. **Validation with one operator, one season.** Irrigation records against our queue. This converts a screening tool into a measured one and produces the pricing anchor in §4.
2. **Regional scale-up.** The same pipeline over the full Wadi as-Sirhan belt and one UAE region. A compute cost, not a research cost.
3. **Deploy the API properly.** Authentication, rate limits, a published OpenAPI spec, and a reference integration with one farm-management platform.
4. **More hyperspectral scenes.** Six to eight matched EMIT acquisitions would settle the question our PoC left open. Upside, not dependency.

---

## 7. Honest risks

| Risk | Where it bites | What we would do |
|---|---|---|
| **No ground truth yet** | Every claim is a screening claim. A buyer will ask "how often is it right?" and today we can only answer "we have not measured that" | Step 1 above exists for exactly this |
| **Cloud gaps** | A long clear-sky gap can misplace a field's last cut and shift its phase | Al Jouf gave 85 usable days in seven months; a wetter region would need the model relaxed |
| **Free imagery is a policy, not a contract** | Copernicus terms could change | Landsat and commercial optical are drop-in at lower cadence; the method does not depend on one sensor |
| **The buyer may already have an agronomist who knows** | On a small farm the manager knows which fields were cut | Value rises with area. Below a few hundred hectares this is a nice-to-have; at 20,000 hectares it is not |

That last row is the one we would lead with in a pitch, because it tells the buyer honestly where the product does and does not earn its price.
