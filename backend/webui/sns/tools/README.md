# SNS posting tools

These helpers are intentionally small and mascot-scoped. They return context for the agent loop; they do not generate text or decide likes/follows.

- `get_mascot_profile(broker)`: current mascot identity and personality.
- `get_own_tweet_history(broker)`: own posts only, bounded by 30 posts / 6,000 estimated tokens, with dates and like counts.
- `get_current_context()`: local date, time, timezone, and season.
- `get_social_context(broker)`: current following/follower state.
- `get_top_news(locale=...)`: regional Google Trends RSS selected from the browser/OS locale, with BBC/NPR used only when Trends is unavailable.

The browser sends its full BCP 47 locale (for example, `ja-JP` or `en-GB`). A region subtag selects that country's Google Trends feed; a language-only locale uses a language-specific default. Retrieved trends and related news are context for the mascot's own feelings, not text to copy or summarize.

Weather remains an optional provider. Use the existing `web_search` / `web_browse` tools for other external sources.
