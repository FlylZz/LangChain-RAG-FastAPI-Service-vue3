"""
原 Streamlit 调试界面已废弃。

现在使用 FastAPI 提供 API 服务，启动方式:
    uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload

API 文档（启动后访问）:
    http://127.0.0.1:8001/docs        # Swagger UI
    http://127.0.0.1:8001/redoc       # ReDoc

如需本地调试 Agent，可使用:
    python -m agent.react_agent
"""

if __name__ == "__main__":
    print("请使用: uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload")
