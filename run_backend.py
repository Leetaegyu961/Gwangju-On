import uvicorn
import os
import sys

# 프로젝트 루트 경로를 sys.path에 추가하여 backend 패키지를 찾을 수 있게 함
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
