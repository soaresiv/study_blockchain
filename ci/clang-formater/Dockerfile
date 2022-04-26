FROM debian:unstable-20211011-slim
ADD entrypoint.sh /entrypoint.sh
ADD clang-format-wrapper.py /clang-format-wrapper.py

RUN  \
apt-get update && \
apt-get install -y --no-install-recommends clang-format-13 && \
chmod +x /clang-format-wrapper.py && \
chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
