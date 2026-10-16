-- c-dqr1hl
with m as (select 100.0*count("location")/nullif(count(*),0) as r from {{ source('heleade','monitoring_site') }})
select r from m where not (r >= 100)
