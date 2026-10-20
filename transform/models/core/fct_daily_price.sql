-- Hecho diario: precio observado por oferta y día.
select
    s.offer_id || '|' || cast(s.snapshot_date as varchar) as price_id,
    s.offer_id,
    s.store_id,
    s.category,
    s.snapshot_date,
    dayofweek(s.snapshot_date)                         as day_of_week,  -- 0 = domingo
    s.price,
    s.list_price,
    round(100 * (1 - s.price / s.list_price), 2)       as discount_pct,
    case when s.size_amount > 0 then s.price / s.size_amount end as price_per_base_unit,
    s.stock
from {{ ref('stg_offers') }} s
