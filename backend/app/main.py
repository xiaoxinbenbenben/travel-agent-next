"""FastAPI 入口。当前仅保留最小骨架，后续逐步挂载业务路由。"""

from fastapi import FastAPI


app = FastAPI(title="Travel Agent Next API")


@app.get("/health")
def health() -> dict[str, str]:
    """基础健康检查接口。"""
    return {"status": "ok"}
