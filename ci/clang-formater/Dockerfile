FROM debian:unstable-20211011-slim

RUN  apt-get update && \
apt-get install -y --no-install-recommends clang-format-13

ADD entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

