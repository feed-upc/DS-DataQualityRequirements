-- c-dqr4hl
with m as (select "wetlandId" as g, count(*) as r from {{ source('heleade','monitoring_site') }} group by "wetlandId")
select g, r from m where not (r >= 5)
