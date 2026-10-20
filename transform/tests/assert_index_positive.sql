select * from {{ ref('mart_price_index') }} where price_index <= 0
