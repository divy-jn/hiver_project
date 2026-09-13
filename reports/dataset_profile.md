# Dataset Profile: Customer Support on Twitter

**Rows**: 2,811,774
**Columns**: 7
**Duplicate rows**: 0

## Columns

| Column | Dtype | Missing |
|--------|-------|---------|
| tweet_id | str | 0 |
| author_id | str | 0 |
| inbound | bool | 0 |
| created_at | str | 0 |
| text | str | 0 |
| response_tweet_id | str | 1,040,629 |
| in_response_to_tweet_id | str | 794,335 |

## Message Distribution

- **Initiating tweets** (no `in_response_to`): 794,335
- **Response tweets**: 2,017,439
- **Unique authors**: 702,777
- **Unique reply targets**: 1,774,822

## Timestamps

- **Min**: 2008-05-08 20:13:59+00:00
- **Max**: 2017-12-03 23:14:01+00:00

## Text Length

- Mean: 113.9, Median: 115.0
- Range: [1, 513]
- IQR: [78.0, 139.0]

## Thread Structure

- **Thread roots found in dataset**: 1,771,145

## Top Brand Candidates

| Author ID | Total Tweets | Responses | Response Ratio |
|-----------|-------------|-----------|----------------|
| AmazonHelp | 169,840 | 169,287 | 99.7% |
| AppleSupport | 106,860 | 106,719 | 99.9% |
| Uber_Support | 56,270 | 56,261 | 100.0% |
| SpotifyCares | 43,265 | 43,243 | 99.9% |
| Delta | 42,253 | 42,197 | 99.9% |
| Tesco | 38,573 | 38,501 | 99.8% |
| AmericanAir | 36,764 | 36,598 | 99.5% |
| TMobileHelp | 34,317 | 34,287 | 99.9% |
| comcastcares | 33,031 | 33,007 | 99.9% |
| British_Airways | 29,361 | 29,315 | 99.8% |
| SouthwestAir | 28,977 | 28,889 | 99.7% |
| VirginTrains | 27,817 | 27,522 | 98.9% |
| Ask_Spectrum | 25,860 | 25,807 | 99.8% |
| XboxSupport | 24,557 | 24,341 | 99.1% |
| sprintcare | 22,381 | 22,335 | 99.8% |
| hulu_support | 21,872 | 21,783 | 99.6% |
| sainsburys | 19,466 | 19,417 | 99.7% |
| GWRHelp | 19,364 | 19,294 | 99.6% |
| AskPlayStation | 19,098 | 18,694 | 97.9% |
| ChipotleTweets | 18,749 | 18,612 | 99.3% |
