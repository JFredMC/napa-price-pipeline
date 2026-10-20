-- Capa staging: tipa y limpia el raw append-only (una fila por oferta y día).
with raw as (
    select *
    from read_csv(
        '{{ var("raw_glob") }}',
        header = true, hive_partitioning = false, union_by_name = true, all_varchar = true
    )
)
select
    cast(snapshot_date as date)                        as snapshot_date,
    offer_id,
    product_key,
    store_id,
    title,
    nullif(brand, '')                                  as brand,
    coalesce(nullif(category, ''), 'sin-categoria')    as category,
    cast(price as double)                              as price,
    greatest(cast(coalesce(nullif(list_price, ''), price) as double), cast(price as double)) as list_price,
    try_cast(nullif(size_amount, '') as double)        as size_amount,
    nullif(size_unit, '')                              as size_unit,
    nullif(seller, '')                                 as seller,
    try_cast(nullif(stock, '') as bigint)              as stock,
    nullif(url, '')                                    as url,
    try_cast(nullif(observed_at, '') as timestamptz)   as observed_at
from raw
where cast(price as double) > 0
qualify row_number() over (partition by offer_id, snapshot_date order by observed_at desc) = 1
