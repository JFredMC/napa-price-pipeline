-- Historial de cambios de precio: una fila cada vez que una oferta cambia de precio.
with ordered as (
    select
        f.*,
        lag(f.price) over (partition by f.offer_id order by f.snapshot_date) as prev_price,
        lag(f.snapshot_date) over (partition by f.offer_id order by f.snapshot_date) as prev_date
    from {{ ref('fct_daily_price') }} f
)
select
    o.offer_id,
    p.title,
    o.store_id,
    o.category,
    o.prev_date,
    o.snapshot_date                                    as change_date,
    o.prev_price,
    o.price                                            as new_price,
    round(100 * (o.price / o.prev_price - 1), 2)       as change_pct
from ordered o
join {{ ref('dim_product') }} p using (offer_id)
where o.prev_price is not null and o.price <> o.prev_price
