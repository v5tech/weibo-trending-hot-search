-- 创建表
CREATE OR REPLACE TABLE weibo_trends AS
SELECT
    -- CAST(regexp_extract(filename, '(\d{4}-\d{2}-\d{2})') AS DATE) AS trend_date,
    CAST(replace(split_part(filename, '/', -1), '.json', '') AS DATE) AS trend_date,
    key AS topic_name,
    CAST(json_extract_string(value, '$.hot') AS INTEGER) AS hot_value,
    json_extract_string(value, '$.url') AS url,
    filename AS source_file
FROM read_json_objects('./weibo-trending-hot-search/raw/*/*.json', filename=true),
    json_each(json);

-- 查看表结构
desc weibo_trends;

-- 查看表数据
select * from weibo_trends order by trend_date desc, hot_value desc;

-- 查看特定日期的热搜
SELECT * FROM weibo_trends
WHERE trend_date = '2025-07-14'
ORDER BY hot_value DESC;

-- 查看最近7天的热搜趋势
SELECT trend_date, COUNT(*) as topic_count, MAX(hot_value) as max_hot
FROM weibo_trends
WHERE trend_date >= CURRENT_DATE - INTERVAL 7 DAY
GROUP BY trend_date
ORDER BY trend_date DESC;

-- 查看某个话题的历史热度
SELECT trend_date, topic_name, hot_value
FROM weibo_trends
WHERE topic_name LIKE '%林俊杰%'
ORDER BY trend_date DESC;
