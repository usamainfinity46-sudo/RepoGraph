FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b
ARG WHEEL=dist/repograph_mcp-0.2.0rc4-py3-none-any.whl
COPY ${WHEEL} /tmp/wheels/
RUN pip install --no-cache-dir /tmp/wheels/*.whl pytest==9.2.0
COPY scripts/security/probe.py /opt/probe.py
USER 65534:65534
WORKDIR /tmp
ENTRYPOINT ["python", "-I", "-B", "/opt/probe.py"]
