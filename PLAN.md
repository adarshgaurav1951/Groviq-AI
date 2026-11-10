# BarcodeLess Produce Assistant

## Production-Ready Product, Engineering, and Delivery Plan

**Document type:** Product + technical execution plan\
**Version:** 1.0\
**Date:** 10 November 2026\
**Status:** Initial product blueprint --- validate with a pilot retailer
before production rollout

------------------------------------------------------------------------

## 1. Executive Summary

BarcodeLess Produce Assistant is a computer-vision-powered produce
identification and checkout-assistance platform. A shopper or cashier
presents loose fruit or vegetables to a camera. The system detects the
item, ranks likely product matches, maps the selected item to the
retailer's product/PLU catalog, obtains a verified weight from a
connected scale, calculates the price using the retailer's pricing
system, and adds the line item to a checkout basket.

The product should be built as a **retail workflow platform with an AI
recognition component**, not as a standalone image classifier.
Recognition confidence, catalog correctness, scale integration, price
integrity, auditability, operational monitoring, and a safe human
fallback are all first-class requirements.

### Product promise

-   Reduce manual produce lookup and key-entry time.
-   Help shoppers and cashiers identify loose produce consistently.
-   Reduce avoidable selection mistakes and produce-related checkout
    friction.
-   Integrate with existing point-of-sale (POS), product catalog,
    scales, and store operations.
-   Operate reliably at the checkout lane, including during intermittent
    network connectivity.

### Important boundary

The initial release is **assisted self-checkout**, not autonomous
checkout. It identifies likely produce and recommends a catalog item;
the shopper or cashier confirms when required. It does not independently
charge a payment method, make claims about organic status, infer product
origin, or replace a legally compliant weighing instrument.

------------------------------------------------------------------------

## 2. Industry Research and Competitive Benchmark

The following are public product and engineering references. They
demonstrate market direction, not access to proprietary architectures or
proof that this project can match their performance without equivalent
data, hardware, integrations, and validation.

### 2.1 Toshiba Global Commerce Solutions --- ELERA Produce Recognition

Toshiba publicly describes ELERA Produce Recognition as AI-enabled
identification of non-barcoded produce at checkout. Its stated benefits
include reducing manual product-code entry, checkout time, and
produce-related shrink.

**What to learn** - Embed recognition in the checkout workflow instead
of making it a separate demo. - Present likely product choices at the
moment produce is weighed. - Treat loss prevention and item validation
as part of the workflow. - Design for edge deployment and store-level
operations.

Reference: [Toshiba ELERA Produce
Recognition](https://commerce.toshiba.com/wps/portal/marketing/iot-suite/produce-recognition/)

### 2.2 NCR Voyix --- Picklist Assist and Self-Checkout

NCR Voyix describes Picklist Assist as computer vision and machine
learning that suggests likely PLU selections at self-checkout. It also
discusses validation checks to help detect selection mismatches and
reduce unnecessary attendant interventions.

**What to learn** - Return a short, ranked list of plausible products
rather than forcing a single prediction. - Combine model output with
checkout validation. - Keep the customer journey simple and
accessible. - Provide centralized configuration and operational
visibility.

References: - [NCR Voyix
Self-Checkout](https://www.ncr.com/platform/retail-applications/checkout/self-checkout) -
[NCR Voyix Loss Prevention / Picklist
Assist](https://www.ncr.com/platform/retail-applications/loss-prevention)

### 2.3 BigBasket + AWS --- AI-enabled retail checkout

An AWS customer story describes BigBasket's AI-enabled checkout work for
physical stores and its use of Amazon SageMaker for FMCG product
identification. The case study discusses reducing model training time
and cost, and the operational challenge of manual weighing stickers and
separate weighing counters.

**What to learn** - Design around actual store workflows and
bottlenecks. - Make catalog and model updates operationally
manageable. - Measure training cost, iteration time, and store-level
impact---not only model accuracy. - Treat the camera, checkout
interface, and weighing process as one customer journey.

Reference: [AWS: How BigBasket improved AI-enabled
checkout](https://aws.amazon.com/blogs/machine-learning/how-bigbasket-improved-ai-enabled-checkout-at-their-physical-stores-using-amazon-sagemaker/)

### 2.4 Amazon Just Walk Out --- sensor fusion and retail systems

Amazon describes Just Walk Out as a broader checkout-free system
involving computer vision, machine learning, sensor inputs, and retail
integrations. Its public developer documentation discusses catalog
setup, POS integration, charge calculation, payment integration, and
post-purchase responsibilities. This is a much broader problem than
produce classification.

**What to learn** - Retail AI depends on reliable catalog, pricing,
transaction, and payment interfaces. - Sensor fusion can help resolve
ambiguity that a camera alone cannot. - Privacy boundaries and data
minimization should be explicit. - A production retail system needs
clear ownership of pricing, payment, receipts, and refunds.

References: - [AWS Just Walk
Out](https://aws.amazon.com/just-walk-out/) - [Amazon Just Walk Out
developer
documentation](https://developer.amazon.com/docs/physicalstores/welcome) -
[Amazon: How Just Walk Out
works](https://www.aboutamazon.com/news/retail/how-does-amazon-just-walk-out-work)

### 2.5 Instacart Caper Cart --- smart-cart and scale integration

Instacart describes Caper Carts as combining computer vision, hardware
sensors, embedded payment, and an integrated scale for produce and bulk
goods. Its public page notes weights-and-measures certification for its
scale implementation.

**What to learn** - Produce recognition and weighing are separate but
coordinated functions. - Weight measurement must come from suitable
hardware, not image estimation. - Sensor fusion can improve basket
accuracy. - Hardware certification and integration are part of the
product, not optional accessories.

Reference: [Instacart Caper
Carts](https://www.instacart.com/company/enterprise-platform/connected-stores/caper-carts/)

### 2.6 Industry standard: IFPS Price Look-Up (PLU)

IFPS explains that PLU codes are used by retailers to identify bulk
produce. A PLU can distinguish commodity, variety, growing method, and
size group. IFPS notes that PLU codes are voluntary and that the system
is not a substitute for a retailer's own product catalog and local
business rules.

**Design implication:** A visual class such as `apple` is not
necessarily a saleable SKU. The catalog must map the visual result to
the store's actual item, PLU, unit of sale, price, and applicable
attributes. The model must not infer organic/conventional status or
other attributes that cannot reliably be observed visually.

Reference: [IFPS PLU Codes](https://www.ifpsglobal.com/plu-codes)

### 2.7 India: Legal Metrology

For an India pilot, retail weighing is a regulated measurement activity.
The Department of Consumer Affairs describes the Legal Metrology Act,
2009 and related rules, including verification and stamping of
applicable weighing instruments. Confirm the exact requirements for the
chosen scale, model, installation, state, and retail use with the
relevant Legal Metrology authority and qualified compliance counsel.

**Design implication:** The AI system may read a scale's digital output
through an approved integration, but it must not replace, modify, or
claim to certify the weighing instrument.

References: - [Department of Consumer Affairs --- Legal Metrology
overview](https://consumeraffairs.gov.in/pages/legal-metrology-overview) -
[Department of Consumer Affairs --- Weights and
Measures](https://consumeraffairs.gov.in/pages/weight-and-measures)

------------------------------------------------------------------------

## 3. Product Vision, Users, and Scope

### 3.1 Vision

Make loose-produce checkout faster, more accurate, accessible, and
easier to operate by combining visual recognition with trusted retail
data and measurement hardware.

### 3.2 Primary users

1.  **Shopper:** presents produce, reviews the suggested item, confirms
    it, and sees the measured weight and price.
2.  **Cashier / attendant:** resolves uncertain or exceptional cases and
    can manually search the catalog.
3.  **Store manager:** manages store-specific product availability,
    prices, devices, and operational reports.
4.  **Retail operations administrator:** manages multiple stores,
    configuration, model rollouts, and performance.
5.  **ML / platform operator:** monitors model quality, drift, device
    health, incidents, and retraining workflows.

### 3.3 MVP scope

-   One checkout station or assisted produce counter.
-   One fixed camera with controlled capture area and lighting.
-   One supported digital scale integration, or a clearly labelled
    simulator during development.
-   A retailer-managed catalog of 20--40 produce classes/SKUs for the
    pilot.
-   Top-3 predictions with calibrated confidence.
-   Human confirmation for uncertain or ambiguous predictions.
-   Store-specific price lookup from a controlled catalog/POS adapter.
-   Weight capture from the scale; no image-based weight estimation.
-   Basket line creation, correction, removal, and transaction audit
    log.
-   Admin interface for catalog mapping, device status, and basic
    metrics.
-   Offline-safe behavior for the locally cached catalog; payment
    remains outside the MVP.

### 3.4 Explicitly out of scope for MVP

-   Fully autonomous payment or cashierless store operation.
-   Face recognition, shopper biometrics, or identity inference.
-   Automatic quality grading, ripeness, disease, or freshness claims.
-   Inferring organic status, country of origin, or certification from
    appearance.
-   General object recognition for all grocery products.
-   Multi-camera shopper tracking.
-   Production payment processing or refunds.
-   Replacing certified weighing equipment.
-   A promise of zero shrink or guaranteed fraud detection.

### 3.5 Later expansion

-   More produce categories and retailer-specific varieties.
-   Multiple cameras and checkout lanes.
-   Edge inference on a dedicated device.
-   POS integrations with real retailers.
-   Multi-store management and model rollout rings.
-   Visual quality inspection as a separate, validated product module.
-   Smart-cart and kiosk integrations.
-   Additional regional catalogs, languages, and currencies.

------------------------------------------------------------------------

## 4. End-to-End Checkout Workflow

1.  The station is idle and displays capture instructions.
2.  Shopper places one produce item in the marked capture area.
3.  Camera captures a short burst or video frames.
4.  Image-quality checks detect blur, glare, occlusion, poor lighting,
    or multiple items.
5.  Detection/segmentation isolates the produce item.
6.  The classifier returns top-K candidates and calibrated confidence.
7.  The catalog resolver maps candidate classes to active store
    SKUs/PLUs.
8.  Decision policy selects one of three paths:
    -   **High confidence:** show the leading match for confirmation.
    -   **Medium confidence:** show a short ranked choice list.
    -   **Low confidence / unknown / multiple items:** request recapture
        or manual search.
9.  Shopper confirms the correct item.
10. Scale adapter obtains a stable weight reading and unit.
11. Pricing service retrieves the active store price and unit basis.
12. System calculates the line amount using decimal arithmetic and
    retailer rules.
13. Checkout/POS adapter receives the selected SKU, PLU, weight, unit
    price, and line total.
14. The station records an auditable event and returns to ready state.

### 4.1 Core decision principle

**The model recommends; the retailer's catalog and pricing system decide
what can be sold and at what price.** No model prediction should
directly create an unreviewed financial charge.

### 4.2 Exception paths

-   No produce detected → prompt to reposition and retry.
-   Multiple produce items → ask shopper to separate items or use a
    supported multi-item flow.
-   Unknown variety → manual catalog search.
-   Low confidence → never silently auto-select.
-   Scale unstable → wait for stable reading.
-   Scale disconnected → block weight-priced line creation and call
    attendant.
-   Catalog/POS unavailable → use only explicitly permitted cached data;
    otherwise pause the line.
-   Duplicate capture → idempotency key prevents duplicate basket
    entries.
-   User cancels → discard pending recognition and weight state.
-   Price changed mid-transaction → apply retailer's defined price-lock
    policy and retain the price version used.

------------------------------------------------------------------------

## 5. Functional Requirements

  ID      Requirement                                               Priority
  ------- --------------------------------------------------------- ---------------------
  FR-01   Capture an image from a supported camera                  P0
  FR-02   Detect invalid capture conditions and request recapture   P0
  FR-03   Recognize supported produce classes                       P0
  FR-04   Return top-3 candidates and confidence values             P0
  FR-05   Map model classes to active store catalog items           P0
  FR-06   Require confirmation according to confidence policy       P0
  FR-07   Read stable weight from supported scale adapter           P0
  FR-08   Retrieve store-specific price and unit basis              P0
  FR-09   Calculate price using decimal-safe arithmetic             P0
  FR-10   Add, correct, and remove basket lines                     P0
  FR-11   Support manual catalog search and attendant override      P0
  FR-12   Persist transaction and audit events                      P0
  FR-13   Provide role-based admin access                           P0
  FR-14   Expose device/model/service health                        P1
  FR-15   Support signed model and catalog version rollout          P1
  FR-16   Export privacy-safe operational metrics                   P1
  FR-17   Support multiple stores and checkout lanes                P1
  FR-18   Integrate with a real POS                                 P1, pilot-dependent
  FR-19   Support offline operation with safe synchronization       P1
  FR-20   Provide multilingual UI                                   P2

------------------------------------------------------------------------

## 6. Non-Functional Requirements and Initial SLO Targets

These are proposed engineering targets for pilot validation, not claims
of achieved performance.

  -----------------------------------------------------------------------
  Area                                Initial target
  ----------------------------------- -----------------------------------
  Recognition response                p95 under 700 ms on target edge
                                      hardware, excluding human
                                      interaction

  End-to-end suggestion               p95 under 1.5 seconds from capture
                                      to candidate display

  Availability                        99.5% monthly pilot service
                                      availability, excluding planned
                                      maintenance

  Data integrity                      No duplicate committed basket lines
                                      from retries

  Price integrity                     Every committed line records
                                      catalog and price version

  Model quality                       Per-class precision/recall
                                      thresholds defined before pilot; no
                                      single aggregate accuracy gate

  Unknown handling                    Unknown/low-confidence inputs route
                                      to safe fallback

  Security                            TLS in transit, encryption at rest,
                                      RBAC, secrets management, audit
                                      logs

  Observability                       Metrics, structured logs, traces,
                                      model version, device version

  Recovery                            Documented backup, restore, and
                                      offline recovery procedure

  Accessibility                       Large readable text, keyboard/touch
                                      support, clear error messages,
                                      color-independent cues
  -----------------------------------------------------------------------

### 6.1 Quality gates

Before a class is enabled for automatic suggestion, evaluate: -
Per-class precision, recall, F1, and confusion matrix. - Top-1 and top-3
accuracy. - Calibration error and confidence reliability. - Performance
across lighting, camera angle, background, packaging, size, variety, and
season. - False acceptance rate for visually similar classes. -
Unknown-class rejection performance. - Latency and memory on the actual
deployment device.

Do not publish a single "99% accurate" claim unless the test protocol,
class distribution, sample size, confidence interval, and store-domain
conditions are documented.

------------------------------------------------------------------------

## 7. System Architecture

### 7.1 Logical architecture

``` text
Camera ──> Capture Client ──> Image Quality Gate
                                  │
                                  v
                         Produce Detector /
                            Classifier
                                  │
                         Top-K + Confidence
                                  │
                                  v
                     Catalog & PLU Resolver
                                  │
                     Decision / Human Review
                                  │
                   Shopper or Attendant Confirm
                                  │
              ┌───────────────────┴──────────────────┐
              v                                      v
        Scale Adapter                         Pricing Adapter
              │                                      │
        Stable Weight                         Active Store Price
              └───────────────────┬──────────────────┘
                                  v
                         Basket / POS Adapter
                                  │
                         Transaction Audit
                                  │
              ┌───────────────────┴──────────────────┐
              v                                      v
        Retail Checkout UI                    Admin / Monitoring
```

### 7.2 Recommended service boundaries

**A. Edge / station application** - Camera capture and device health. -
Local image-quality checks. - Local inference when supported. - Checkout
UI and local state machine. - Scale adapter. - Encrypted local cache and
offline queue.

**B. Backend API** - Authentication and authorization. - Store, station,
and device registration. - Catalog and PLU mapping. - Recognition
request orchestration (if inference is server-side). - Pricing/POS
adapters. - Basket and transaction events. - Admin and reporting APIs.

**C. ML platform** - Dataset registry and versioning. - Annotation and
quality review. - Training and evaluation pipelines. - Model registry. -
Model signing and deployment. - Drift, confidence, and error monitoring.

**D. Data platform** - Relational operational database. - Object storage
for approved training/evaluation images. - Event/metrics store. - Audit
retention and deletion policies.

### 7.3 Deployment options

**Prototype:** laptop/webcam + local Python inference + simulated
scale/catalog.

**Pilot:** dedicated checkout PC or edge device, fixed camera, supported
scale, local service, backend synchronization.

**Enterprise:** edge-first inference, centrally managed
configuration/model registry, store-specific catalog/POS connectors,
fleet monitoring, staged rollouts, disaster recovery.

Use cloud inference only when the network and privacy model support it.
A practical production design keeps capture, inference, and basic
checkout assistance functioning locally, while central services manage
catalog, reporting, and controlled synchronization.

------------------------------------------------------------------------

## 8. AI / Computer Vision Strategy

### 8.1 Problem formulation

Do not assume that a single flat classifier solves every retail
scenario. Use a staged vision pipeline:

1.  **Image quality assessment:** reject blur, severe glare, poor
    exposure, and unsupported views.
2.  **Object detection or segmentation:** locate produce and isolate it
    from hands, trays, and background.
3.  **Fine-grained classification:** predict supported produce
    class/variety.
4.  **Open-set recognition:** detect when the item is outside the
    supported classes.
5.  **Confidence calibration:** ensure confidence values correspond to
    observed correctness.
6.  **Catalog resolution:** map visual class to store-specific saleable
    items.
7.  **Human confirmation:** handle ambiguity, low confidence, and
    exceptions.

For a controlled single-item capture area, begin with image
classification plus quality checks. Add object detection/segmentation
when multiple items, clutter, or partial occlusion become real
requirements.

### 8.2 Model candidates

Benchmark rather than selecting by reputation alone.

  -----------------------------------------------------------------------
  Candidate               Role                    Considerations
  ----------------------- ----------------------- -----------------------
  EfficientNet-B0/B2      Strong baseline         Good accuracy/compute
                          classifier              trade-off

  MobileNetV3             Edge/mobile baseline    Small and fast

  ConvNeXt-Tiny           Higher-capacity         Compare latency and
                          classifier              memory

  YOLO-family detector    Object localization     Useful for multiple
                                                  objects

  RT-DETR                 Detection alternative   Benchmark on target
                                                  hardware

  Vision Transformer      Research comparison     May require more
                                                  data/compute

  Embedding +             Catalog expansion /     Requires careful
  nearest-neighbour       similarity              thresholding and
  retrieval                                       curated references
  -----------------------------------------------------------------------

A sensible first experiment is MobileNetV3 or EfficientNet-B0, followed
by a stronger baseline. Export to ONNX or an appropriate edge runtime
only after measuring actual target-device performance.

### 8.3 Data collection and dataset strategy

Potential sources: - [Fruits-360
dataset](https://www.kaggle.com/datasets/moltean/fruits) - [Fruits and
Vegetables Image Recognition datasets on
Kaggle](https://www.kaggle.com/datasets) - [Roboflow
Universe](https://universe.roboflow.com/) datasets, subject to each
dataset's license. - Retailer/host-provided images captured at the
actual checkout station. - Original images collected with consent and a
documented data agreement.

**Critical:** public datasets are useful for pretraining and prototypes,
but they rarely represent the exact camera, lighting, cultivar,
packaging, regional produce, seasonal variation, or checkout background
of a real store. A production pilot requires a retailer-specific
dataset.

### 8.4 Dataset collection protocol

For every target class: - Capture multiple individual items, not just
repeated photos of one specimen. - Include different suppliers,
cultivars, sizes, ripeness appearances, and seasons. - Vary orientation,
distance, lighting, background, and camera exposure. - Include realistic
occlusion, hands, bags, trays, and imperfect placement. - Capture
confusing lookalike pairs intentionally. - Include unsupported produce
and non-produce examples. - Record store, station, camera, date, and
capture conditions as metadata. - Avoid storing faces or unnecessary
customer information. - Obtain appropriate consent and define retention
before collecting operational images.

Suggested starting target for a pilot: at least 300--500 distinct
physical examples per class, with multiple images per example and a
separate store-domain test set. Increase this based on class complexity
and measured error rates. Do not treat near-duplicate frames as
independent examples.

### 8.5 Data split and leakage prevention

Split by physical item/session/source and preferably by collection date
or store: - Train: 70% - Validation: 15% - Test: 15%

Never randomly split adjacent frames of the same physical fruit across
train and test. Keep a locked test set that is not used for model
selection. Include an external/store-domain test set before rollout.

### 8.6 Augmentation

Use realistic transformations: - Moderate brightness, contrast,
saturation, and white-balance shifts. - Small rotations and perspective
changes. - Scale/crop and translation. - Mild blur and sensor noise. -
Background variation where appropriate. - Occlusion simulation.

Avoid transformations that change semantic identity or create
unrealistic colors/textures. Keep augmentation policies versioned.

### 8.7 Training and evaluation

Track: - Top-1 and top-3 accuracy. - Per-class precision, recall, F1. -
Macro F1 and weighted F1. - Confusion matrix. - Calibration metrics
(ECE/Brier score). - Unknown rejection precision/recall. - False
acceptance rate. - p50/p95 inference latency. - Model size, memory, and
CPU/GPU utilization.

Use class-balanced sampling or weighted loss only when justified by
class distribution. Tune thresholds on validation data, then report
final metrics on the locked test set.

### 8.8 Human-in-the-loop learning

With appropriate policy and consent: - Store only the minimum necessary
low-confidence examples. - Allow attendants to correct a prediction. -
Record correction reason and catalog mapping. - Route samples to an
annotation queue. - Review labels before retraining. - Compare candidate
model against current production model. - Deploy in shadow/canary mode
before promotion.

Never automatically train on unreviewed customer or checkout data.

------------------------------------------------------------------------

## 9. Catalog, PLU, Pricing, and Weight

### 9.1 Product catalog model

The retailer's catalog is authoritative. Each saleable item should
contain: - Internal SKU / product ID. - Display name and localized
names. - Visual class mapping(s). - PLU where applicable. - Unit of
sale: kg, g, piece, bunch, pack. - Price and price basis (for example,
₹/kg or ₹/piece). - Store availability and effective dates. -
Tax/category configuration from the retailer's system. - Active/inactive
state. - Organic/conventional or other attributes only when supported by
verified catalog data or explicit labeling.

One visual class may map to multiple catalog items. For example, the
image may indicate "apple," while the store may sell multiple varieties,
grades, or growing-method variants. The UI must ask for a choice or use
a retailer-approved rule; the model must not invent the missing
attribute.

### 9.2 PLU handling

-   Store PLU as a catalog identifier, not as a class label.
-   Support retailer-specific PLU mappings where applicable.
-   Keep the source and effective date of each mapping.
-   Do not assume IFPS PLU codes are universal or mandatory in every
    market.
-   Do not infer organic status from visual appearance.
-   Validate mapping with the retailer's POS/catalog owner.

### 9.3 Weight handling

-   Read weight from a supported scale interface.
-   Wait for stable readings and capture unit, timestamp, device ID, and
    calibration/verification metadata if available.
-   Convert units using explicit, tested conversion rules.
-   Use integer minor units or decimal arithmetic for money; never
    binary floating-point for final price calculations.
-   Reject negative, unstable, out-of-range, or missing readings.
-   Do not estimate weight from image dimensions.
-   Ensure scale use complies with applicable legal metrology
    requirements.

### 9.4 Price calculation

Example only:

`line_total = round_to_currency_rule(net_weight_kg × price_per_kg)`

The production implementation must use the retailer's authoritative
pricing and rounding rules, including tare, promotions, taxes, minimum
charges, and price-lock behavior. Store the inputs and rule version used
to compute every line.

------------------------------------------------------------------------

## 10. Application and API Design

### 10.1 Suggested technology stack

Choose based on the team's skills and target deployment; this is a
practical default, not a mandatory stack.

  Layer                 Suggested technology
  --------------------- -------------------------------------------
  ML                    Python, PyTorch, torchvision, timm
  Image processing      OpenCV, Pillow
  API                   FastAPI, Pydantic
  UI                    React + TypeScript
  Station runtime       Python service or lightweight local agent
  Database              PostgreSQL
  Cache / queue         Redis or durable local queue as needed
  Object storage        S3-compatible storage / MinIO
  Model tracking        MLflow
  Experiment tracking   MLflow or Weights & Biases
  Data validation       Pandera / Great Expectations
  Packaging             Docker
  CI/CD                 GitHub Actions or equivalent
  Monitoring            Prometheus + Grafana; OpenTelemetry
  Error tracking        Sentry or equivalent

### 10.2 API endpoints (initial contract)

All endpoints require authentication except explicitly public health
checks.

  -------------------------------------------------------------------------------------
  Method                  Endpoint                              Purpose
  ----------------------- ------------------------------------- -----------------------
  POST                    `/api/v1/recognitions`                Submit capture or image
                                                                reference

  GET                     `/api/v1/recognitions/{id}`           Get candidates and
                                                                decision status

  POST                    `/api/v1/recognitions/{id}/confirm`   Confirm selected
                                                                catalog item

  POST                    `/api/v1/recognitions/{id}/reject`    Reject candidates /
                                                                request manual lookup

  GET                     `/api/v1/catalog/items`               Search active store
                                                                catalog

  GET                     `/api/v1/catalog/items/{id}`          Retrieve catalog item

  POST                    `/api/v1/scale/readings`              Receive scale reading
                                                                from trusted adapter

  POST                    `/api/v1/basket/lines`                Add confirmed item and
                                                                weight

  PATCH                   `/api/v1/basket/lines/{id}`           Correct a line

  DELETE                  `/api/v1/basket/lines/{id}`           Remove a line

  GET                     `/api/v1/stores/{id}/devices`         Device status

  GET                     `/api/v1/admin/metrics`               Operational metrics

  GET                     `/health/live`                        Process liveness

  GET                     `/health/ready`                       Dependency readiness
  -------------------------------------------------------------------------------------

### 10.3 Example recognition response

``` json
{
  "recognition_id": "rec_01J...",
  "model_version": "produce-classifier-0.1.0",
  "status": "needs_confirmation",
  "candidates": [
    {"visual_class": "apple", "confidence": 0.91, "catalog_item_id": "sku_101"},
    {"visual_class": "pear", "confidence": 0.06, "catalog_item_id": "sku_204"}
  ],
  "decision": {
    "action": "confirm_top_candidate",
    "reason": "confidence_policy"
  }
}
```

This is an illustrative contract. Do not expose raw image storage paths,
internal secrets, or sensitive operational metadata to the shopper
client.

### 10.4 API engineering rules

-   Version APIs from the beginning.
-   Validate payloads and file sizes.
-   Use request IDs and idempotency keys.
-   Enforce store/station scoping on every data query.
-   Apply rate limits and upload limits.
-   Use signed, short-lived object references for image uploads.
-   Keep model inference separate from payment/transaction authority.
-   Return structured error codes and actionable UI messages.
-   Maintain backward compatibility for deployed station clients.

------------------------------------------------------------------------

## 11. Database Design

Suggested core tables:

### `stores`

`id`, `name`, `timezone`, `currency`, `status`, `created_at`

### `stations`

`id`, `store_id`, `station_code`, `location_label`, `status`,
`created_at`

### `devices`

`id`, `station_id`, `device_type`, `manufacturer`, `model`,
`firmware_version`, `last_seen_at`, `status`

### `catalog_items`

`id`, `retailer_sku`, `display_name`, `unit_of_sale`, `price_basis`,
`active`, `created_at`, `updated_at`

### `catalog_mappings`

`id`, `catalog_item_id`, `visual_class`, `plu_code`, `store_id`,
`effective_from`, `effective_to`, `mapping_source`, `verified_by`

### `prices`

`id`, `catalog_item_id`, `store_id`, `amount`, `currency`, `unit_basis`,
`effective_from`, `effective_to`, `price_version`

### `recognitions`

`id`, `store_id`, `station_id`, `model_version`, `status`,
`top_candidates_json`, `selected_catalog_item_id`, `confidence`,
`created_at`

### `scale_readings`

`id`, `station_id`, `recognition_id`, `weight_value`, `weight_unit`,
`stable`, `device_timestamp`, `received_at`

### `basket_lines`

`id`, `transaction_id`, `catalog_item_id`, `weight_value`,
`weight_unit`, `unit_price`, `line_total`, `price_version`, `status`,
`created_at`

### `transactions`

`id`, `store_id`, `station_id`, `external_pos_reference`, `status`,
`currency`, `created_at`, `completed_at`

### `audit_events`

`id`, `actor_id`, `store_id`, `station_id`, `entity_type`, `entity_id`,
`action`, `reason`, `metadata_json`, `created_at`

### `model_versions`

`id`, `name`, `version`, `artifact_uri`, `checksum`, `metrics_json`,
`approval_status`, `created_at`, `deployed_at`

### Database rules

-   Use UUIDs or similarly robust identifiers.
-   Add foreign keys and appropriate indexes.
-   Use decimal/numeric columns for monetary values.
-   Store timestamps in UTC and retain store timezone separately.
-   Make catalog and price changes effective-dated.
-   Enforce tenant/store isolation.
-   Keep audit events append-only for application roles.
-   Define retention and deletion policies for images separately from
    transaction records.
-   Avoid storing payment card data; delegate payment to the retailer's
    certified POS/payment provider.

------------------------------------------------------------------------

## 12. Frontend / UX Requirements

### Shopper checkout screen

-   Large camera preview and simple placement instruction.
-   Clear "item detected" state.
-   Candidate names with images where useful.
-   Explicit confirmation and correction.
-   Weight, unit price, and estimated line amount.
-   Clear retry, cancel, and call-attendant actions.
-   Accessible text, contrast, and non-color-only status indicators.

### Attendant screen

-   Manual product search.
-   Top candidate list and confidence context.
-   Reason for escalation.
-   Correction and override with reason code.
-   Device status and recent errors.

### Admin dashboard

-   Store/station/device inventory.
-   Catalog and PLU mapping management.
-   Price synchronization status.
-   Model version and rollout status.
-   Recognition volume, manual override rate, unknown rate, latency, and
    device health.
-   Class-level performance and drift alerts.
-   Audit search with role-based access.

### UX principle

Never display a confusing probability as if it were a guarantee. Prefer
language such as "Suggested item" and "Please confirm." Do not expose
raw model confidence to shoppers unless user testing demonstrates that
it helps.

------------------------------------------------------------------------

## 13. Security, Privacy, and Compliance

### 13.1 Security controls

-   TLS for all network communication.
-   Encryption at rest for databases, object storage, and local device
    caches.
-   Role-based access control (shopper, attendant, manager, admin,
    service).
-   Strong admin authentication and MFA where supported.
-   Device identity using certificates or managed credentials.
-   Secrets stored in a secrets manager, never in source code.
-   Signed model artifacts and checksum verification.
-   Secure boot / OS hardening where supported.
-   Dependency and container vulnerability scanning.
-   Audit logging for catalog changes, overrides, model rollouts, and
    admin actions.
-   Backups with tested restore procedures.
-   Network segmentation for checkout devices and store systems.
-   Least-privilege service accounts.

### 13.2 Privacy by design

-   Do not use facial recognition or identify shoppers from camera
    footage.
-   Frame the camera toward the produce capture area, not the shopper.
-   Avoid recording continuous video unless there is a separately
    justified, approved use case.
-   Prefer transient image processing and store only approved training
    samples.
-   Define retention, access, deletion, and incident procedures.
-   Mask or exclude incidental personal data.
-   Obtain retailer/legal review for applicable Indian privacy and
    data-protection obligations before pilot deployment.

### 13.3 India-specific measurement and retail compliance

-   Confirm the scale model and its suitability for trade use.
-   Confirm applicable model approval, verification, stamping, and
    periodic verification requirements.
-   Use a qualified integrator and consult the relevant State Legal
    Metrology authority.
-   Do not modify metrology firmware or alter measurement output.
-   Confirm applicable packaged-commodity declarations, tax, POS, and
    consumer-protection requirements with the retailer.
-   Maintain a compliance checklist per store and device.

This plan is engineering guidance, not legal advice or a certification.

------------------------------------------------------------------------

## 14. Reliability, Offline Operation, and Observability

### 14.1 Offline strategy

The station should be able to: - Run the currently approved model
locally where hardware permits. - Read a signed, versioned local catalog
snapshot. - Keep pending non-payment events in an encrypted durable
queue. - Detect stale catalog/pricing data and apply retailer-approved
restrictions. - Sync events using idempotency keys after connectivity
returns. - Show a clear unavailable state when authoritative pricing or
required POS confirmation is unavailable.

Never silently accept stale prices beyond the retailer's defined policy.

### 14.2 Observability

Track: - Recognition requests, success/failure, and latency. - Per-class
prediction distribution. - Confidence histogram and unknown rate. -
Human confirmation and correction rates. - Catalog lookup failures and
stale catalog events. - Scale connection, stability, and reading
failures. - POS adapter latency and errors. - Station CPU, memory, disk,
temperature, and network. - Model version and configuration version by
station. - Offline queue depth and synchronization lag.

Logs must avoid raw customer images and unnecessary personal
information.

### 14.3 Incident playbooks

Document actions for: - Incorrect produce suggestions. - Wrong
catalog/PLU mapping. - Incorrect price or stale catalog. - Scale
disconnected or unstable. - POS outage. - Camera failure. - Model
regression after rollout. - Security incident or suspected data
exposure. - Local storage full / offline queue saturation.

A station must be able to fall back to the retailer's normal manual
lookup process.

------------------------------------------------------------------------

## 15. Testing and Quality Assurance

### ML tests

-   Locked test-set evaluation.
-   Per-class and lookalike confusion tests.
-   Unknown-class and non-produce rejection.
-   Lighting, blur, occlusion, and camera-shift tests.
-   Calibration and threshold tests.
-   Performance tests on target edge hardware.

### Backend tests

-   Unit and integration tests.
-   API schema/contract tests.
-   Store-tenant isolation tests.
-   Idempotency and retry tests.
-   Price rounding and unit conversion tests.
-   Catalog versioning and effective-date tests.
-   Audit immutability tests.

### Hardware and station tests

-   Camera disconnect/reconnect.
-   Scale disconnect/reconnect.
-   Stable/unstable/zero/negative/out-of-range readings.
-   Power loss and reboot recovery.
-   Network loss and reconnection.
-   Thermal and sustained-load testing.
-   Camera position and lighting reproducibility.

### End-to-end acceptance tests

-   One supported produce item from capture to basket.
-   Lookalike produce with manual selection.
-   Unknown item fallback.
-   Multiple objects in capture area.
-   Weight-priced and piece-priced items.
-   Price update during an active transaction.
-   Duplicate request retry.
-   POS timeout and attendant recovery.
-   Full offline-to-online synchronization.

------------------------------------------------------------------------

## 16. CI/CD and MLOps

### Application CI/CD

1.  Lint and static analysis.
2.  Unit and integration tests.
3.  Dependency and image scanning.
4.  Build immutable container/artifact.
5.  Deploy to development.
6.  Run smoke and contract tests.
7.  Promote to staging.
8.  Pilot canary deployment.
9.  Monitor SLOs and business metrics.
10. Promote or rollback.

### Model release pipeline

1.  Register dataset version and data lineage.
2.  Validate labels and dataset quality.
3.  Train candidate model.
4.  Evaluate against locked test and store-domain set.
5.  Compare with current champion.
6.  Review class-level regressions and safety thresholds.
7.  Sign and register artifact.
8.  Deploy to shadow mode.
9.  Canary on limited stations.
10. Promote or roll back.

### Rollback triggers

-   Critical class precision/recall falls below agreed threshold.
-   Unknown rejection degrades materially.
-   p95 latency exceeds station budget.
-   Crash rate or device resource use increases.
-   Manual override rate spikes.
-   Catalog mapping or price integrity issue appears.

Model rollback must not roll back or overwrite transaction records.

------------------------------------------------------------------------

## 17. Delivery Roadmap

Indicative schedule for a small focused team. Timelines depend on access
to real produce, camera/scale hardware, POS documentation, and retailer
partners.

  ------------------------------------------------------------------------
  Phase                         Duration Deliverables     Exit criteria
  ---------------- --------------------- ---------------- ----------------
  0\. Discovery               1--2 weeks User journeys,   Workflow and
                                         pilot partner,   success metrics
                                         requirements,    signed off
                                         risk register    

  1\. Data +                  2--4 weeks Dataset,         Leakage-safe
  baseline                               annotation       baseline and
                                         guide, baseline  error analysis
                                         classifier       

  2\. MVP station             2--3 weeks Camera capture,  End-to-end demo
                                         inference,       works reliably
                                         candidate UI,    
                                         manual fallback  

  3\. Catalog +               2--4 weeks Catalog mapping, Verified weight
  scale                                  scale adapter,   and correct test
                                         price            pricing
                                         calculation      

  4\. Backend +               2--3 weeks APIs,            RBAC and
  admin                                  PostgreSQL,      transaction
                                         audit, admin     traceability
                                         dashboard        

  5\. Pilot                   2--4 weeks Monitoring,      Pilot acceptance
  hardening                              offline queue,   checklist passed
                                         security, QA     

  6\. Store pilot             4--8 weeks Limited live     Business and
                                         deployment and   technical gates
                                         measured         met
                                         evaluation       

  7\. Scale-out                  Ongoing Multi-store, POS Repeatable
                                         integrations,    rollout and
                                         edge fleet       support model
                                         management       
  ------------------------------------------------------------------------

### Recommended team

-   Product owner / retail workflow lead.
-   Computer vision / ML engineer.
-   Backend engineer.
-   Frontend / station UI engineer.
-   DevOps / platform engineer (part-time initially).
-   QA / test engineer.
-   Retail POS / hardware integration specialist.
-   Retail operations and compliance representative.

For a solo portfolio build, combine roles and simulate unavailable
retail systems, but clearly label all simulators and avoid claiming a
live retail deployment.

------------------------------------------------------------------------

## 18. Pilot Success Metrics

Establish a baseline before deployment and compare like-for-like
checkout conditions.

### Customer and operations

-   Median and p95 produce identification time.
-   Median produce line completion time.
-   Attendant intervention rate.
-   Manual lookup rate.
-   Shopper correction rate.
-   Station uptime and abandonment rate.

### ML

-   Top-1 and top-3 accuracy by class.
-   Precision and recall by class.
-   Unknown rejection performance.
-   False acceptance rate for lookalike products.
-   Confidence calibration.
-   Error distribution by store, camera, lighting, and time.

### Commercial

-   Cost per recognition.
-   Hardware and installation cost per station.
-   Support incidents per station/week.
-   Estimated labor time saved (validated with store data).
-   Produce shrink and mis-key trends, interpreted carefully.
-   Return on investment based on measured pilot costs and benefits.

### Pilot gates

Do not proceed to wider rollout until: - The retailer approves the
workflow and catalog mappings. - Scale and POS integrations pass
acceptance tests. - All critical supported classes meet agreed precision
and fallback thresholds. - Pricing and transaction audit tests pass. -
Staff can recover from common failures. - Privacy/security and legal
metrology reviews are complete. - A rollback and support plan exists.

------------------------------------------------------------------------

## 19. Risks and Mitigations

  -----------------------------------------------------------------------
  Risk                    Impact                  Mitigation
  ----------------------- ----------------------- -----------------------
  Similar-looking         Wrong SKU/price         Top-K, retailer
  varieties                                       mapping, confirmation,
                                                  collect lookalike data

  Organic vs conventional Incorrect pricing       Never infer from
  ambiguity                                       appearance; ask or rely
                                                  on verified
                                                  catalog/label

  Public dataset domain   Poor store performance  Collect store-camera
  gap                                             data and use external
                                                  store test set

  Seasonal appearance     Model drift             Seasonal monitoring and
  changes                                         approved retraining

  Multiple items /        Wrong recognition       Capture guidance,
  occlusion                                       detection,
                                                  separate-item workflow

  Scale mismatch or       Incorrect line amount   Trusted scale adapter,
  failure                                         stability checks,
                                                  manual fallback

  Stale price/catalog     Financial error         Effective-dated
                                                  catalog, price
                                                  versioning, POS
                                                  authority

  Network outage          Interrupted checkout    Edge inference, local
                                                  cache, durable queue,
                                                  safe restrictions

  Hardware variability    Inconsistent results    Supported device matrix
                                                  and station calibration
                                                  process

  Model overconfidence    Silent                  Calibration, unknown
                          misclassification       rejection, human
                                                  confirmation

  Data privacy incident   Legal/reputational risk Minimize capture,
                                                  retention, access, and
                                                  storage

  POS vendor constraints  Integration delay       Start with simulator;
                                                  obtain API/vendor
                                                  approval early

  Compliance failure      Cannot deploy for trade Legal Metrology review
                                                  and approved weighing
                                                  hardware
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## 20. Repository Structure

``` text
barcodeless-produce-assistant/
├── README.md
├── PLAN.md
├── LICENSE
├── .env.example
├── .gitignore
├── docker-compose.yml
├── docs/
│   ├── architecture.md
│   ├── api-specification.md
│   ├── database-design.md
│   ├── security-and-privacy.md
│   ├── data-governance.md
│   ├── model-card.md
│   ├── annotation-guidelines.md
│   ├── hardware-integration.md
│   ├── deployment-runbook.md
│   ├── incident-response.md
│   └── adr/
├── apps/
│   ├── checkout-ui/
│   ├── admin-dashboard/
│   └── station-agent/
├── services/
│   ├── api/
│   ├── catalog/
│   ├── pricing/
│   ├── basket/
│   ├── scale-adapter/
│   └── pos-adapter/
├── ml/
│   ├── configs/
│   ├── data/
│   │   ├── raw/              # ignored; access-controlled
│   │   ├── interim/
│   │   ├── processed/
│   │   └── splits/
│   ├── notebooks/
│   ├── src/
│   │   ├── data/
│   │   ├── models/
│   │   ├── training/
│   │   ├── evaluation/
│   │   ├── inference/
│   │   └── monitoring/
│   ├── tests/
│   └── artifacts/            # model binaries not committed by default
├── infra/
│   ├── docker/
│   ├── monitoring/
│   ├── migrations/
│   └── deployment/
├── tests/
│   ├── integration/
│   ├── e2e/
│   ├── hardware/
│   └── load/
└── scripts/
    ├── validate_dataset.py
    ├── train.py
    ├── evaluate.py
    └── export_model.py
```

Keep raw images, credentials, customer data, model binaries, and
production exports out of Git unless there is an explicit approved
storage strategy. Use dataset manifests and versioned artifact storage.

------------------------------------------------------------------------

## 21. Definition of Done

The project is not production-ready merely because the model predicts a
fruit correctly in a notebook.

A pilot-ready release must have: - A documented supported produce
catalog and limitations. - A leakage-safe, store-representative dataset
and model card. - A measured model with per-class metrics and unknown
rejection. - A camera capture client and stable station state machine. -
A real supported scale integration or an explicitly marked simulator. -
Authoritative catalog and pricing integration or a clearly marked pilot
adapter. - A manual fallback for every critical failure. - Secure APIs,
RBAC, audit trails, and store isolation. - Transaction-safe basket
updates and idempotency. - Monitoring, alerts, backups, rollback, and
incident runbooks. - Hardware and end-to-end test evidence. - Privacy
and applicable Legal Metrology review. - A measured pilot report with
baseline comparisons and limitations.

------------------------------------------------------------------------

## 22. First 30 Days: Concrete Execution Plan

### Week 1 --- Define the real problem

-   Choose the first retail workflow: assisted checkout or
    self-checkout.
-   Define 20--40 pilot produce classes with a retailer-like catalog.
-   Create a SKU/visual-class/PLU mapping sheet.
-   Select camera, lighting, workstation, and scale candidates.
-   Write annotation rules and a privacy/data collection plan.
-   Build a clickable checkout workflow mockup.

### Week 2 --- Build a credible vision baseline

-   Gather public data for initial experimentation.
-   Collect a small original dataset using the target camera and capture
    area.
-   Create leakage-safe train/validation/test splits.
-   Train MobileNetV3 or EfficientNet baseline.
-   Produce per-class metrics and a confusion matrix.
-   Identify lookalike and unsupported classes.

### Week 3 --- Build the station workflow

-   Implement camera capture and image-quality checks.
-   Serve model predictions through a FastAPI endpoint or local
    inference process.
-   Display top-3 choices and manual search.
-   Implement confidence-based confirmation and unknown fallback.
-   Add a simulated scale adapter with explicit simulator labeling.

### Week 4 --- Connect retail logic

-   Implement PostgreSQL catalog and store-specific mappings.
-   Add a price service using decimal arithmetic.
-   Implement stable-weight validation and basket line creation.
-   Add audit events, request IDs, and idempotency.
-   Demonstrate a full capture → confirm → weigh → price → basket
    workflow.
-   Document what remains blocked on real hardware, POS access, and
    compliance review.

### First milestone

At the end of 30 days, the target is a **working, testable end-to-end
pilot prototype**, not a claim of enterprise deployment. It should be
possible to demonstrate a produce item being captured, recognized,
confirmed, weighed (real or clearly labelled simulated), priced from a
store catalog, and added to a basket with a traceable event record.

------------------------------------------------------------------------

## 23. Research Sources

1.  Toshiba Global Commerce Solutions, ELERA Produce Recognition ---
    https://commerce.toshiba.com/wps/portal/marketing/iot-suite/produce-recognition/
2.  NCR Voyix, Self-Checkout ---
    https://www.ncr.com/platform/retail-applications/checkout/self-checkout
3.  NCR Voyix, Loss Prevention / Picklist Assist ---
    https://www.ncr.com/platform/retail-applications/loss-prevention
4.  AWS, BigBasket AI-enabled checkout case study ---
    https://aws.amazon.com/blogs/machine-learning/how-bigbasket-improved-ai-enabled-checkout-at-their-physical-stores-using-amazon-sagemaker/
5.  AWS, Just Walk Out --- https://aws.amazon.com/just-walk-out/
6.  Amazon Physical Stores developer documentation ---
    https://developer.amazon.com/docs/physicalstores/welcome
7.  Instacart, Caper Carts ---
    https://www.instacart.com/company/enterprise-platform/connected-stores/caper-carts/
8.  IFPS, PLU Codes --- https://www.ifpsglobal.com/plu-codes
9.  Government of India, Department of Consumer Affairs, Legal Metrology
    --- https://consumeraffairs.gov.in/pages/legal-metrology-overview
10. Government of India, Department of Consumer Affairs, Weights and
    Measures ---
    https://consumeraffairs.gov.in/pages/weight-and-measures
11. Fruits-360 public dataset ---
    https://www.kaggle.com/datasets/moltean/fruits
12. Roboflow Universe --- https://universe.roboflow.com/

------------------------------------------------------------------------

## Final Product Principle

**Build the checkout system first, then make the AI reliable inside
it.** A model that recognizes fruit in a notebook is a prototype. A
system that handles ambiguity, verified weight, store-specific PLUs,
authoritative pricing, POS integration, offline behavior, human
fallback, security, and measurable store outcomes is a credible retail
product.
