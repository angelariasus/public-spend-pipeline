# Findings

What the marts show for contracting processes published between January 2024
and October 2026, as loaded on 2026-10-24. Every figure can be reproduced with
a query on the `marts` schema or from the Metabase dashboards; the sources are
refreshed daily, so later loads will differ slightly.

## Public procurement

- **S/ 222 billion awarded** in 184,139 awards by 2,992 entities to 81,201
  suppliers. By year: S/ 63 billion in 2024, S/ 95 billion in 2025 and S/ 64
  billion in 2026 to October.
- **Works take half the money.** Works are 52% of the awarded amount (S/ 116
  billion), services 29% and goods 19%.
- **Lima-based entities award 48%** of the total. The next departments,
  Piura, La Libertad and Cajamarca, are around 4% each. This follows the
  buyer's address, so national entities count as Lima.
- **Consortia win 60% of the amount with 22% of the awards.** Companies win
  36% with 59% of the awards; individuals and foreign suppliers share the
  remaining 4%. Large works go to consortia, routine purchases to companies.
- **2% of the awarded amount was in foreign currency** (S/ 7.9 billion after
  conversion), almost all of it with a rate reported by the award itself.

## Supplier concentration

- In 2025, **56% of the entities have a highly concentrated supplier base**
  (HHI of 2,500 or more), but they award only S/ 22 billion of the S/ 95
  billion. The 26% of entities with low concentration award S/ 58 billion.
  Concentration is a small-buyer phenomenon: 224 entities used a single
  supplier in 2025, and only two of them awarded S/ 10 million or more.
- The most concentrated entities with S/ 10M+ awarded in a year are district
  municipalities whose single supplier is a consortium formed for one work.

## Investment projects: contracted versus delivered

- **41% of processes fund an investment project**, and they carry 55% of the
  contracted amount. 33,532 project codes appear in budgets; 31,836 (95%) are
  found in the MEF files, with S/ 93 billion contracted. The 1,696 unmatched
  codes carry only S/ 0.9 billion.
- **Local governments hold most projects, national entities most spend.**
  Local governments: 25,996 projects, S/ 48 billion contracted, S/ 57 billion
  accrued over the projects' life. Regional governments: 3,435 projects, S/ 25
  billion contracted, S/ 47 billion accrued. National: 2,405 projects, S/ 20
  billion contracted, S/ 75 billion accrued.
- **Most projects with contracts are advancing.** Among active projects with
  at least S/ 1M contracted that report progress, the median physical
  progress is 82%.
- **459 projects are lagging:** at least S/ 1M contracted, a first contract
  signed over a year ago and less than 25% physical progress. Together they
  hold S/ 14 billion in contracts, 7% of the 6,416 projects old enough to be
  judged. By entity, the Ministry of Transport (MTC) leads with S/ 3.2 billion
  in 7 projects, followed by the regional governments of Piura (S/ 1.4
  billion), Cajamarca (12 projects, S/ 1.1 billion) and Ancash, SEDAPAL and
  the Ministry of Health.
- **354 projects have contracts above 150% of their cost**, S/ 2.7 billion in
  excess. The largest is a S/ 0.8 million sports court in Lima to which
  INVERMET charged S/ 1.6 billion of road and infrastructure works: a tagging
  error in the source, not an overrun. The flag is a data-quality signal
  before it is a finance one.

## About the data

- 1.2% of the processes linked to an investment fund several projects; their
  amounts are split equally.
- Accrued spend in MEF covers the whole project life, while the contracts in
  scope start in 2024, so accrued spend exceeds the contracted amount for
  two thirds of the matched projects. The ratio is useful to rank, not to
  audit.
- Thresholds and the full reasoning are in
  [design-decisions.md](design-decisions.md); column definitions in the
  [data dictionary](data-dictionary.md).
