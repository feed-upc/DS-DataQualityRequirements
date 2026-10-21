-- c-dqr2hl
with m as (select 100.0*count(*) filter (where regexp_matches(CAST("observedAt" AS VARCHAR), '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]+)?Z$'))/nullif(count(*),0) as r from {{ source('heleade','observation') }})
select r from m where not (r >= 100)
