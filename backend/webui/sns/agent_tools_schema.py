"""Tool schema exposed only to the SNS posting agent."""

SNS_AGENT_TOOLS_SCHEMA = [
    {"type": "function", "function": {"name": "sns_get_own_tweet_history", "description": "Read only this mascot's dated tweet history and like counts for self-review.", "parameters": {"type": "object", "properties": {"max_posts": {"type": "integer"}, "token_budget": {"type": "integer"}}, "required": []}}},
    {"type": "function", "function": {"name": "sns_get_current_context", "description": "Get local date, time, timezone, and season.", "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "sns_search_news", "description": "Search a current news topic as inspiration; do not copy headlines as a post.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
]

def get_sns_agent_tools_schema():
    return SNS_AGENT_TOOLS_SCHEMA.copy()
