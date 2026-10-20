-- Mejor día de la semana para comprar, por tienda y categoría.
-- Compara cada precio con el promedio de esa oferta; < 0 = más barato que su promedio.
-- `is_reliable` solo es true con suficientes días de historia (var min_days_for_weekday).
with rel as (
    select
        f.store_id,
        f.category,
        f.day_of_week,
        f.snapshot_date,
        f.price / avg(f.price) over (partition by f.offer_id) - 1 as rel_price
    from {{ ref('fct_daily_price') }} f
),
agg as (
    select
        store_id,
        category,
        day_of_week,
        count(distinct snapshot_date)                  as days_sampled,
        count(*)                                       as observations,
        round(100 * avg(rel_price), 3)                 as avg_vs_mean_pct
    from rel
    group by all
),
history as (
    select count(distinct snapshot_date) as total_days from {{ ref('fct_daily_price') }}
)
select
    a.*,
    ['domingo','lunes','martes','miércoles','jueves','viernes','sábado'][a.day_of_week + 1] as day_name,
    row_number() over (partition by store_id, category order by avg_vs_mean_pct, day_of_week) = 1 as is_best_day,
    h.total_days >= {{ var('min_days_for_weekday') }} as is_reliable
from agg a cross join history h
