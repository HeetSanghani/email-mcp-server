import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from auth.routes import router as auth_router
from chat.routes import router as chat_router
from dotenv import load_dotenv

load_dotenv(override=True)

app = FastAPI(
    title="Email MCP Server",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Allow all origins for local frontend testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(chat_router)


@app.get("/")
def root():
    return FileResponse("frontend/index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


# ── OAuth success redirect helper ────────────────────────────────────────────
# Your auth/routes.py callback should call this after saving the token,
# so the frontend receives ?connected=gmail (or outlook) and shows the toast.
#
# In auth/routes.py, at the end of your Gmail callback, replace any existing
# redirect with:
#
#   return RedirectResponse(url="/?connected=gmail")
#
# And for Outlook:
#
#   return RedirectResponse(url="/?connected=outlook")
#
# That's the only change needed in auth/routes.py — the frontend handles the
# rest (toast, modal close, status refresh, welcome message).
# ─────────────────────────────────────────────────────────────────────────────