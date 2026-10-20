-- Dimensión de producto: atributos más recientes de cada oferta.
select
    offer_id,
    product_key,
    store_id,
    title,
    brand,
    category,
    size_amount,
    size_unit,
    url,
    min(snapshot_date) over (partition by offer_id) as first_seen,
    max(snapshot_date) over (partition by offer_id) as last_seen,
    count(*) over (partition by offer_id)          as days_observed
from {{ ref('stg_offers') }}
qualify row_number() over (partition by offer_id order by snapshot_date desc) = 1
