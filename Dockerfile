FROM python:3.13-slim

WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential && rm -rf /var/lib/apt/lists/*

# Poetry 설치
RUN pip install poetry

# 의존성 파일만 먼저 복사 (Docker 캐시 활용)
COPY pyproject.toml poetry.lock ./

# 가상환경 없이 시스템에 직접 설치
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --no-root

# 소스 코드 복사
COPY backend/ ./backend/
COPY src/ ./src/
COPY data/ ./data/
COPY vector_data/ ./vector_data/

# static 디렉토리 생성
RUN mkdir -p static/uploads

# Cloud Run은 PORT 환경변수를 주입 (기본 8080)
ENV PORT=8080
EXPOSE 8080

CMD exec uvicorn backend.main:app --host 0.0.0.0 --port $PORT
