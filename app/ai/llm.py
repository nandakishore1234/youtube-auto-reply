from langchain_ollama import ChatOllama

from app.ai.promt import reply_prompt
from app.ai.schema import ReplyDraftRequest, ReplyDraft

from langchain_core.output_parsers import PydanticOutputParser

llm = ChatOllama(model="qwen2",
    temperature=0.4,
    )

parser = PydanticOutputParser(pydantic_object=ReplyDraft)

prompt = reply_prompt.partial(
    format_instructions=parser.get_format_instructions(),
)


reply_chain = prompt | llm | parser


def generate_reply_draft(request: ReplyDraftRequest) -> ReplyDraft:
    result = reply_chain.invoke(
        request.model_dump()
    )

    # Enforce the application's review policy as well.
    if result.intent in {"spam", "criticism"}:
        result.needs_human_review = True

    return result