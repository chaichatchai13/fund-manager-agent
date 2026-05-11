from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.events import on_shutdown, on_startup


@asynccontextmanager
async def lifespan(app: FastAPI):
    await on_startup()
    yield
    await on_shutdown()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Fund Manager Agent",
        description="Automated sell-puts trading system with AI agent interface",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from app.api.routes import agent, rules, positions, orders, performance, websocket, account
    app.include_router(agent.router)
    app.include_router(rules.router)
    app.include_router(positions.router)
    app.include_router(orders.router)
    app.include_router(performance.router)
    app.include_router(account.router)
    app.include_router(websocket.router)

    # Serve React frontend build in production
    import os
    frontend_dist = os.path.join(os.path.dirname(__file__), "../../frontend/dist")
    if os.path.exists(frontend_dist):
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="static")

    return app
