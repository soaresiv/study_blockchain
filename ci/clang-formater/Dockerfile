FROM debian:unstable-20211011-slim
ADD clang-format-wrapper.py /clang-format-wrapper.py

RUN  \
apt-get update && \
apt-get install -y --no-install-recommends clang-format-13 && \
chmod +x /clang-format-wrapper.py

ENTRYPOINT ["/clang-format-wrapper.py"]

