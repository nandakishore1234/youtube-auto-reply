# Conversiq
Conversiq is a YouTube creator workspace. It connects a YouTube channel, drafts comment replies for review, and includes a Creator Chat assistant for ideas, scripts, SEO, thumbnails, images, and public channel statistics.
The backend is FastAPI. The frontend is React with Vite. Creator Chat runs locally through Ollama and LangGraph. Images are generated locally with FLUX.2 Klein.
## Features
- Account registration, login, and sessions
- YouTube channel connection through Google OAuth
- Comment fetching and AI reply drafts
- Review queue to approve or reject replies
- Optional auto-publish policy
- Creator Chat for:
  - video ideas
  - scripts
  - SEO titles, descriptions, keywords, and hashtags
  - thumbnail prompt writing
  - local thumbnail and image generation
  - public channel and latest-video statistics
- Channel-aware answers for the signed-in user and selected channel
Creator Chat can read public YouTube Data API statistics such as subscribers, views, uploads, likes, and comments. It does not read private YouTube Studio Analytics such as revenue, watch time, impressions, or click-through rate.
## Project structure
```text
app/
  api/                  HTTP routes
  ai/                   Comment-reply workflow
  ai/creator/           Creator Chat planner, graph, and prompts
  services/             YouTube, OAuth, replies, and image generation
  models/               Database models
frontend/               React application
alembic/                Database migrations
tests/                  Backend tests
```
## Requirements
- Python 3.13
- Node.js 20 or newer
- PostgreSQL
- [Ollama](https://ollama.com/) with the `qwen2` model
- A Google Cloud project with the YouTube Data API enabled
- For local images: stable-diffusion.cpp and the FLUX.2 Klein model files
Normal text generation uses the local `qwen2` model. Ollama places that model on the GPU when one is available. A GPU is not required for text, but a GPU is required for practical FLUX image generation.
## Backend setup
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-win.txt
```
On Linux or macOS, install `requirements.txt` instead of `requirements-win.txt`.
Create a `.env` file in the project root:
```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/youtube_ai_replier
SESSION_SECRET=replace-with-a-long-random-string
TOKEN_ENCRYPTION_KEY=replace-with-a-fernet-key
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://127.0.0.1:8000/api/v1/youtube/oauth/callback
IMAGE_GENERATION_EXECUTABLE=C:\AI\stable-diffusion.cpp\sd-cli.exe
IMAGE_GENERATION_MODEL=C:\AI\models\flux2-klein\flux-2-klein-4b-Q4_K_M.gguf
IMAGE_GENERATION_LLM=C:\AI\models\flux2-klein\Qwen3-4B-Q4_K_S.gguf
IMAGE_GENERATION_VAE=C:\AI\models\flux2-klein\flux2-vae.safetensors
IMAGE_GENERATION_OUTPUT_DIR=C:\AI\generated\creator-chat
```
Create the database and run migrations:
```powershell
alembic upgrade head
```
Pull the chat model and start the API:
```powershell
ollama pull qwen2
uvicorn app.main:app --reload
```
The API runs at `http://127.0.0.1:8000`.
## Frontend setup
```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```
The app runs at `http://127.0.0.1:5173`.
## Tests
Use a separate PostgreSQL database for tests:
```powershell
$env:TEST_DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/youtube_ai_replier_test"
pytest
```
## Creator Chat flow
1. The planner model chooses the required tool.
2. The graph runs only the approved tools, in order.
3. YouTube statistics come from the connected channel's OAuth client.
4. Images are generated locally with FLUX.2 Klein.
5. The final reply is based on the tool results and the selected account context.
A request such as "use my latest video to create SEO titles" can run YouTube retrieval and then SEO generation.
## Notes
- Do not commit `.env`, OAuth tokens, model files, or generated images.
- Reconnect a channel when its YouTube authorization expires.
- Select a connected channel before asking for channel statistics or the channel name.
- Check the environment variable names in `app/config.py` before publishing. They must match the settings used by the application.
