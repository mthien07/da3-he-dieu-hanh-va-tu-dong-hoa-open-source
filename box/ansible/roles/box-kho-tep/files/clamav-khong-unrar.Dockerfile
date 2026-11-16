# Image kiểm dịch cục bộ của OneBee Box: ClamAV chính chủ đã ghim digest, bỏ libclamunrar (giấy phép UnRAR, ngoài OSI).
# Dồn về một lớp (FROM scratch) để thư viện đã xóa không còn nằm trong lớp gốc. Thêm python3 để dịch vụ cổng tệp
# (mã trong repo, MIT) chạy chung image với clamscan — quét từng lượt, không có clamd thường trú (ADR 0006, QĐ5).
# Sửa tệp này là bộ cài dựng lại image; image đã có và tệp không đổi thì bộ cài không dựng lại.
FROM docker.io/clamav/clamav:1.5.4-debian13-slim@sha256:76a9c3b63764b78178dc68fa7efcceca0cde2c8c9d4f925a8e697cb4511f8fdc AS goc
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 \
 && rm -rf /var/lib/apt/lists/* \
 && rm -f /usr/lib/libclamunrar.so* /usr/lib/libclamunrar_iface.so*

FROM scratch
COPY --from=goc / /
ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC
EXPOSE 3310/tcp 7357/tcp
HEALTHCHECK --start-period=6m CMD clamdcheck.sh
ENTRYPOINT ["/init"]
