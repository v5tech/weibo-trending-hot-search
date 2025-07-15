# 微博热搜数据分析案例

基于 `weibo_trends` 表结构，以下是一些实用的数据分析案例：

## 1. 基础统计分析

### 数据概览
```sql
-- 查看数据基本信息
SELECT
    COUNT(*) AS total_records,
    COUNT(DISTINCT trend_date) AS total_days,
    COUNT(DISTINCT topic_name) AS unique_topics,
    MIN(trend_date) AS earliest_date,
    MAX(trend_date) AS latest_date,
    AVG(hot_value) AS avg_hot_value,
    MAX(hot_value) AS max_hot_value
FROM weibo_trends;
```

### 每日热搜数量统计
```sql
-- 每日热搜话题数量趋势
SELECT
    trend_date,
    COUNT(*) AS topic_count,
    AVG(hot_value) AS avg_hot,
    MAX(hot_value) AS max_hot,
    MIN(hot_value) AS min_hot
FROM weibo_trends
GROUP BY trend_date
ORDER BY trend_date DESC;
```

## 2. 热度分析

### 历史最热话题TOP20
```sql
-- 历史最热话题排行榜
SELECT
    topic_name,
    hot_value,
    trend_date,
    url
FROM weibo_trends
ORDER BY hot_value DESC
LIMIT 20;
```

### 热度分布分析
```sql
-- 热度值分布区间统计
SELECT
    CASE
        WHEN hot_value >= 10000000 THEN '1000万+'
        WHEN hot_value >= 5000000 THEN '500万-1000万'
        WHEN hot_value >= 1000000 THEN '100万-500万'
        WHEN hot_value >= 500000 THEN '50万-100万'
        ELSE '50万以下'
    END AS hot_range,
    COUNT(*) AS topic_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS percentage
FROM weibo_trends
GROUP BY 1
ORDER BY MIN(hot_value) DESC;
```

## 3. 时间趋势分析

### 周热度趋势
```sql
-- 一周内每天的平均热度
SELECT
    DAYNAME(trend_date) AS day_of_week,
    DAYOFWEEK(trend_date) AS day_num,
    COUNT(*) AS topic_count,
    AVG(hot_value) AS avg_hot_value,
    MAX(hot_value) AS max_hot_value
FROM weibo_trends
GROUP BY DAYNAME(trend_date), DAYOFWEEK(trend_date)
ORDER BY day_num;
```

### 月度热搜趋势
```sql
-- 按月统计热搜趋势
SELECT
    DATE_TRUNC('month', trend_date) AS month,
    COUNT(*) AS total_topics,
    AVG(hot_value) AS avg_hot,
    MAX(hot_value) AS max_hot,
    COUNT(DISTINCT topic_name) AS unique_topics
FROM weibo_trends
GROUP BY DATE_TRUNC('month', trend_date)
ORDER BY month DESC;
```

## 4. 话题分析

### 重复上榜话题
```sql
-- 多次上热搜的话题
SELECT
    topic_name,
    COUNT(*) AS appearance_count,
    AVG(hot_value) AS avg_hot,
    MAX(hot_value) AS max_hot,
    MIN(trend_date) AS first_appearance,
    MAX(trend_date) AS last_appearance
FROM weibo_trends
GROUP BY topic_name
HAVING COUNT(*) > 1
ORDER BY appearance_count DESC, max_hot DESC;
```

### 话题热度持续性分析
```sql
-- 连续多天上榜的话题
WITH consecutive_topics AS (
    SELECT
        topic_name,
        trend_date,
        hot_value,
        LAG(trend_date) OVER (PARTITION BY topic_name ORDER BY trend_date) AS prev_date
    FROM weibo_trends
),
topic_streaks AS (
    SELECT
        topic_name,
        trend_date,
        hot_value,
        CASE
            WHEN prev_date IS NULL OR trend_date - prev_date > 1 THEN 1
            ELSE 0
        END AS is_new_streak
    FROM consecutive_topics
),
streak_groups AS (
    SELECT
        topic_name,
        trend_date,
        hot_value,
        SUM(is_new_streak) OVER (PARTITION BY topic_name ORDER BY trend_date) AS streak_group
    FROM topic_streaks
)
SELECT
    topic_name,
    COUNT(*) AS consecutive_days,
    MIN(trend_date) AS streak_start,
    MAX(trend_date) AS streak_end,
    AVG(hot_value) AS avg_hot_during_streak,
    MAX(hot_value) AS peak_hot
FROM streak_groups
GROUP BY topic_name, streak_group
HAVING COUNT(*) >= 3  -- 连续3天以上
ORDER BY consecutive_days DESC, peak_hot DESC;
```

## 5. 关键词分析

### 热门关键词提取
```sql
-- 话题名称中的热门关键词（简单版本）
WITH keywords AS (
    SELECT
        CASE
            WHEN topic_name LIKE '%演唱会%' THEN '演唱会'
            WHEN topic_name LIKE '%电影%' THEN '电影'
            WHEN topic_name LIKE '%明星%' OR topic_name LIKE '%艺人%' THEN '娱乐明星'
            WHEN topic_name LIKE '%疫情%' OR topic_name LIKE '%新冠%' THEN '疫情'
            WHEN topic_name LIKE '%春节%' OR topic_name LIKE '%过年%' THEN '春节'
            WHEN topic_name LIKE '%天气%' OR topic_name LIKE '%下雨%' OR topic_name LIKE '%下雪%' THEN '天气'
            WHEN topic_name LIKE '%股票%' OR topic_name LIKE '%股市%' THEN '股市'
            ELSE '其他'
        END AS keyword_category,
        topic_name,
        hot_value,
        trend_date
    FROM weibo_trends
)
SELECT
    keyword_category,
    COUNT(*) AS topic_count,
    AVG(hot_value) AS avg_hot,
    MAX(hot_value) AS max_hot
FROM keywords
WHERE keyword_category != '其他'
GROUP BY keyword_category
ORDER BY topic_count DESC;
```

## 6. 异常检测

### 热度异常值检测
```sql
-- 检测异常高热度的话题
WITH stats AS (
    SELECT
        AVG(hot_value) AS mean_hot,
        STDDEV(hot_value) AS std_hot
    FROM weibo_trends
)
SELECT
    t.topic_name,
    t.hot_value,
    t.trend_date,
    ROUND((t.hot_value - s.mean_hot) / s.std_hot, 2) AS z_score
FROM weibo_trends t
CROSS JOIN stats s
WHERE (t.hot_value - s.mean_hot) / s.std_hot > 3  -- 3个标准差以上
ORDER BY z_score DESC;
```

## 7. 对比分析

### 工作日vs周末热搜对比
```sql
-- 工作日与周末的热搜对比
SELECT
    CASE
        WHEN DAYOFWEEK(trend_date) IN (1, 7) THEN '周末'
        ELSE '工作日'
    END AS day_type,
    COUNT(*) AS topic_count,
    AVG(hot_value) AS avg_hot,
    MAX(hot_value) AS max_hot,
    COUNT(DISTINCT topic_name) AS unique_topics
FROM weibo_trends
GROUP BY 1;
```

### 最近7天vs历史平均对比
```sql
-- 最近7天与历史平均的对比
WITH recent_data AS (
    SELECT AVG(hot_value) AS recent_avg_hot
    FROM weibo_trends
    WHERE trend_date >= CURRENT_DATE - INTERVAL 7 DAY
),
historical_data AS (
    SELECT AVG(hot_value) AS historical_avg_hot
    FROM weibo_trends
    WHERE trend_date < CURRENT_DATE - INTERVAL 7 DAY
)
SELECT
    r.recent_avg_hot,
    h.historical_avg_hot,
    ROUND((r.recent_avg_hot - h.historical_avg_hot) / h.historical_avg_hot * 100, 2) AS change_percentage
FROM recent_data r
CROSS JOIN historical_data h;
```

## 8. 综合排行榜

### 话题影响力综合评分
```sql
-- 综合考虑热度和持续性的话题影响力评分
WITH topic_metrics AS (
    SELECT
        topic_name,
        COUNT(*) AS appearance_days,
        AVG(hot_value) AS avg_hot,
        MAX(hot_value) AS peak_hot,
        SUM(hot_value) AS total_hot
    FROM weibo_trends
    GROUP BY topic_name
)
SELECT
    topic_name,
    appearance_days,
    avg_hot,
    peak_hot,
    total_hot,
    -- 综合评分：考虑峰值热度、平均热度和持续天数
    ROUND(
        (peak_hot * 0.4 + avg_hot * 0.3 + appearance_days * 100000 * 0.3),
        0
    ) AS influence_score
FROM topic_metrics
WHERE appearance_days >= 1
ORDER BY influence_score DESC
LIMIT 50;
```

这些分析案例涵盖了：
- **描述性统计**：基础数据概览
- **趋势分析**：时间维度的变化趋势
- **分类分析**：不同类型话题的特征
- **异常检测**：识别特殊事件
- **对比分析**：不同时期/类型的对比
- **综合评估**：多维度的综合评分

## 9. 高级时间序列分析

### 热度变化率分析
```sql
-- 计算每日热度变化率和趋势
WITH daily_stats AS (
    SELECT
        trend_date,
        COUNT(*) AS topic_count,
        AVG(hot_value) AS avg_hot,
        SUM(hot_value) AS total_hot
    FROM weibo_trends
    GROUP BY trend_date
),
trend_analysis AS (
    SELECT
        trend_date,
        avg_hot,
        total_hot,
        LAG(avg_hot) OVER (ORDER BY trend_date) AS prev_avg_hot,
        LAG(total_hot) OVER (ORDER BY trend_date) AS prev_total_hot,
        AVG(avg_hot) OVER (ORDER BY trend_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS ma7_avg_hot
    FROM daily_stats
)
SELECT
    trend_date,
    avg_hot,
    ma7_avg_hot,
    ROUND((avg_hot - prev_avg_hot) / prev_avg_hot * 100, 2) AS daily_change_pct,
    ROUND((total_hot - prev_total_hot) / prev_total_hot * 100, 2) AS total_change_pct,
    CASE
        WHEN avg_hot > ma7_avg_hot * 1.2 THEN '异常高'
        WHEN avg_hot < ma7_avg_hot * 0.8 THEN '异常低'
        ELSE '正常'
    END AS trend_status
FROM trend_analysis
WHERE prev_avg_hot IS NOT NULL
ORDER BY trend_date DESC;
```

### 季节性模式分析
```sql
-- 分析不同季节的热搜模式
WITH seasonal_data AS (
    SELECT
        topic_name,
        hot_value,
        trend_date,
        CASE
            WHEN MONTH(trend_date) IN (3,4,5) THEN '春季'
            WHEN MONTH(trend_date) IN (6,7,8) THEN '夏季'
            WHEN MONTH(trend_date) IN (9,10,11) THEN '秋季'
            ELSE '冬季'
        END AS season,
        CASE
            WHEN MONTH(trend_date) IN (1,2) THEN '春节期间'
            WHEN MONTH(trend_date) = 6 THEN '高考季'
            WHEN MONTH(trend_date) IN (7,8) THEN '暑假'
            WHEN MONTH(trend_date) IN (11,12) THEN '年末'
            ELSE '平常时期'
        END AS special_period
    FROM weibo_trends
)
SELECT
    season,
    special_period,
    COUNT(*) AS topic_count,
    AVG(hot_value) AS avg_hot,
    MAX(hot_value) AS max_hot,
    COUNT(DISTINCT topic_name) AS unique_topics,
    ROUND(AVG(hot_value) / (SELECT AVG(hot_value) FROM weibo_trends) * 100, 2) AS relative_heat_index
FROM seasonal_data
GROUP BY season, special_period
ORDER BY season, avg_hot DESC;
```

## 10. 网络分析和关联性

### 话题共现分析
```sql
-- 分析同一天出现的话题组合
WITH topic_pairs AS (
    SELECT
        a.trend_date,
        a.topic_name AS topic_a,
        b.topic_name AS topic_b,
        a.hot_value AS hot_a,
        b.hot_value AS hot_b
    FROM weibo_trends a
    JOIN weibo_trends b ON a.trend_date = b.trend_date
    WHERE a.topic_name < b.topic_name  -- 避免重复配对
)
SELECT
    topic_a,
    topic_b,
    COUNT(*) AS co_occurrence_days,
    AVG(hot_a + hot_b) AS avg_combined_hot,
    MAX(hot_a + hot_b) AS max_combined_hot,
    ROUND(COUNT(*) * 100.0 / (
        SELECT COUNT(DISTINCT trend_date) FROM weibo_trends
    ), 2) AS co_occurrence_rate
FROM topic_pairs
GROUP BY topic_a, topic_b
HAVING COUNT(*) >= 3  -- 至少共现3天
ORDER BY co_occurrence_days DESC, avg_combined_hot DESC
LIMIT 20;
```

### 话题影响力传播分析
```sql
-- 分析话题的传播模式（基于热度变化）
WITH topic_evolution AS (
    SELECT
        topic_name,
        trend_date,
        hot_value,
        ROW_NUMBER() OVER (PARTITION BY topic_name ORDER BY trend_date) AS day_sequence,
        FIRST_VALUE(hot_value) OVER (PARTITION BY topic_name ORDER BY trend_date) AS initial_hot,
        MAX(hot_value) OVER (PARTITION BY topic_name) AS peak_hot
    FROM weibo_trends
),
spread_pattern AS (
    SELECT
        topic_name,
        COUNT(*) AS total_days,
        initial_hot,
        peak_hot,
        ROUND(peak_hot / initial_hot, 2) AS amplification_ratio,
        CASE
            WHEN peak_hot = initial_hot THEN '瞬时爆发'
            WHEN peak_hot / initial_hot > 5 THEN '病毒式传播'
            WHEN peak_hot / initial_hot > 2 THEN '稳步增长'
            ELSE '平稳传播'
        END AS spread_type
    FROM topic_evolution
    GROUP BY topic_name, initial_hot, peak_hot
)
SELECT
    spread_type,
    COUNT(*) AS topic_count,
    AVG(amplification_ratio) AS avg_amplification,
    AVG(total_days) AS avg_duration,
    AVG(peak_hot) AS avg_peak_hot
FROM spread_pattern
WHERE total_days >= 2
GROUP BY spread_type
ORDER BY avg_amplification DESC;
```

## 11. 预测性分析

### 热度预测模型（简单线性趋势）
```sql
-- 基于历史趋势预测未来热度
WITH trend_data AS (
    SELECT
        trend_date,
        AVG(hot_value) AS daily_avg_hot,
        ROW_NUMBER() OVER (ORDER BY trend_date) AS day_number
    FROM weibo_trends
    GROUP BY trend_date
),
regression_stats AS (
    SELECT
        COUNT(*) AS n,
        SUM(day_number) AS sum_x,
        SUM(daily_avg_hot) AS sum_y,
        SUM(day_number * daily_avg_hot) AS sum_xy,
        SUM(day_number * day_number) AS sum_x2
    FROM trend_data
),
regression_coeff AS (
    SELECT
        (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x) AS slope,
        (sum_y - ((n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)) * sum_x) / n AS intercept
    FROM regression_stats
)
SELECT
    'Historical' AS data_type,
    trend_date,
    daily_avg_hot AS actual_hot,
    NULL AS predicted_hot
FROM trend_data
WHERE trend_date >= (SELECT MAX(trend_date) - INTERVAL 30 DAY FROM trend_data)

UNION ALL

SELECT
    'Predicted' AS data_type,
    (SELECT MAX(trend_date) FROM trend_data) + INTERVAL (generate_series) DAY AS trend_date,
    NULL AS actual_hot,
    ROUND(intercept + slope * ((SELECT MAX(day_number) FROM trend_data) + generate_series), 0) AS predicted_hot
FROM regression_coeff
CROSS JOIN generate_series(1, 7)  -- 预测未来7天
ORDER BY trend_date;
```

### 话题生命周期分析
```sql
-- 分析话题的生命周期阶段
WITH topic_lifecycle AS (
    SELECT
        topic_name,
        trend_date,
        hot_value,
        ROW_NUMBER() OVER (PARTITION BY topic_name ORDER BY trend_date) AS day_in_cycle,
        COUNT(*) OVER (PARTITION BY topic_name) AS total_cycle_days,
        MAX(hot_value) OVER (PARTITION BY topic_name) AS peak_hot_value,
        MIN(trend_date) OVER (PARTITION BY topic_name) AS start_date,
        MAX(trend_date) OVER (PARTITION BY topic_name) AS end_date
    FROM weibo_trends
),
lifecycle_stages AS (
    SELECT
        topic_name,
        trend_date,
        hot_value,
        day_in_cycle,
        total_cycle_days,
        peak_hot_value,
        CASE
            WHEN day_in_cycle <= total_cycle_days * 0.3 THEN '萌芽期'
            WHEN day_in_cycle <= total_cycle_days * 0.6 THEN '成长期'
            WHEN day_in_cycle <= total_cycle_days * 0.8 THEN '成熟期'
            ELSE '衰退期'
        END AS lifecycle_stage,
        ROUND(hot_value / peak_hot_value * 100, 2) AS heat_percentage
    FROM topic_lifecycle
)
SELECT
    lifecycle_stage,
    COUNT(*) AS observation_count,
    AVG(heat_percentage) AS avg_heat_percentage,
    AVG(total_cycle_days) AS avg_total_days,
    COUNT(DISTINCT topic_name) AS unique_topics
FROM lifecycle_stages
WHERE total_cycle_days >= 3  -- 至少持续3天的话题
GROUP BY lifecycle_stage
ORDER BY
    CASE lifecycle_stage
        WHEN '萌芽期' THEN 1
        WHEN '成长期' THEN 2
        WHEN '成熟期' THEN 3
        WHEN '衰退期' THEN 4
    END;
```

## 12. 竞争分析

### 话题竞争强度分析
```sql
-- 分析每日话题竞争激烈程度
WITH daily_competition AS (
    SELECT
        trend_date,
        COUNT(*) AS total_topics,
        AVG(hot_value) AS avg_hot,
        STDDEV(hot_value) AS hot_stddev,
        MAX(hot_value) AS max_hot,
        MIN(hot_value) AS min_hot,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY hot_value) AS median_hot,
        PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY hot_value) AS p90_hot,
        PERCENTILE_CONT(0.1) WITHIN GROUP (ORDER BY hot_value) AS p10_hot
    FROM weibo_trends
    GROUP BY trend_date
)
SELECT
    trend_date,
    total_topics,
    ROUND(avg_hot, 0) AS avg_hot,
    ROUND(hot_stddev, 0) AS hot_stddev,
    ROUND(hot_stddev / avg_hot, 3) AS coefficient_of_variation,
    ROUND((max_hot - min_hot) / avg_hot, 2) AS heat_range_ratio,
    ROUND((p90_hot - p10_hot) / median_hot, 2) AS competition_intensity,
    CASE
        WHEN hot_stddev / avg_hot > 1.5 THEN '极度竞争'
        WHEN hot_stddev / avg_hot > 1.0 THEN '激烈竞争'
        WHEN hot_stddev / avg_hot > 0.5 THEN '中等竞争'
        ELSE '温和竞争'
    END AS competition_level
FROM daily_competition
ORDER BY trend_date DESC;
```

### 热搜榜位置分析
```sql
-- 模拟热搜榜排名分析
WITH daily_rankings AS (
    SELECT
        trend_date,
        topic_name,
        hot_value,
        ROW_NUMBER() OVER (PARTITION BY trend_date ORDER BY hot_value DESC) AS daily_rank,
        COUNT(*) OVER (PARTITION BY trend_date) AS total_topics_that_day
    FROM weibo_trends
),
ranking_analysis AS (
    SELECT
        topic_name,
        COUNT(*) AS total_appearances,
        AVG(daily_rank) AS avg_rank,
        MIN(daily_rank) AS best_rank,
        MAX(daily_rank) AS worst_rank,
        COUNT(CASE WHEN daily_rank <= 10 THEN 1 END) AS top10_days,
        COUNT(CASE WHEN daily_rank <= 3 THEN 1 END) AS top3_days,
        AVG(hot_value) AS avg_hot_value
    FROM daily_rankings
    GROUP BY topic_name
)
SELECT
    topic_name,
    total_appearances,
    ROUND(avg_rank, 1) AS avg_rank,
    best_rank,
    ROUND(top10_days * 100.0 / total_appearances, 1) AS top10_rate,
    ROUND(top3_days * 100.0 / total_appearances, 1) AS top3_rate,
    ROUND(avg_hot_value, 0) AS avg_hot_value,
    CASE
        WHEN avg_rank <= 5 THEN '顶级话题'
        WHEN avg_rank <= 15 THEN '热门话题'
        WHEN avg_rank <= 30 THEN '中等话题'
        ELSE '普通话题'
    END AS topic_tier
FROM ranking_analysis
WHERE total_appearances >= 3
ORDER BY avg_rank ASC, total_appearances DESC;
```

## 13. 用户行为洞察

### 热度阈值分析
```sql
-- 分析不同热度阈值的话题分布
WITH heat_thresholds AS (
    SELECT
        topic_name,
        hot_value,
        trend_date,
        CASE
            WHEN hot_value >= 50000000 THEN '现象级(5000万+)'
            WHEN hot_value >= 20000000 THEN '超热门(2000万+)'
            WHEN hot_value >= 10000000 THEN '热门(1000万+)'
            WHEN hot_value >= 5000000 THEN '中热(500万+)'
            WHEN hot_value >= 1000000 THEN '小热(100万+)'
            ELSE '普通(100万以下)'
        END AS heat_level,
        NTILE(10) OVER (ORDER BY hot_value) AS heat_decile
    FROM weibo_trends
)
SELECT
    heat_level,
    COUNT(*) AS topic_count,
    COUNT(DISTINCT topic_name) AS unique_topics,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS percentage,
    AVG(hot_value) AS avg_hot_in_level,
    MIN(hot_value) AS min_hot_in_level,
    MAX(hot_value) AS max_hot_in_level
FROM heat_thresholds
GROUP BY heat_level
ORDER BY min_hot_in_level DESC;
```

### 话题新鲜度分析
```sql
-- 分析新话题vs重复话题的模式
WITH topic_history AS (
    SELECT
        topic_name,
        trend_date,
        hot_value,
        MIN(trend_date) OVER (PARTITION BY topic_name) AS first_appearance,
        COUNT(*) OVER (PARTITION BY topic_name) AS total_appearances,
        ROW_NUMBER() OVER (PARTITION BY topic_name ORDER BY trend_date) AS appearance_sequence
    FROM weibo_trends
),
freshness_analysis AS (
    SELECT
        trend_date,
        COUNT(*) AS total_topics,
        COUNT(CASE WHEN appearance_sequence = 1 THEN 1 END) AS new_topics,
        COUNT(CASE WHEN appearance_sequence > 1 THEN 1 END) AS returning_topics,
        AVG(CASE WHEN appearance_sequence = 1 THEN hot_value END) AS avg_new_topic_hot,
        AVG(CASE WHEN appearance_sequence > 1 THEN hot_value END) AS avg_returning_topic_hot
    FROM topic_history
    GROUP BY trend_date
)
SELECT
    trend_date,
    total_topics,
    new_topics,
    returning_topics,
    ROUND(new_topics * 100.0 / total_topics, 1) AS new_topic_percentage,
    ROUND(avg_new_topic_hot, 0) AS avg_new_topic_hot,
    ROUND(avg_returning_topic_hot, 0) AS avg_returning_topic_hot,
    CASE
        WHEN new_topics * 100.0 / total_topics > 80 THEN '高新鲜度'
        WHEN new_topics * 100.0 / total_topics > 60 THEN '中新鲜度'
        ELSE '低新鲜度'
    END AS freshness_level
FROM freshness_analysis
ORDER BY trend_date DESC;
```

## 14. 综合评估模型

### 话题价值评估模型
```sql
-- 综合多个维度评估话题价值
WITH topic_metrics AS (
    SELECT
        topic_name,
        COUNT(*) AS persistence_days,
        AVG(hot_value) AS avg_hot,
        MAX(hot_value) AS peak_hot,
        MIN(hot_value) AS min_hot,
        STDDEV(hot_value) AS hot_volatility,
        SUM(hot_value) AS total_heat,
        MIN(trend_date) AS start_date,
        MAX(trend_date) AS end_date
    FROM weibo_trends
    GROUP BY topic_name
),
value_scoring AS (
    SELECT
        topic_name,
        persistence_days,
        peak_hot,
        avg_hot,
        total_heat,
        hot_volatility,
        -- 持续性得分 (0-25分)
        LEAST(persistence_days * 5, 25) AS persistence_score,
        -- 峰值热度得分 (0-25分)
        CASE
            WHEN peak_hot >= 50000000 THEN 25
            WHEN peak_hot >= 20000000 THEN 20
            WHEN peak_hot >= 10000000 THEN 15
            WHEN peak_hot >= 5000000 THEN 10
            ELSE 5
        END AS peak_score,
        -- 平均热度得分 (0-25分)
        CASE
            WHEN avg_hot >= 20000000 THEN 25
            WHEN avg_hot >= 10000000 THEN 20
            WHEN avg_hot >= 5000000 THEN 15
            WHEN avg_hot >= 2000000 THEN 10
            ELSE 5
        END AS avg_score,
        -- 稳定性得分 (0-25分，波动越小得分越高)
        CASE
            WHEN hot_volatility / avg_hot <= 0.3 THEN 25
            WHEN hot_volatility / avg_hot <= 0.6 THEN 20
            WHEN hot_volatility / avg_hot <= 1.0 THEN 15
            WHEN hot_volatility / avg_hot <= 1.5 THEN 10
            ELSE 5
        END AS stability_score
    FROM topic_metrics
    WHERE persistence_days >= 1
)
SELECT
    topic_name,
    persistence_days,
    ROUND(peak_hot, 0) AS peak_hot,
    ROUND(avg_hot, 0) AS avg_hot,
    persistence_score,
    peak_score,
    avg_score,
    stability_score,
    (persistence_score + peak_score + avg_score + stability_score) AS total_value_score,
    CASE
        WHEN (persistence_score + peak_score + avg_score + stability_score) >= 80 THEN 'S级话题'
        WHEN (persistence_score + peak_score + avg_score + stability_score) >= 60 THEN 'A级话题'
        WHEN (persistence_score + peak_score + avg_score + stability_score) >= 40 THEN 'B级话题'
        ELSE 'C级话题'
    END AS topic_grade
FROM value_scoring
ORDER BY total_value_score DESC
LIMIT 50;
```

这些高级分析案例涵盖了：

- **时间序列分析**：趋势预测、季节性模式
- **网络分析**：话题关联、传播模式
- **预测建模**：简单的线性回归预测
- **竞争分析**：市场竞争强度、排名分析
- **用户行为**：参与度分析、新鲜度评估
- **综合评估**：多维度价值评分模型

这些分析可以帮助你深入理解微博热搜的运作机制，识别趋势和模式，为内容策略和营销决策提供数据支持。

---

# 微博热搜趋势数据分析案例

## 1. 数据概览与基础统计

### 1.1 数据质量检查
```sql
-- 数据总量统计
SELECT COUNT(*) as total_records FROM weibo_trends;

-- 数据时间范围
SELECT
    MIN(trend_date) as earliest_date,
    MAX(trend_date) as latest_date,
    DATEDIFF('day', MIN(trend_date), MAX(trend_date)) as date_span_days
FROM weibo_trends;

-- 数据完整性检查
SELECT
    COUNT(*) as total_records,
    COUNT(DISTINCT trend_date) as unique_dates,
    COUNT(DISTINCT topic_name) as unique_topics,
    SUM(CASE WHEN hot_value IS NULL THEN 1 ELSE 0 END) as null_hot_values,
    SUM(CASE WHEN topic_name IS NULL THEN 1 ELSE 0 END) as null_topics
FROM weibo_trends;
```

### 1.2 热度值分布分析
```sql
-- 热度值基础统计
SELECT
    MIN(hot_value) as min_hot_value,
    MAX(hot_value) as max_hot_value,
    AVG(hot_value) as avg_hot_value,
    MEDIAN(hot_value) as median_hot_value,
    STDDEV(hot_value) as std_hot_value
FROM weibo_trends;

-- 热度值分布区间
SELECT
    CASE
        WHEN hot_value < 10000 THEN '低热度(<1万)'
        WHEN hot_value < 100000 THEN '中等热度(1-10万)'
        WHEN hot_value < 1000000 THEN '高热度(10-100万)'
        ELSE '超高热度(>100万)'
    END as hot_level,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
FROM weibo_trends
GROUP BY 1
ORDER BY MIN(hot_value);
```

## 2. 时间维度分析

### 2.1 日度热搜趋势
```sql
-- 每日热搜数量和平均热度
SELECT
    trend_date,
    COUNT(*) as daily_topics_count,
    AVG(hot_value) as avg_daily_hot_value,
    MAX(hot_value) as max_daily_hot_value,
    MIN(hot_value) as min_daily_hot_value
FROM weibo_trends
GROUP BY trend_date
ORDER BY trend_date;

-- 工作日vs周末热搜对比
SELECT
    CASE
        WHEN DAYOFWEEK(trend_date) IN (1, 7) THEN '周末'
        ELSE '工作日'
    END as day_type,
    COUNT(*) as topics_count,
    AVG(hot_value) as avg_hot_value,
    MAX(hot_value) as max_hot_value
FROM weibo_trends
GROUP BY 1;
```

### 2.2 周度和月度趋势
```sql
-- 周度趋势分析
SELECT
    YEAR(trend_date) as year,
    WEEK(trend_date) as week,
    COUNT(*) as weekly_topics,
    AVG(hot_value) as avg_weekly_hot_value
FROM weibo_trends
GROUP BY 1, 2
ORDER BY 1, 2;

-- 月度趋势分析
SELECT
    DATE_TRUNC('month', trend_date) as month,
    COUNT(*) as monthly_topics,
    AVG(hot_value) as avg_monthly_hot_value,
    COUNT(DISTINCT topic_name) as unique_topics_count
FROM weibo_trends
GROUP BY 1
ORDER BY 1;
```

## 3. 话题内容分析

### 3.1 热门话题排行
```sql
-- 总体最热话题TOP20
SELECT
    topic_name,
    COUNT(*) as appearance_count,
    AVG(hot_value) as avg_hot_value,
    MAX(hot_value) as max_hot_value,
    MIN(trend_date) as first_appearance,
    MAX(trend_date) as last_appearance
FROM weibo_trends
GROUP BY topic_name
ORDER BY max_hot_value DESC
LIMIT 20;

-- 持续热度话题（出现天数最多）
SELECT
    topic_name,
    COUNT(DISTINCT trend_date) as days_on_trend,
    AVG(hot_value) as avg_hot_value,
    MAX(hot_value) as peak_hot_value
FROM weibo_trends
GROUP BY topic_name
HAVING COUNT(DISTINCT trend_date) > 1
ORDER BY days_on_trend DESC
LIMIT 15;
```

### 3.2 话题关键词分析
```sql
-- 话题名称长度分析
SELECT
    LENGTH(topic_name) as topic_length,
    COUNT(*) as count,
    AVG(hot_value) as avg_hot_value
FROM weibo_trends
GROUP BY 1
ORDER BY 1;

-- 包含特定关键词的话题分析
SELECT
    '明星娱乐' as category,
    COUNT(*) as count,
    AVG(hot_value) as avg_hot_value
FROM weibo_trends
WHERE topic_name LIKE '%明星%' OR topic_name LIKE '%娱乐%' OR topic_name LIKE '%电影%'

UNION ALL

SELECT
    '社会新闻' as category,
    COUNT(*) as count,
    AVG(hot_value) as avg_hot_value
FROM weibo_trends
WHERE topic_name LIKE '%社会%' OR topic_name LIKE '%新闻%' OR topic_name LIKE '%事件%'

UNION ALL

SELECT
    '体育赛事' as category,
    COUNT(*) as count,
    AVG(hot_value) as avg_hot_value
FROM weibo_trends
WHERE topic_name LIKE '%体育%' OR topic_name LIKE '%比赛%' OR topic_name LIKE '%奥运%';
```

## 4. 热度变化模式分析

### 4.1 话题生命周期分析
```sql
-- 话题热度变化轨迹
WITH topic_lifecycle AS (
    SELECT
        topic_name,
        trend_date,
        hot_value,
        ROW_NUMBER() OVER (PARTITION BY topic_name ORDER BY trend_date) as day_sequence,
        LAG(hot_value) OVER (PARTITION BY topic_name ORDER BY trend_date) as prev_hot_value
    FROM weibo_trends
    WHERE topic_name IN (
        SELECT topic_name
        FROM weibo_trends
        GROUP BY topic_name
        HAVING COUNT(DISTINCT trend_date) >= 3
    )
)
SELECT
    topic_name,
    day_sequence,
    hot_value,
    prev_hot_value,
    CASE
        WHEN prev_hot_value IS NULL THEN 'Initial'
        WHEN hot_value > prev_hot_value THEN 'Rising'
        WHEN hot_value < prev_hot_value THEN 'Declining'
        ELSE 'Stable'
    END as trend_direction
FROM topic_lifecycle
ORDER BY topic_name, day_sequence;
```

### 4.2 热度爆发模式识别
```sql
-- 识别热度爆发话题（单日热度增长超过100%）
WITH daily_growth AS (
    SELECT
        topic_name,
        trend_date,
        hot_value,
        LAG(hot_value) OVER (PARTITION BY topic_name ORDER BY trend_date) as prev_hot_value,
        CASE
            WHEN LAG(hot_value) OVER (PARTITION BY topic_name ORDER BY trend_date) > 0
            THEN (hot_value - LAG(hot_value) OVER (PARTITION BY topic_name ORDER BY trend_date)) * 100.0 / LAG(hot_value) OVER (PARTITION BY topic_name ORDER BY trend_date)
            ELSE NULL
        END as growth_rate
    FROM weibo_trends
)
SELECT
    topic_name,
    trend_date,
    hot_value,
    prev_hot_value,
    ROUND(growth_rate, 2) as growth_rate_percent
FROM daily_growth
WHERE growth_rate > 100
ORDER BY growth_rate DESC;
```

## 5. 高级分析与洞察

### 5.1 热搜预测模型特征工程
```sql
-- 构建预测特征
WITH feature_engineering AS (
    SELECT
        topic_name,
        trend_date,
        hot_value,
        -- 时间特征
        DAYOFWEEK(trend_date) as day_of_week,
        DAYOFMONTH(trend_date) as day_of_month,
        MONTH(trend_date) as month,
        -- 历史特征
        LAG(hot_value, 1) OVER (PARTITION BY topic_name ORDER BY trend_date) as hot_value_lag1,
        LAG(hot_value, 2) OVER (PARTITION BY topic_name ORDER BY trend_date) as hot_value_lag2,
        -- 移动平均
        AVG(hot_value) OVER (PARTITION BY topic_name ORDER BY trend_date ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) as ma_3day,
        -- 话题特征
        LENGTH(topic_name) as topic_length,
        COUNT(*) OVER (PARTITION BY topic_name) as topic_frequency
    FROM weibo_trends
)
SELECT * FROM feature_engineering
WHERE hot_value_lag1 IS NOT NULL;
```

### 5.2 异常检测分析
```sql
-- 基于统计方法的异常热度检测
WITH stats AS (
    SELECT
        AVG(hot_value) as mean_hot_value,
        STDDEV(hot_value) as std_hot_value
    FROM weibo_trends
),
outliers AS (
    SELECT
        t.*,
        s.mean_hot_value,
        s.std_hot_value,
        (t.hot_value - s.mean_hot_value) / s.std_hot_value as z_score
    FROM weibo_trends t
    CROSS JOIN stats s
)
SELECT
    trend_date,
    topic_name,
    hot_value,
    ROUND(z_score, 2) as z_score,
    CASE
        WHEN ABS(z_score) > 3 THEN '极端异常'
        WHEN ABS(z_score) > 2 THEN '显著异常'
        ELSE '正常'
    END as anomaly_level
FROM outliers
WHERE ABS(z_score) > 2
ORDER BY ABS(z_score) DESC;
```

### 5.3 话题相关性分析
```sql
-- 同期热搜话题关联分析
WITH daily_topics AS (
    SELECT
        trend_date,
        ARRAY_AGG(topic_name ORDER BY hot_value DESC) as topics_array,
        COUNT(*) as daily_topic_count
    FROM weibo_trends
    GROUP BY trend_date
),
topic_cooccurrence AS (
    SELECT
        t1.topic_name as topic1,
        t2.topic_name as topic2,
        COUNT(*) as cooccurrence_count
    FROM weibo_trends t1
    JOIN weibo_trends t2 ON t1.trend_date = t2.trend_date AND t1.topic_name < t2.topic_name
    GROUP BY t1.topic_name, t2.topic_name
    HAVING COUNT(*) > 1
)
SELECT
    topic1,
    topic2,
    cooccurrence_count,
    ROUND(cooccurrence_count * 100.0 / (SELECT COUNT(DISTINCT trend_date) FROM weibo_trends), 2) as cooccurrence_rate
FROM topic_cooccurrence
ORDER BY cooccurrence_count DESC
LIMIT 20;
```

## 6. 业务洞察与建议

### 6.1 热搜运营策略分析
```sql
-- 最佳发布时机分析
SELECT
    HOUR(trend_date) as hour,
    COUNT(*) as topics_count,
    AVG(hot_value) as avg_hot_value,
    ROUND(AVG(hot_value), 0) as recommended_threshold
FROM weibo_trends
GROUP BY 1
ORDER BY avg_hot_value DESC;

-- 话题持续性评估
WITH topic_sustainability AS (
    SELECT
        topic_name,
        COUNT(DISTINCT trend_date) as duration_days,
        AVG(hot_value) as avg_hot_value,
        STDDEV(hot_value) as hot_value_volatility,
        MAX(hot_value) - MIN(hot_value) as hot_value_range
    FROM weibo_trends
    GROUP BY topic_name
)
SELECT
    CASE
        WHEN duration_days = 1 THEN '一日热搜'
        WHEN duration_days <= 3 THEN '短期热搜'
        WHEN duration_days <= 7 THEN '中期热搜'
        ELSE '长期热搜'
    END as sustainability_type,
    COUNT(*) as topic_count,
    AVG(avg_hot_value) as avg_hot_value,
    AVG(hot_value_volatility) as avg_volatility
FROM topic_sustainability
GROUP BY 1
ORDER BY AVG(avg_hot_value) DESC;
```

## 7. 数据可视化建议

基于以上分析，建议创建以下可视化图表：

1. **时间序列图**：展示每日热搜数量和平均热度变化
2. **热力图**：显示一周七天和24小时的热搜活跃度
3. **词云图**：展示高频出现的话题关键词
4. **散点图**：话题持续天数vs平均热度的关系
5. **柱状图**：不同类别话题的热度分布
6. **网络图**：话题共现关系网络

这个分析案例涵盖了从基础统计到高级分析的完整流程，可以为微博运营、内容策略、用户行为研究等提供数据支持。


# 微博热搜趋势数据分析案例（进阶篇）

## 8. 用户行为模式深度分析

### 8.1 热搜传播速度分析
```sql
-- 话题传播速度建模（基于热度增长率）
WITH propagation_speed AS (
    SELECT
        topic_name,
        trend_date,
        hot_value,
        ROW_NUMBER() OVER (PARTITION BY topic_name ORDER BY trend_date) as day_rank,
        FIRST_VALUE(hot_value) OVER (PARTITION BY topic_name ORDER BY trend_date) as initial_hot_value,
        hot_value - FIRST_VALUE(hot_value) OVER (PARTITION BY topic_name ORDER BY trend_date) as hot_value_growth,
        DATEDIFF('hour', FIRST_VALUE(trend_date) OVER (PARTITION BY topic_name ORDER BY trend_date), trend_date) as hours_since_start
    FROM weibo_trends
),
speed_classification AS (
    SELECT
        topic_name,
        MAX(hot_value_growth) as max_growth,
        MIN(hours_since_start) as min_hours,
        CASE
            WHEN MIN(hours_since_start) = 0 THEN MAX(hot_value_growth)
            ELSE MAX(hot_value_growth) / NULLIF(MIN(hours_since_start), 0)
        END as propagation_velocity
    FROM propagation_speed
    WHERE hours_since_start > 0
    GROUP BY topic_name
)
SELECT
    CASE
        WHEN propagation_velocity > 10000 THEN '病毒式传播'
        WHEN propagation_velocity > 5000 THEN '快速传播'
        WHEN propagation_velocity > 1000 THEN '中速传播'
        ELSE '慢速传播'
    END as propagation_type,
    COUNT(*) as topic_count,
    AVG(propagation_velocity) as avg_velocity,
    AVG(max_growth) as avg_max_growth
FROM speed_classification
WHERE propagation_velocity IS NOT NULL
GROUP BY 1
ORDER BY avg_velocity DESC;
```

### 8.2 用户参与度峰值分析
```sql
-- 识别用户参与度的黄金时段
WITH hourly_engagement AS (
    SELECT
        EXTRACT(hour FROM trend_date) as hour,
        EXTRACT(dow FROM trend_date) as day_of_week,
        topic_name,
        hot_value,
        AVG(hot_value) OVER (PARTITION BY EXTRACT(hour FROM trend_date)) as hourly_avg
    FROM weibo_trends
),
engagement_patterns AS (
    SELECT
        hour,
        day_of_week,
        COUNT(*) as topic_count,
        AVG(hot_value) as avg_engagement,
        MAX(hot_value) as peak_engagement,
        STDDEV(hot_value) as engagement_volatility
    FROM hourly_engagement
    GROUP BY hour, day_of_week
)
SELECT
    hour,
    CASE day_of_week
        WHEN 0 THEN '周日'
        WHEN 1 THEN '周一'
        WHEN 2 THEN '周二'
        WHEN 3 THEN '周三'
        WHEN 4 THEN '周四'
        WHEN 5 THEN '周五'
        WHEN 6 THEN '周六'
    END as weekday,
    ROUND(avg_engagement, 0) as avg_engagement,
    ROUND(peak_engagement, 0) as peak_engagement,
    ROUND(engagement_volatility, 0) as volatility,
    ROUND(avg_engagement / AVG(avg_engagement) OVER(), 2) as engagement_index
FROM engagement_patterns
ORDER BY day_of_week, hour;
```

## 9. 内容质量与影响力分析

### 9.1 话题影响力评分模型
```sql
-- 构建综合影响力评分
WITH topic_metrics AS (
    SELECT
        topic_name,
        COUNT(DISTINCT trend_date) as persistence_days,
        MAX(hot_value) as peak_hot_value,
        AVG(hot_value) as avg_hot_value,
        SUM(hot_value) as total_hot_value,
        STDDEV(hot_value) as hot_value_stability,
        COUNT(*) as total_appearances
    FROM weibo_trends
    GROUP BY topic_name
),
influence_score AS (
    SELECT
        topic_name,
        persistence_days,
        peak_hot_value,
        avg_hot_value,
        total_hot_value,
        hot_value_stability,
        -- 影响力评分计算（权重分配）
        (
            COALESCE(LOG(peak_hot_value), 0) * 0.3 +  -- 峰值热度权重30%
            COALESCE(LOG(total_hot_value), 0) * 0.25 + -- 总热度权重25%
            persistence_days * 0.2 +                   -- 持续性权重20%
            COALESCE(LOG(avg_hot_value), 0) * 0.15 +   -- 平均热度权重15%
            (CASE WHEN hot_value_stability > 0 THEN 1/hot_value_stability ELSE 0 END) * 0.1 -- 稳定性权重10%
        ) as influence_score
    FROM topic_metrics
)
SELECT
    topic_name,
    ROUND(influence_score, 2) as influence_score,
    persistence_days,
    peak_hot_value,
    ROUND(avg_hot_value, 0) as avg_hot_value,
    CASE
        WHEN influence_score >= 15 THEN 'S级影响力'
        WHEN influence_score >= 12 THEN 'A级影响力'
        WHEN influence_score >= 9 THEN 'B级影响力'
        WHEN influence_score >= 6 THEN 'C级影响力'
        ELSE 'D级影响力'
    END as influence_level
FROM influence_score
ORDER BY influence_score DESC
LIMIT 30;
```

### 9.2 话题内容质量分析
```sql
-- 基于多维度的内容质量评估
WITH content_quality AS (
    SELECT
        topic_name,
        LENGTH(topic_name) as title_length,
        -- 标题复杂度（基于字符多样性）
        LENGTH(topic_name) - LENGTH(REPLACE(REPLACE(REPLACE(topic_name, ' ', ''), '#', ''), '@', '')) as complexity_score,
        -- 是否包含特殊符号
        CASE WHEN topic_name LIKE '%#%' OR topic_name LIKE '%@%' THEN 1 ELSE 0 END as has_special_chars,
        -- 是否包含数字
        CASE WHEN topic_name ~ '[0-9]' THEN 1 ELSE 0 END as has_numbers,
        MAX(hot_value) as max_hot_value,
        AVG(hot_value) as avg_hot_value,
        COUNT(DISTINCT trend_date) as trend_duration
    FROM weibo_trends
    GROUP BY topic_name
),
quality_analysis AS (
    SELECT
        CASE
            WHEN title_length <= 10 THEN '简短标题'
            WHEN title_length <= 20 THEN '中等标题'
            WHEN title_length <= 30 THEN '较长标题'
            ELSE '超长标题'
        END as title_length_category,
        COUNT(*) as topic_count,
        AVG(max_hot_value) as avg_peak_hot_value,
        AVG(trend_duration) as avg_duration,
        AVG(complexity_score) as avg_complexity,
        SUM(has_special_chars) * 100.0 / COUNT(*) as special_chars_ratio,
        SUM(has_numbers) * 100.0 / COUNT(*) as numbers_ratio
    FROM content_quality
    GROUP BY 1
)
SELECT
    title_length_category,
    topic_count,
    ROUND(avg_peak_hot_value, 0) as avg_peak_hot_value,
    ROUND(avg_duration, 1) as avg_duration_days,
    ROUND(avg_complexity, 1) as avg_complexity,
    ROUND(special_chars_ratio, 1) as special_chars_pct,
    ROUND(numbers_ratio, 1) as numbers_pct
FROM quality_analysis
ORDER BY avg_peak_hot_value DESC;
```

## 10. 竞争分析与市场洞察

### 10.1 话题竞争强度分析
```sql
-- 同日话题竞争分析
WITH daily_competition AS (
    SELECT
        trend_date,
        COUNT(*) as competing_topics,
        MAX(hot_value) as daily_max_hot_value,
        AVG(hot_value) as daily_avg_hot_value,
        STDDEV(hot_value) as daily_hot_value_std,
        -- 计算基尼系数衡量热度分布不均匀程度
        SUM(hot_value) as total_daily_hot_value
    FROM weibo_trends
    GROUP BY trend_date
),
competition_intensity AS (
    SELECT
        trend_date,
        competing_topics,
        daily_max_hot_value,
        daily_avg_hot_value,
        daily_hot_value_std,
        CASE
            WHEN daily_hot_value_std / NULLIF(daily_avg_hot_value, 0) > 2 THEN '高竞争'
            WHEN daily_hot_value_std / NULLIF(daily_avg_hot_value, 0) > 1 THEN '中竞争'
            ELSE '低竞争'
        END as competition_level
    FROM daily_competition
)
SELECT
    competition_level,
    COUNT(*) as days_count,
    AVG(competing_topics) as avg_competing_topics,
    AVG(daily_max_hot_value) as avg_daily_peak,
    AVG(daily_avg_hot_value) as avg_daily_mean,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
FROM competition_intensity
GROUP BY competition_level
ORDER BY avg_daily_peak DESC;
```

### 10.2 话题生态位分析
```sql
-- 识别不同类型话题的生态位
WITH topic_ecosystem AS (
    SELECT
        topic_name,
        AVG(hot_value) as avg_hot_value,
        MAX(hot_value) as peak_hot_value,
        COUNT(DISTINCT trend_date) as duration,
        STDDEV(hot_value) as volatility,
        -- 话题类型推断
        CASE
            WHEN topic_name LIKE '%明星%' OR topic_name LIKE '%娱乐%' OR topic_name LIKE '%电影%' OR topic_name LIKE '%综艺%' THEN '娱乐'
            WHEN topic_name LIKE '%新闻%' OR topic_name LIKE '%社会%' OR topic_name LIKE '%政策%' THEN '新闻'
            WHEN topic_name LIKE '%体育%' OR topic_name LIKE '%比赛%' OR topic_name LIKE '%奥运%' OR topic_name LIKE '%足球%' THEN '体育'
            WHEN topic_name LIKE '%科技%' OR topic_name LIKE '%AI%' OR topic_name LIKE '%互联网%' THEN '科技'
            WHEN topic_name LIKE '%经济%' OR topic_name LIKE '%股市%' OR topic_name LIKE '%金融%' THEN '财经'
            ELSE '其他'
        END as topic_category
    FROM weibo_trends
    GROUP BY topic_name
),
ecosystem_analysis AS (
    SELECT
        topic_category,
        COUNT(*) as topic_count,
        AVG(avg_hot_value) as category_avg_hot_value,
        AVG(peak_hot_value) as category_peak_hot_value,
        AVG(duration) as category_avg_duration,
        AVG(volatility) as category_avg_volatility,
        -- 计算市场份额
        SUM(peak_hot_value) as category_total_peak_value
    FROM topic_ecosystem
    GROUP BY topic_category
)
SELECT
    topic_category,
    topic_count,
    ROUND(category_avg_hot_value, 0) as avg_hot_value,
    ROUND(category_peak_hot_value, 0) as peak_hot_value,
    ROUND(category_avg_duration, 1) as avg_duration,
    ROUND(category_avg_volatility, 0) as avg_volatility,
    ROUND(category_total_peak_value * 100.0 / SUM(category_total_peak_value) OVER(), 2) as market_share_pct,
    -- 生态位特征
    CASE
        WHEN category_avg_duration > 3 AND category_avg_volatility < 50000 THEN '稳定型'
        WHEN category_peak_hot_value > 500000 THEN '爆发型'
        WHEN category_avg_duration <= 1 THEN '快消型'
        ELSE '平衡型'
    END as ecosystem_type
FROM ecosystem_analysis
ORDER BY category_total_peak_value DESC;
```

## 11. 预测模型与趋势预警

### 11.1 热搜趋势预测特征构建
```sql
-- 构建时间序列预测特征
WITH time_series_features AS (
    SELECT
        trend_date,
        topic_name,
        hot_value,
        -- 滞后特征
        LAG(hot_value, 1) OVER (PARTITION BY topic_name ORDER BY trend_date) as lag_1,
        LAG(hot_value, 2) OVER (PARTITION BY topic_name ORDER BY trend_date) as lag_2,
        LAG(hot_value, 3) OVER (PARTITION BY topic_name ORDER BY trend_date) as lag_3,
        -- 移动平均特征
        AVG(hot_value) OVER (PARTITION BY topic_name ORDER BY trend_date ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) as ma_3,
        AVG(hot_value) OVER (PARTITION BY topic_name ORDER BY trend_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) as ma_7,
        -- 趋势特征
        hot_value - LAG(hot_value, 1) OVER (PARTITION BY topic_name ORDER BY trend_date) as daily_change,
        (hot_value - LAG(hot_value, 1) OVER (PARTITION BY topic_name ORDER BY trend_date)) / NULLIF(LAG(hot_value, 1) OVER (PARTITION BY topic_name ORDER BY trend_date), 0) as daily_change_rate,
        -- 周期性特征
        EXTRACT(dow FROM trend_date) as day_of_week,
        EXTRACT(day FROM trend_date) as day_of_month,
        EXTRACT(month FROM trend_date) as month,
        -- 外部特征
        COUNT(*) OVER (PARTITION BY trend_date) as daily_competition_count
    FROM weibo_trends
),
prediction_dataset AS (
    SELECT
        *,
        -- 目标变量（预测下一天的热度）
        LEAD(hot_value, 1) OVER (PARTITION BY topic_name ORDER BY trend_date) as next_day_hot_value,
        -- 分类目标（预测趋势方向）
        CASE
            WHEN LEAD(hot_value, 1) OVER (PARTITION BY topic_name ORDER BY trend_date) > hot_value THEN 'UP'
            WHEN LEAD(hot_value, 1) OVER (PARTITION BY topic_name ORDER BY trend_date) < hot_value THEN 'DOWN'
            ELSE 'STABLE'
        END as trend_direction
    FROM time_series_features
)
SELECT
    trend_date,
    topic_name,
    hot_value,
    lag_1, lag_2, lag_3,
    ROUND(ma_3, 0) as ma_3,
    ROUND(ma_7, 0) as ma_7,
    daily_change,
    ROUND(daily_change_rate * 100, 2) as daily_change_rate_pct,
    day_of_week,
    daily_competition_count,
    next_day_hot_value,
    trend_direction
FROM prediction_dataset
WHERE lag_3 IS NOT NULL AND next_day_hot_value IS NOT NULL
ORDER BY trend_date, hot_value DESC;
```

### 11.2 异常热搜预警系统
```sql
-- 构建多层次预警系统
WITH baseline_metrics AS (
    SELECT
        topic_name,
        AVG(hot_value) as historical_avg,
        STDDEV(hot_value) as historical_std,
        MAX(hot_value) as historical_max,
        COUNT(*) as historical_count
    FROM weibo_trends
    WHERE trend_date <= CURRENT_DATE - INTERVAL '7 days'  -- 使用历史数据作为基线
    GROUP BY topic_name
),
current_metrics AS (
    SELECT
        topic_name,
        trend_date,
        hot_value,
        COUNT(*) OVER (PARTITION BY trend_date) as daily_topic_count
    FROM weibo_trends
    WHERE trend_date > CURRENT_DATE - INTERVAL '7 days'  -- 最近7天数据
),
alert_system AS (
    SELECT
        c.topic_name,
        c.trend_date,
        c.hot_value,
        c.daily_topic_count,
        b.historical_avg,
        b.historical_std,
        b.historical_max,
        -- 计算异常分数
        CASE
            WHEN b.historical_std > 0 THEN (c.hot_value - b.historical_avg) / b.historical_std
            ELSE 0
        END as z_score,
        c.hot_value / NULLIF(b.historical_max, 0) as max_ratio,
        -- 预警级别
        CASE
            WHEN c.hot_value > b.historical_max * 2 THEN '红色预警'
            WHEN c.hot_value > b.historical_max * 1.5 THEN '橙色预警'
            WHEN (c.hot_value - b.historical_avg) / NULLIF(b.historical_std, 0) > 3 THEN '黄色预警'
            WHEN (c.hot_value - b.historical_avg) / NULLIF(b.historical_std, 0) > 2 THEN '蓝色预警'
            ELSE '正常'
        END as alert_level
    FROM current_metrics c
    LEFT JOIN baseline_metrics b ON c.topic_name = b.topic_name
)
SELECT
    trend_date,
    topic_name,
    hot_value,
    ROUND(historical_avg, 0) as historical_avg,
    ROUND(z_score, 2) as z_score,
    ROUND(max_ratio, 2) as max_ratio,
    alert_level,
    daily_topic_count
FROM alert_system
WHERE alert_level != '正常'
ORDER BY
    CASE alert_level
        WHEN '红色预警' THEN 1
        WHEN '橙色预警' THEN 2
        WHEN '黄色预警' THEN 3
        WHEN '蓝色预警' THEN 4
    END,
    hot_value DESC;
```

## 12. 社交网络分析

### 12.1 话题传播网络构建
```sql
-- 构建话题共现网络
WITH topic_pairs AS (
    SELECT
        t1.topic_name as source_topic,
        t2.topic_name as target_topic,
        t1.trend_date,
        t1.hot_value as source_hot_value,
        t2.hot_value as target_hot_value,
        ABS(t1.hot_value - t2.hot_value) as hot_value_diff
    FROM weibo_trends t1
    JOIN weibo_trends t2 ON t1.trend_date = t2.trend_date
        AND t1.topic_name != t2.topic_name
        AND t1.topic_name < t2.topic_name  -- 避免重复配对
),
network_edges AS (
    SELECT
        source_topic,
        target_topic,
        COUNT(*) as co_occurrence_count,
        AVG(hot_value_diff) as avg_hot_value_diff,
        MIN(hot_value_diff) as min_hot_value_diff,
        -- 计算连接强度
        COUNT(*) * EXP(-AVG(hot_value_diff) / 100000.0) as connection_strength
    FROM topic_pairs
    GROUP BY source_topic, target_topic
    HAVING COUNT(*) >= 2  -- 至少共现2次
),
network_nodes AS (
    SELECT
        topic_name,
        COUNT(DISTINCT trend_date) as node_frequency,
        AVG(hot_value) as node_avg_hot_value,
        MAX(hot_value) as node_max_hot_value
    FROM weibo_trends
    GROUP BY topic_name
)
SELECT
    e.source_topic,
    e.target_topic,
    e.co_occurrence_count,
    ROUND(e.connection_strength, 3) as connection_strength,
    n1.node_frequency as source_frequency,
    n2.node_frequency as target_frequency,
    ROUND(n1.node_avg_hot_value, 0) as source_avg_hot_value,
    ROUND(n2.node_avg_hot_value, 0) as target_avg_hot_value
FROM network_edges e
JOIN network_nodes n1 ON e.source_topic = n1.topic_name
JOIN network_nodes n2 ON e.target_topic = n2.topic_name
ORDER BY connection_strength DESC
LIMIT 50;
```

### 12.2 影响力传播路径分析
```sql
-- 分析话题影响力传播路径
WITH topic_timeline AS (
    SELECT
        topic_name,
        trend_date,
        hot_value,
        ROW_NUMBER() OVER (PARTITION BY topic_name ORDER BY trend_date) as day_sequence,
        FIRST_VALUE(trend_date) OVER (PARTITION BY topic_name ORDER BY trend_date) as first_appearance
    FROM weibo_trends
),
influence_cascade AS (
    SELECT
        t1.topic_name as influencer_topic,
        t2.topic_name as influenced_topic,
        t1.trend_date as influencer_date,
        t2.trend_date as influenced_date,
        t1.hot_value as influencer_hot_value,
        t2.hot_value as influenced_hot_value,
        DATEDIFF('day', t1.trend_date, t2.trend_date) as time_lag
    FROM topic_timeline t1
    JOIN topic_timeline t2 ON t1.day_sequence = 1  -- 影响者首次出现
        AND t2.day_sequence = 1  -- 被影响者首次出现
        AND t1.trend_date < t2.trend_date  -- 时间先后顺序
        AND DATEDIFF('day', t1.trend_date, t2.trend_date) <= 3  -- 3天内的影响
        AND t1.topic_name != t2.topic_name
),
cascade_analysis AS (
    SELECT
        influencer_topic,
        COUNT(*) as influenced_count,
        AVG(time_lag) as avg_influence_lag,
        AVG(influenced_hot_value) as avg_influenced_hot_value,
        SUM(influenced_hot_value) as total_influenced_hot_value
    FROM influence_cascade
    GROUP BY influencer_topic
    HAVING COUNT(*) >= 2  -- 至少影响2个话题
)
SELECT
    influencer_topic,
    influenced_count,
    ROUND(avg_influence_lag, 1) as avg_influence_lag_days,
    ROUND(avg_influenced_hot_value, 0) as avg_influenced_hot_value,
    total_influenced_hot_value,
    -- 影响力评级
    CASE
        WHEN influenced_count >= 5 AND total_influenced_hot_value > 1000000 THEN '超级影响者'
        WHEN influenced_count >= 3 AND total_influenced_hot_value > 500000 THEN '强影响者'
        WHEN influenced_count >= 2 THEN '一般影响者'
        ELSE '弱影响者'
    END as influence_level
FROM cascade_analysis
ORDER BY total_influenced_hot_value DESC;
```

## 13. 高级业务应用场景

### 13.1 内容推荐算法优化
```sql
-- 基于用户兴趣的话题推荐评分
WITH user_interest_simulation AS (
    -- 模拟用户兴趣偏好（实际应用中应来自用户行为数据）
    SELECT
        '娱乐' as interest_category, 0.4 as interest_weight
    UNION ALL SELECT '新闻', 0.3
    UNION ALL SELECT '体育', 0.2
    UNION ALL SELECT '科技', 0.1
),
topic_features AS (
    SELECT
        topic_name,
        CASE
            WHEN topic_name LIKE '%明星%' OR topic_name LIKE '%娱乐%' THEN '娱乐'
            WHEN topic_name LIKE '%新闻%' OR topic_name LIKE '%社会%' THEN '新闻'
            WHEN topic_name LIKE '%体育%' OR topic_name LIKE '%比赛%' THEN '体育'
            WHEN topic_name LIKE '%科技%' OR topic_name LIKE '%AI%' THEN '科技'
            ELSE '其他'
        END as topic_category,
        AVG(hot_value) as avg_hot_value,
        MAX(hot_value) as peak_hot_value,
        COUNT(DISTINCT trend_date) as persistence,
        MAX(trend_date) as latest_date,
        -- 新鲜度评分
        CASE
            WHEN MAX(trend_date) >= CURRENT_DATE - INTERVAL '1 day' THEN 1.0
            WHEN MAX(trend_date) >= CURRENT_DATE - INTERVAL '3 days' THEN 0.8
            WHEN MAX(trend_date) >= CURRENT_DATE - INTERVAL '7 days' THEN 0.5
            ELSE 0.2
        END as freshness_score
    FROM weibo_trends
    GROUP BY topic_name
),
recommendation_scores AS (
    SELECT
        tf.topic_name,
        tf.topic_category,
        tf.avg_hot_value,
        tf.peak_hot_value,
        tf.persistence,
        tf.freshness_score,
        COALESCE(ui.interest_weight, 0.05) as user_interest_weight,
        -- 综合推荐评分
        (
            LOG(tf.peak_hot_value + 1) * 0.3 +  -- 热度权重
            tf.persistence * 0.2 +               -- 持续性权重
            tf.freshness_score * 0.3 +           -- 新鲜度权重
            COALESCE(ui.interest_weight, 0.05) * 100 * 0.2  -- 用户兴趣权重
        ) as recommendation_score
    FROM topic_features tf
    LEFT JOIN user_interest_simulation ui ON tf.topic_category = ui.interest_category
)
SELECT
    topic_name,
    topic_category,
    ROUND(recommendation_score, 2) as recommendation_score,
    ROUND(avg_hot_value, 0) as avg_hot_value,
    persistence as persistence_days,
    ROUND(freshness_score, 2) as freshness_score,
    ROUND(user_interest_weight, 2) as user_interest_weight
FROM recommendation_scores
ORDER BY recommendation_score DESC
LIMIT 20;
```

### 13.2 广告投放策略优化
```sql
-- 广告投放时机和话题选择优化
WITH ad_opportunity_analysis AS (
    SELECT
        topic_name,
        trend_date,
        hot_value,
        LAG(hot_value) OVER (PARTITION BY topic_name ORDER BY trend_date) as prev_hot_value,
        LEAD(hot_value) OVER (PARTITION BY topic_name ORDER BY trend_date) as next_hot_value,
        -- 计算话题生命周期阶段
        ROW_NUMBER() OVER (PARTITION BY topic_name ORDER BY trend_date) as day_in_lifecycle,
        COUNT(*) OVER (PARTITION BY topic_name) as total_lifecycle_days,
        -- 计算增长趋势
        CASE
            WHEN LAG(hot_value) OVER (PARTITION BY topic_name ORDER BY trend_date) IS NULL THEN 'Initial'
            WHEN hot_value > LAG(hot_value) OVER (PARTITION BY topic_name ORDER BY trend_date) * 1.2 THEN 'Rapid Growth'
            WHEN hot_value > LAG(hot_value) OVER (PARTITION BY topic_name ORDER BY trend_date) THEN 'Growth'
            WHEN hot_value < LAG(hot_value) OVER (PARTITION BY topic_name ORDER BY trend_date) * 0.8 THEN 'Decline'
            ELSE 'Stable'
        END as growth_stage
    FROM weibo_trends
),
ad_timing_optimization AS (
    SELECT
        topic_name,
        trend_date,
        hot_value,
        growth_stage,
        day_in_lifecycle,
        total_lifecycle_days,
        ROUND(day_in_lifecycle * 100.0 / total_lifecycle_days, 1) as lifecycle_percentage,
        -- 广告投放建议
        CASE
            WHEN growth_stage = 'Rapid Growth' AND day_in_lifecycle <= 2 THEN '最佳投放时机'
            WHEN growth_stage = 'Growth' AND lifecycle_percentage <= 30 THEN '良好投放时机'
            WHEN growth_stage = 'Stable' AND hot_value > 100000 THEN '稳定投放时机'
            WHEN growth_stage = 'Decline' THEN '避免投放'
            ELSE '观望'
        END as ad_recommendation,
        -- 预估投放成本效益
        CASE
            WHEN growth_stage = 'Rapid Growth' THEN hot_value * 0.8  -- 高性价比
            WHEN growth_stage = 'Growth' THEN hot_value * 1.0
            WHEN growth_stage = 'Stable' THEN hot_value * 1.2
            ELSE hot_value * 2.0  -- 低性价比
        END as estimated_cost_per_exposure
    FROM ad_opportunity_analysis
)
SELECT
    topic_name,
    trend_date,
    hot_value,
    growth_stage,
    lifecycle_percentage,
    ad_recommendation,
    ROUND(estimated_cost_per_exposure, 0) as estimated_cost_per_exposure
FROM ad_timing_optimization
WHERE ad_recommendation IN ('最佳投放时机', '良好投放时机', '稳定投放时机')
ORDER BY
    CASE ad_recommendation
        WHEN '最佳投放时机' THEN 1
        WHEN '良好投放时机' THEN 2
        WHEN '稳定投放时机' THEN 3
    END,
    hot_value DESC;
```

这些进阶分析案例涵盖了：
- 用户行为深度建模
- 内容质量评估体系
- 竞争分析框架
- 预测模型构建
- 社交网络分析
- 业务应用场景

每个分析都可以为实际的产品运营、内容策略、广告投放等业务决策提供数据支持。
