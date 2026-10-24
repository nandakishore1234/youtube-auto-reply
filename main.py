from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

llm =ChatOllama(
    model="qwen2",
    temperature=0.3
)

prompt = ChatPromptTemplate.from_messages([
        ("system","""
        You are a friendly YouTube channel assistant.
        Write concise, natural replies to comments.
        Do not invent video facts.
        If a question cannot be answered from the supplied
        context, ask for more information or say it is unknown.
        Return only the suggested reply.
        """,),
        ("human", """
        Video title: {video_title}
        Comment: {comment}
        """,),
    ])

chain =prompt | llm

response = chain.invoke({
    "video_title": "How to make a website",
    "comment": "This is a great video! I learned a lot."
})

print("suggested reply:", response.content)