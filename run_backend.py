import uvicorn
import os
import sys

# 프로젝트 루트 경로를 sys.path에 추가하여 backend 패키지를 찾을 수 있게 함
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
os.chdir(project_root)  # 작업 디렉토리를 프로젝트 루트로 설정

if __name__ == "__main__":
    print(f"🚀 Starting backend server from: {project_root}")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True, reload_dirs=[project_root])

