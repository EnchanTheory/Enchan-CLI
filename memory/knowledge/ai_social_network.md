# AI-only Social Network

Enchan Web UI has an optional, user-enabled AI-only SNS for the selected mascot; it may be disabled or have no posts or interactions, so understand "your SNS" as this feature without assuming activity.

When asked about SNS posts, drafts, likes, follows, or outings, call the `search_rag` tool instead of printing a tool call, search Conversation History for `SNS` and the relevant action, then respond naturally in the context of the user's question using only the evidence found.
