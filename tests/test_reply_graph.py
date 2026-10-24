from app.ai.graph import reply_graph

initial_state = {
    "user_id": 2,
    "channel_id": 2,
    "comment_id": 2,
    "comment_text": "",
    "video_id": "",
    "video_title": "",
    "video_context": "",
    "channel_tone": "Friendly, natural, and respectful",
    "request": None,
    "draft": None,
    "error": None,
    "needs_review": True,
}

result = reply_graph.invoke(initial_state)

print("Comment:", result.get("comment_text"))
print("Video ID:", result.get("video_id"))
print("Video title:", result.get("video_title"))
print("Draft:", result.get("draft"))
print("Needs review:", result.get("needs_review"))
print("Error:", result.get("error"))