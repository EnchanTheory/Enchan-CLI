# SNS posting tools

These helpers are intentionally small and mascot-scoped. They return context for the agent loop; they do not generate text or decide likes/follows.

- `get_mascot_profile(broker)`: current mascot identity and personality.
- `get_own_tweet_history(broker)`: own posts only, bounded by 30 posts / 6,000 estimated tokens, with dates and like counts.
- `get_current_context()`: local date, time, timezone, and season.
- `get_social_context(broker)`: current following/follower state.

News and weather remain optional providers. Use the existing `web_search` / `web_browse` tools for external sources, and convert retrieved material into the mascot's own feelings rather than copying headlines.
