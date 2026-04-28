FROM python:3.12-slim

WORKDIR /app

# git インストール（gitpython用）
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# uv インストール
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 依存パッケージインストール（キャッシュ効率のため先にコピー）
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# アプリケーションコード
COPY src/ src/
COPY pages/ pages/
COPY data/templates/ data/templates/
COPY app.py sync.py generate.py healthcheck.py repo_sync.py ./
COPY .streamlit/ .streamlit/

# データディレクトリ（ボリュームマウント対象）
RUN mkdir -p data/knowledge data/raw data/chroma data/repos output

EXPOSE 8502

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD uv run python healthcheck.py || exit 1

CMD ["uv", "run", "streamlit", "run", "app.py", "--server.address", "0.0.0.0", "--server.port", "8502"]
