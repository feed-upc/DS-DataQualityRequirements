-- c-dqr3hl
with m as (select 100.0*count(*) filter (where ("breedingEvidence" IS NULL OR NOT ("breedingEvidence" IN ('courtship', 'nesting', 'chicks'))))/nullif(count(*),0) as r from {{ source('heleade','observation') }} where "detectionStatus" in ('notDetected'))
select r from m where not (r >= 100)
