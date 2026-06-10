# Role5-FakeSignal-v1

All Role 5 signal scores use the inclusive `0..100` range. Probability inputs use `0..1` and are clamped before calculation.

## Primary Risk Scores

```text
fake_comment = 100 * clamp(
  .20 generic + .20 duplicate + .15 emoji_only + .15 spam_keywords
  + .10 link_spam + .10 low_context + .10 aigc)

fake_follower = 100 * clamp(
  .25 profile_anomaly + .25 engagement_mismatch + .20 abnormal_ratio
  + .15 growth_anomaly + .15 low_activity_high_followers)

bot_behavior = 100 * clamp(
  .25 posting_uniformity + .20 comment_uniformity + .20 text_reuse
  + .15 engagement_burst + .10 night_activity + .10 activity_velocity)

coordinated = 100 * clamp(
  .30 repeated_commenters + .25 duplicate_text + .20 synchronized_activity
  + .15 shared_hashtags + .10 suspicious_account_overlap)

overall_fake = .30 fake_comment + .25 fake_follower + .25 bot_behavior + .20 coordinated
```

When an upstream fake-comment classifier supplies `model_fake_probability`, the final fake-comment score is `0.60 * model_probability * 100 + 0.40 * heuristic_score`.

## Derived Quality Scores

```text
engagement_quality = clamp(100 - overall_fake + authentic_bonus, 0, 100)
adjusted_sentiment = raw_sentiment * (1 - .50 * overall_fake / 100)
```

The authentic bonus is limited to 10 points and is based only on supplied diversity, relevance, stability, ratio, and source-diversity evidence.

Credibility starts at 50 and applies the published positive and negative rule values. Fewer than three sources cap credibility at 70 and produce Low confidence.

## Five-Layer Mapping

- Semantic: spam, toxicity, AIGC, claim mismatch, propaganda template, repeated talking points.
- Behavioral: fake follower, fake comment, bot behavior, timing, velocity, duplicates, night activity.
- Graph proxy: repeated commenters, duplicate text, suspicious overlap, shared hashtags, same source.
- Bot rings: coordinated risk, confirmed bot overlap, amplifier ratio, synchronization.
- Brand safety risk: `100 - brand_safety_score`.

Default fusion weights are Semantic `.20`, Behavioral `.30`, Graph `.20`, Bot Rings `.20`, Brand Safety `.10`. Missing layers are removed and available weights are divided by their remaining total. The risk JSON records effective weights, contribution, availability, renormalization, model version, and UTC computation time.

## Trust

```text
positive_trust = .20 relevance + .20 credibility + .15 engagement_quality
               + .15 sentiment + .15 brand_safety + .15 source_confidence
role5_trust = clamp(positive_trust - .50 overall_fake, 0, 100)
```

Caps:

- Overall fake risk above 80: trust at most 45.
- Any severe brand-safety flag: trust at most 40.
- Fewer than three sources: trust at most 70.

Grades are `A+ 90..100`, `A 80..89`, `B 70..79`, `C 60..69`, `D 40..59`, and `F 0..39`.

Every analyzer returns reasons plus measured feature evidence. Serious brand-safety flags include the matched keyword, category, severity, source URL, context, and review status. These flags are evidence for review, not legal, medical, political, or criminal conclusions.
