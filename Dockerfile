FROM python:3.12-slim
RUN useradd --create-home --uid 10001 lua && mkdir -p /app /data && chown -R lua:lua /app /data
WORKDIR /app
COPY --chown=lua:lua . /app
ENV LUA_DATA=/data HOST=0.0.0.0 PORT=8000 PYTHONUNBUFFERED=1
USER lua
VOLUME ["/data"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8000')+'/aluno',timeout=4)"
CMD ["python", "servidor.py"]
