import uvicorn
import os

os.environ["ROME_PROXY_API_KEY"] = "2556c1b210a01dfbd13890f570008950"
if __name__ == "__main__":
    uvicorn.run(
        "RomeProxy:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )