-- Índice de precios por tienda y categoría (base 100 = primer precio observado de cada oferta).
-- Es un índice encadenado simple: promedio de precio / precio base de las ofertas presentes.
with base as (
    select offer_id, price as base_price
    from {{ ref('fct_daily_price') }}
    qualify row_number() over (partition by offer_id order by snapshot_date) = 1
)
select
    f.store_id,
    f.category,
    f.snapshot_date,
    count(*)                                           as offers,
    round(100 * avg(f.price / b.base_price), 2)        as price_index,
    round(avg(f.discount_pct), 2)                      as avg_discount_pct
from {{ ref('fct_daily_price') }} f
join base b using (offer_id)
group by all
