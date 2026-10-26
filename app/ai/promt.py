
from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate

PROMPTS_DIR = Path(__file__).parent / "prompts"

SYSTEM_PROMPT_FILE = PROMPTS_DIR / "reply_system.md"
HUMAN_PROMPT_FILE = PROMPTS_DIR / "reply_human.md"

REPLY_SYSTEM_PROMPT = SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")
REPLY_HUMAN_PROMPT = HUMAN_PROMPT_FILE.read_text(encoding="utf-8")

reply_prompt = ChatPromptTemplate.from_messages([
    ("system", REPLY_SYSTEM_PROMPT),
    ("human", REPLY_HUMAN_PROMPT),
])
