-- El precio vigente nunca debe superar el precio de lista.
select * from {{ ref('fct_daily_price') }} where price > list_price
