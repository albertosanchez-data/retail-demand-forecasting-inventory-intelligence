CREATE TABLE public.stg_retail_demand (
    city_id INTEGER,
    store_id INTEGER,
    management_group_id INTEGER,
    first_category_id INTEGER,
    second_category_id INTEGER,
    third_category_id INTEGER,
    product_id INTEGER,
    dt DATE,
    sale_amount DOUBLE PRECISION,
    hours_sale DOUBLE PRECISION[],
    stock_hour6_22_cnt INTEGER,
    hours_stock_status SMALLINT[],
    discount DOUBLE PRECISION,
    holiday_flag SMALLINT,
    activity_flag SMALLINT,
    precpt DOUBLE PRECISION,
    avg_temperature DOUBLE PRECISION,
    avg_humidity DOUBLE PRECISION,
    avg_wind_level DOUBLE PRECISION,
    CONSTRAINT uq_stg_retail_demand
        UNIQUE (city_id, store_id, product_id, dt)
);