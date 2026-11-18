# ALPHA KNOWLEDGE

## GOLDEN RULES
- Always use group_neutralize(x, sector) or group_rank(x, sector)
- Decay 3 to 10, truncation 0.08, delay 1, pasteurization ON
- Target: Sharpe over 1.4, Fitness over 0.8, Turnover under 0.70

## HIGH SELF-CORRELATION - AVOID
- ts_corr, ts_cov, ts_mean(close)
- rank(close / ts_mean(close, 20))
- Any expression using only close and volume

## LOW SELF-CORRELATION - USE MORE
- Sentiment: sentiment, news_sentiment, analyst_rating, analyst_revision
- Fundamental: sales, roa, debt_to_equity, book_value, pe_ratio
- Volatility: ts_std_dev, ts_max_drawdown, ts_range
- Volume quality: vwap, volume / ts_mean(volume, 20)

## ROTATION ORDER
Sentiment -> Fundamental -> Volatility -> Volume -> Mean Reversion -> Momentum

## LESSONS LEARNED
- Analyst revisions work better with decay 5 than decay 20
- Sentiment needs sector neutralization or it becomes market beta
- Add your new lesson here after each batch