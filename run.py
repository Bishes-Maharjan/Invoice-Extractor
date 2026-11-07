import os
import uvicorn
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "True").lower() in ("true", "1", "t")

    print(f"\n Starting FastAPI server at http://{host}:{port}")
    print(f" Interactive Swagger API docs available at http://{host}:{port}/docs\n")
    uvicorn.run("app.main:app", host=host, port=port, reload=reload)

