# ADR 0006 — Lõi DX-OS open-core: SSO, cổng API, dữ liệu cấu trúc, kho tệp, kiểm dịch, động cơ quy trình

- Ngày: 15/11/2026 · Trạng thái: Đề xuất, chờ duyệt · Đo và thử trên máy ảo, **chưa thử trên Box thật**
- Liên quan: ADR 0005 (CA riêng ràng buộc tên, Caddy là dịch vụ duy nhất công bố cổng)

## Bối cảnh
Plan OLP 2026 biến OneBee Box thành DX-OS open-core: một tài khoản đăng nhập cho mọi dịch vụ, API dữ liệu có phân quyền tới từng dòng,
kho tệp có API và kiểm dịch, động cơ quy trình có bước người duyệt. Mọi thành phần phải có giấy phép OSI. Trước khi viết mã cần chốt
bằng số đo: thành phần nào, ghim bản nào, và bảy quyết định thiết kế mà giai đoạn SSO + cổng API và giai đoạn dữ liệu cấu trúc phụ thuộc vào.

Điều kiện đo và thử (14–15/11/2026):
- Máy ảo VMware `onebee-kiem-box`: Ubuntu 24.04, 4 vCPU, 10 GB RAM, Docker 29.1.3, Docker Compose 2.40.3. Thư mục thử `~/onebee-thu-loi/` (ngoài repo).
- Bản Box cài từ đợt kiểm trước (Ollama, Open WebUI, n8n, Uptime Kuma, rest-server, Caddy) **vẫn chạy** trong lúc đo, không bị dừng; số đo là theo từng container nên không lẫn.
- Mọi cổng thử chỉ công bố trên `127.0.0.1` của máy ảo (443, 9443, 13001). Thử "vào bằng IP" dùng `curl --connect-to 192.168.72.50:443:127.0.0.1:443`.
- CA thử sinh bằng đúng `box/ansible/roles/box-stack/files/onebee-ca.sh` (mã `thu`, IP `192.168.72.50`), Caddy dùng CA đó như Box (`tls internal`, gốc không kèm khóa).
- Tên `box.thu.onebee.internal` trỏ về `127.0.0.1` bằng một dòng `/etc/hosts` trên máy ảo (đã xóa sau khi thử).
- Mật khẩu, khóa, JWT, mã TOTP dùng khi thử chỉ nằm trong `.env` của thư mục thử; trong tài liệu này thay bằng `<mật khẩu thử>` hoặc `<che>`.

## Giấy phép (nhiệm vụ 1.1)
Mỗi dòng đọc từ tệp giấy phép trong kho mã chính thức **đúng tag** của phiên bản đã dựng thử; đối chiếu danh sách OSI tại https://opensource.org/licenses.

| Thành phần | Phiên bản đã thử | SPDX | Tệp giấy phép đúng tag | OSI |
|---|---|---|---|---|
| Authelia | 4.39.28 | Apache-2.0 | https://raw.githubusercontent.com/authelia/authelia/v4.39.28/LICENSE | Có |
| Caddy (đang dùng) | 2.11.4 | Apache-2.0 | https://raw.githubusercontent.com/caddyserver/caddy/v2.11.4/LICENSE | Có |
| PostgreSQL | 18.7 (trong image `pgvector/pgvector:0.8.7-pg18-trixie`) | PostgreSQL | https://raw.githubusercontent.com/postgres/postgres/REL_18_7/COPYRIGHT | Có |
| pgvector | 0.8.7 | PostgreSQL | https://raw.githubusercontent.com/pgvector/pgvector/v0.8.7/LICENSE | Có |
| PostgREST | 16.5 | MIT | https://raw.githubusercontent.com/PostgREST/postgrest/v16.5/LICENSE | Có |
| SeaweedFS | 4.53 | Apache-2.0 | https://raw.githubusercontent.com/seaweedfs/seaweedfs/4.53/LICENSE | Có |
| ClamAV | 1.5.4 | GPL-2.0-only (lõi; kèm thư viện LGPL-2.1, Apache-2.0, BSD-3-Clause, MIT, Zlib…; riêng `libclamunrar` dùng giấy phép UnRAR, không phải OSI — https://raw.githubusercontent.com/Cisco-Talos/clamav/clamav-1.5.4/COPYING/COPYING.unrar) | https://raw.githubusercontent.com/Cisco-Talos/clamav/clamav-1.5.4/COPYING.txt | Có (lõi); image chính chủ **có** `libclamunrar` → dùng bản đã bỏ (QĐ5) |
| cvdupdate (tải chữ ký ClamAV ở máy có Internet) | 1.2.0 | Apache-2.0 | https://raw.githubusercontent.com/Cisco-Talos/cvdupdate/cvdupdate-1.2.0/LICENSE | Có |
| Node-RED | 5.0.9 | Apache-2.0 | https://raw.githubusercontent.com/node-red/node-red/5.0.9/LICENSE | Có |
| node-red-node-email (nút gửi thư của Node-RED) | 5.2.5 | Apache-2.0 | https://raw.githubusercontent.com/node-red/node-red-nodes/master/LICENSE (gói npm 5.2.5 khai `Apache-2.0`; kho dùng chung không gắn tag theo gói) | Có |
| Flowable (ứng viên, bị loại ở QĐ6) | 8.0.0 | Apache-2.0 | https://raw.githubusercontent.com/flowable/flowable-engine/flowable-8.0.0/LICENSE | Có |
| Kestra (ứng viên, bị loại ở QĐ6) | 2.0.10 (+ plugin-email 1.6.8) | Apache-2.0 | https://raw.githubusercontent.com/kestra-io/kestra/v2.0.10/LICENSE | Có |
| Keycloak (phương án lùi của Authelia, không dựng thử) | 26.8.2 | Apache-2.0 | https://raw.githubusercontent.com/keycloak/keycloak/26.8.2/LICENSE.txt | Có |
| Python (image chính chủ, chạy cầu nối danh tính và dịch vụ tệp) | 3.14.10 (`python:3.14.10-slim-trixie`) | Python-2.0 (gồm PSF-2.0); gói Debian trong image giữ giấy phép riêng | https://raw.githubusercontent.com/python/cpython/v3.14.10/LICENSE | Có |
| Ollama (đang dùng) | 0.34.4 | MIT | https://raw.githubusercontent.com/ollama/ollama/v0.34.4/LICENSE | Có |
| Uptime Kuma (đang dùng) | 2.5.5 | MIT | https://raw.githubusercontent.com/louislam/uptime-kuma/2.5.5/LICENSE | Có |
| restic rest-server (đang dùng) | 0.14.0 | BSD-2-Clause | https://raw.githubusercontent.com/restic/rest-server/v0.14.0/LICENSE | Có |
| Mô hình Gemma 4 (`gemma4:e2b-it-qat`) | Gemma 4 | Apache-2.0 | https://ai.google.dev/gemma/apache_2 (trang https://ai.google.dev/gemma/terms ghi Gemma 4 dùng giấy phép này; Gemma Terms of Use chỉ áp cho các dòng ở Phụ lục) | Có |

Kiểm trên Box thử (model đúng tag đang ghim):
```console
$ docker exec onebee-ollama ollama show --license gemma4:e2b-it-qat | head -12

                                 Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

   TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION

   1. Definitions.

      "License" shall mean the terms and conditions for use, reproduction,
      and distribution as defined by Sections 1 through 9 of this document.
```
Toàn văn 178 dòng, không có chữ "Gemma Terms" hay "Prohibited" (`grep -ciE "prohibited|gemma terms"` in `0`).

### Bị loại vì giấy phép
| Thành phần | Phiên bản | Giấy phép | Tệp giấy phép đúng tag | OSI | Lý do |
|---|---|---|---|---|---|
| n8n (đang dùng, gỡ ở giai đoạn 5) | 2.42.6 | Sustainable Use License 1.0 + n8n Enterprise License (tệp `.ee.`) | https://raw.githubusercontent.com/n8n-io/n8n/n8n@2.42.6/LICENSE.md | Không | Fair-code: chỉ cho mục đích kinh doanh nội bộ |
| Open WebUI (đang dùng, gỡ ở giai đoạn 8) | từ v0.6.6; đang ghim v0.11.4 | Open WebUI License (BSD-3-Clause sửa đổi + điều khoản giữ thương hiệu khi > 50 người dùng/30 ngày) | https://raw.githubusercontent.com/open-webui/open-webui/v0.11.4/LICENSE | Không | Điều khoản thương hiệu ngoài OSI |
| MinIO | RELEASE.2025-10-15T17-29-55Z | AGPL-3.0-only | https://raw.githubusercontent.com/minio/minio/RELEASE.2025-10-15T17-29-55Z/LICENSE | Có | Plan mẹ tránh AGPL cho kho tệp lõi; SeaweedFS (Apache-2.0) thay được |
| Garage | v2.5.0 | AGPL-3.0-only | https://git.deuxfleurs.fr/Deuxfleurs/garage/raw/tag/v2.5.0/LICENSE | Có | Như MinIO |

## Số đo (nhiệm vụ 1.2)
Lệnh đã chạy cho mỗi cấu hình (tệp `do-ram.sh` trong thư mục thử): dựng cấu hình, chạy năm việc mẫu, để yên 180 giây rồi chụp một lần.
```bash
sleep 180
docker compose ps --format '{{.Name}} {{.Status}}'
docker stats --no-stream --format "{{.Name}} {{.MemUsage}}" | grep '^thu-'
```

### RAM lúc rảnh của cấu hình được chọn (Node-RED, ClamAV chạy từng lượt — không có `clamd`)
Đầu ra thật lúc 01:14:55 ngày 15/11/2026 (mọi container `Up`, `thu-db`/`thu-nodered`/`thu-authelia` `healthy`):
```console
$ docker stats --no-stream --format "{{.Name}} {{.MemUsage}}"
thu-authelia 29.11MiB / 9.712GiB
thu-nodered 71.36MiB / 9.712GiB
thu-mailpit 9.73MiB / 9.712GiB
thu-postgrest 12.3MiB / 9.712GiB
thu-seaweedfs 70.88MiB / 9.712GiB
thu-caddy 14.13MiB / 9.712GiB
thu-echo 14.18MiB / 9.712GiB
thu-cau-noi 14.6MiB / 9.712GiB
thu-kho-tep 14.23MiB / 9.712GiB
thu-db 62.83MiB / 9.712GiB
```

| Container | Vai trò | RAM lúc rảnh | Tính vào ngân sách |
|---|---|---|---|
| thu-db | PostgreSQL 18.7 + pgvector 0.8.7 | 62,83 MiB | Có |
| thu-postgrest | PostgREST 16.5 | 12,3 MiB | Có |
| thu-cau-noi | Cầu nối danh tính (Python thư viện chuẩn) | 14,6 MiB | Có |
| thu-kho-tep | Dịch vụ tệp: quét rồi ghi SeaweedFS (Python thư viện chuẩn) | 14,23 MiB | Có |
| thu-authelia | Authelia 4.39.28 | 29,11 MiB | Có |
| thu-seaweedfs | SeaweedFS 4.53 (`server -filer -s3`) | 70,88 MiB | Có |
| thu-nodered | Node-RED 5.0.9 + node-red-node-email | 71,36 MiB | Có |
| (ClamAV) | `clamscan` từng lượt: không có tiến trình thường trú | 0 MiB | Có |
| thu-caddy | Caddy 2.11.4 (đã có trong Box) | 14,13 MiB | Không (không phải thành phần mới) |
| thu-mailpit, thu-echo | Chỉ để thử (SMTP giả, dịch vụ trả tiêu đề) | 9,73 + 14,18 MiB | Không |
| **Tổng thành phần mới, lúc rảnh** | | **275,3 MiB ≈ 0,27 GB** | ≤ 1,5 GB: **đạt** |
| **Tổng lúc đang quét một lượt** (275,3 + đỉnh 962,6 của `clamscan`) | | **1.237,9 MiB ≈ 1,21 GB** | ≤ 1,5 GB: **đạt** |

### So sánh các cấu hình (cùng cách đo, mỗi ứng viên động cơ quy trình đo riêng một lần)
| Cấu hình | Động cơ | clamav (`clamd`) | db | Các thành phần mới còn lại | Tổng lúc rảnh | Tổng khi không có `clamd` | Cộng đỉnh một lượt `clamscan` |
|---|---|---|---|---|---|---|---|
| Flowable + `clamd` (00:39:44) | 371,6 MiB | 1,009 GiB | 80,01 MiB | 136,7 MiB | **1.621,5 MiB — vượt** | 588,3 MiB (suy ra) | 1.550,9 MiB — vượt |
| Node-RED + `clamd` (00:51:22) | 66,87 MiB | 1,009 GiB | 56,41 MiB | 138,3 MiB | 1.294,8 MiB — đạt khi rảnh | 261,6 MiB (suy ra) | 1.224,2 MiB |
| Kestra + `clamd` (01:11:22) | 848,6 MiB | 962,2 MiB | 112,3 MiB | 140,8 MiB | **2.063,9 MiB — vượt** | 1.101,7 MiB (suy ra) | 2.064,3 MiB — vượt |
| **Node-RED, `clamscan` từng lượt (được chọn, 01:14:55)** | 71,36 MiB | 0 | 62,83 MiB | 141,1 MiB | **275,3 MiB — đạt** | (đo trực tiếp) | 1.237,9 MiB — đạt |

"Các thành phần mới còn lại" = authelia + postgrest + seaweedfs + cau-noi + kho-tep của cùng lần chụp. Cột "suy ra" là phép trừ dòng clamav của cùng lần chụp, không phải lần đo riêng.

### ClamAV: thường trú hay từng lượt (lệnh trong `do-clamav.sh`)
```console
$ docker exec thu-clamav cat /sys/fs/cgroup/memory.current /sys/fs/cgroup/memory.peak
1091.1 MiB
2058.0 MiB
$ docker exec thu-clamav clamdscan --stream --no-summary /tmp/eicar.com   # đo thời gian bằng date +%s%N
/tmp/eicar.com: Eicar-Test-Signature FOUND
mã thoát clamdscan: 1
thời gian: 12 ms
$ docker compose --profile clamd stop clamav
$ docker run --rm --network none -v onebee-thu-loi_clamav:/var/lib/clamav:ro -v <thư mục>:/quet:ro --entrypoint sh clamav/clamav:1.5.4-debian13-slim -c 'clamscan --no-summary /quet/bao-cao.txt; cat /sys/fs/cgroup/memory.peak'
/quet/bao-cao.txt: OK
mã thoát clamscan: 0
thời gian: 10119 ms
đỉnh RAM: 962.6 MiB
$ docker run ... -c 'clamscan --no-summary /quet/eicar.com; cat /sys/fs/cgroup/memory.peak'
/quet/eicar.com: Eicar-Test-Signature FOUND
mã thoát clamscan: 1
thời gian: 10128 ms
đỉnh RAM: 959.3 MiB
```
| Cấu hình ClamAV | RAM thường trú | Đỉnh RAM (`memory.peak` của cgroup, gồm cả bộ đệm tệp) | Thời gian một lần quét |
|---|---|---|---|
| `clamd` thường trú | 1,009 GiB (`docker stats`) | 2.058,0 MiB từ lúc khởi động (nạp chữ ký + `freshclam` cập nhật) | 12 ms (`clamdscan --stream`) |
| `clamscan` từng lượt | 0 | 962,6 MiB trong ~10 giây | ~10,1 giây (gần hết là nạp chữ ký) |

### Thời gian khởi động và kích thước image
Thời gian: dừng dịch vụ (không tính), rồi tính từ lúc gọi `docker compose up -d --no-deps <dịch vụ>` tới lần trả lời đầu tiên (`do-khoi-dong.sh`).
Kích thước: `docker image ls --digests --format "{{.Repository}} {{.Digest}} {{.Size}}"`.

| Dịch vụ | Khởi động (giây) | Image (theo `docker image ls`) |
|---|---|---|
| db (pgvector/pgvector) | 0,4 | 677 MB |
| postgrest | 0,9 | 41,1 MB |
| authelia | 0,9 | 110 MB |
| seaweedfs | 2,0 | 1,08 GB |
| cau-noi, kho-tep (python) | 0,9 | 181 MB (dùng chung) |
| nodered | 2,0 | 1,02 GB |
| clamav (`clamd`, tới khi `clamdscan --ping` trả lời) | 9,7 | 556 MB |
| flowable | 8,2 | 517 MB |
| kestra (`v2.0.10-slim`) | 7,2 | 759 MB |

### Năm việc mẫu của động cơ quy trình
| Việc | Flowable 8.0.0 | Node-RED 5.0.9 | Kestra 2.0.10 |
|---|---|---|---|
| 1. Chạy theo lịch | Đạt: `timerEventDefinition R/PT1M`, 3 lần trong 3 phút | Đạt: nút `inject` 60 giây, 4 lần | Đạt: `Schedule` `*/1 * * * *` |
| 2. Nhận webhook | Đạt: `POST /runtime/process-instances` → 201 (cần tài khoản REST) | Đạt: nút `http in` `POST /webhook/don` → 202 | Đạt: `POST /executions/webhook/<ns>/<flow>/<khóa>` → 200 (không cần đăng nhập, khóa trong URL); 30 giây đầu sau khởi động trả 500 |
| 3. Gửi thư SMTP (Mailpit) | Đạt: `flowable:type="mail"` | Đạt, phải cài thêm gói `node-red-node-email` 5.2.5 | Đạt, phải cài thêm `plugin-email` 1.6.8 |
| 4. Gọi điểm cuối HTTP | Đạt: `flowable:type="http"` | Đạt: nút `http request` | Đạt: `io.kestra.plugin.core.http.Request` |
| 5. Dừng chờ duyệt/từ chối rồi đi tiếp | Đạt, có sẵn: `userTask` nhóm `quan_ly` → `POST /runtime/tasks/<id>` `complete` → rẽ nhánh → thư | Đạt, tự làm: lưu đơn chờ duyệt, `POST /duyet/<mã>/<dong-y\|tu-choi>` đi tiếp; duyệt lần hai → 404 | Đạt, có sẵn: `Pause` + `onResume` → `POST /executions/<id>/actions/resume` |
| RAM lúc rảnh | 371,6 MiB | 66,87–71,36 MiB | 848,6 MiB |

Lệnh và kết quả (rút gọn; đủ ở `thu-flowable.sh`, `thu-nodered.sh`, `thu-kestra.sh`):
```console
$ curl -u quantri:<mật khẩu thử> '$FLOWABLE/history/historic-process-instances?processDefinitionKey=thuDuyet&finished=true'
2 ['xong', 'xong']
$ curl $MAILPIT/api/v1/messages
[('Don D2: bi tu choi', 'nhanvien@thu.onebee.internal'), ('Don D1: da duyet', 'nhanvien@thu.onebee.internal')]
$ curl -H 'Content-Type: application/json' -d '{"ma_don":"D1"}' -w ' %{http_code}' $NODERED/webhook/don
{"trang_thai":"cho_duyet","ma_don":"D1"} 202
$ curl -X POST -w ' %{http_code}' $NODERED/duyet/D1/dong-y
{"ma_don":"D1","ket_qua":"dong-y"} 200
$ curl -X POST -w ' %{http_code}' $NODERED/duyet/D2/tu-choi
{"ma_don":"D2","ket_qua":"tu-choi"} 200
$ curl -X POST -w ' %{http_code}' $NODERED/duyet/D1/dong-y
{"loi":"khong co don cho duyet"} 404
$ curl $MAILPIT/api/v1/messages
[('Don D2: bi tu choi', 'nhanvien@thu.onebee.internal'), ('Don D1: da duyet', 'nhanvien@thu.onebee.internal')]
$ docker logs thu-echo 2>&1 | grep nodered/lich
172.19.0.12 - - [14/Nov/2026 17:48:15] "POST /nodered/lich HTTP/1.1" 200 -
172.19.0.12 - - [14/Nov/2026 17:49:15] "POST /nodered/lich HTTP/1.1" 200 -
$ curl -u ... -F duyet=true -w ' %{http_code}' $KESTRA/executions/<id của D1>/actions/resume
200
$ curl -u ... $KESTRA/executions/<id của D1>
D1 SUCCESS [('goi_http', 'SUCCESS'), ('cho_duyet', 'SUCCESS'), ('re_nhanh', 'SUCCESS'), ('thu_dong_y', 'SUCCESS')]
```

## Thử các điểm ghép nối (nhiệm vụ 1.3)
Cấu hình Caddy dùng khi thử (phần thêm vào cách Box đang dùng CA riêng; đoạn `forward_auth` chép đúng tài liệu Authelia
https://github.com/authelia/authelia/blob/v4.39.28/docs/content/integration/proxies/caddy.md):
```caddyfile
(xac_thuc) {
	forward_auth authelia:9091 {
		uri /api/authz/forward-auth
		copy_headers Remote-User Remote-Groups Remote-Email Remote-Name
	}
}

https://box.thu.onebee.internal, https://192.168.72.50 {
	import onebee_tls
	handle /dangnhap* {
		reverse_proxy authelia:9091
	}
	# route giữ đúng thứ tự: xác thực trên đường dẫn gốc (luật Authelia khớp ^/api/) rồi mới bỏ tiền tố
	handle /api/* {
		route {
			import xac_thuc
			uri strip_prefix /api
			reverse_proxy cau-noi:8080
		}
	}
	handle /files/* {
		route {
			import xac_thuc
			uri strip_prefix /files
			request_body {
				max_size 25MB
			}
			reverse_proxy kho-tep:8080
		}
	}
}
```
Không dùng `handle_path` cho tuyến có `forward_auth`: `handle_path` bỏ tiền tố **trước** khi `forward_auth` chạy nên Authelia thấy `/ghi_chu` thay cho `/api/ghi_chu`.

Cấu hình Authelia dùng khi thử (bí mật truyền bằng `AUTHELIA_SESSION_SECRET`, `AUTHELIA_STORAGE_ENCRYPTION_KEY`, `AUTHELIA_IDENTITY_VALIDATION_RESET_PASSWORD_JWT_SECRET`):
```yaml
server:
  address: 'tcp://:9091/dangnhap'
authentication_backend:
  file:
    path: /config/users.yml
    password:
      algorithm: argon2
access_control:
  default_policy: deny
  rules:
    - domain: 'box.thu.onebee.internal'
      subject: ['group:ky_thuat', 'group:quan_ly']
      policy: two_factor
    - domain: 'box.thu.onebee.internal'
      resources: ['^/api/', '^/files/', '^/echo/', '^/ai/']
      subject: ['group:nhan_vien']
      policy: one_factor
session:
  cookies:
    - domain: 'box.thu.onebee.internal'
      authelia_url: 'https://box.thu.onebee.internal/dangnhap'
      default_redirection_url: 'https://box.thu.onebee.internal/'
  expiration: 8h
  inactivity: 1h
storage:
  local:
    path: /data/db.sqlite3
notifier:
  filesystem:
    filename: /data/thong-bao.txt
```

### (a) Caddy `forward_auth` + Authelia, vào bằng IP và bằng tên
**(a).2 — tên miền cookie là địa chỉ IP.** Tài liệu (https://github.com/authelia/authelia/blob/v4.39.28/docs/content/configuration/session/introduction.md)
yêu cầu `domain` là "standard use domain" mà CA công cộng chịu cấp chứng chỉ, có ít nhất một dấu chấm, không trùng public suffix, `authelia_url` phải `https://`.
Không nói tới địa chỉ IP. Chạy thử:
```console
$ authelia validate-config --config /config/configuration-ip.yml      # session.cookies[0].domain: '192.168.72.50'
Configuration parsed and loaded successfully without errors.
mã thoát: 0
$ authelia validate-config --config /config/configuration.yml         # domain: 'box.thu.onebee.internal'
Configuration parsed and loaded successfully without errors.
mã thoát: 0
```
Lần chạy đầu với `server.address: 'tcp://:9091/dang-nhap'` (như đặc tả) bị từ chối:
```console
$ authelia validate-config --config /config/configuration.yml
	 - server: option 'address' must have a path with only alphanumeric characters but it's configured as '/dang-nhap'
mã thoát: 1
```
→ đường dẫn con phải chỉ gồm chữ và số; dùng `/dangnhap`.

**(a).3 và (a).5 — vào bằng tên, trang đăng nhập ở đường dẫn con** (`thu-a.sh`):
```console
$ curl --cacert pki/root.crt -o /dev/null -w '%{http_code} %{redirect_url}' https://box.thu.onebee.internal/echo/
302 https://box.thu.onebee.internal/dangnhap/?rd=https%3A%2F%2Fbox.thu.onebee.internal%2Fecho%2F&rm=GET
$ curl --cacert pki/root.crt -H 'Accept: application/json' -o /dev/null -w '%{http_code}' https://box.thu.onebee.internal/api/ghi_chu
401
$ curl --cacert pki/root.crt -H 'Remote-User: an' -H 'Remote-Groups: nhan_vien' -o /dev/null -w '%{http_code}' https://box.thu.onebee.internal/echo/
302
$ curl --cacert pki/root.crt -c jar -H 'Content-Type: application/json' -d '{"username":"an","password":"<mật khẩu thử>","targetURL":"https://box.thu.onebee.internal/echo/"}' -w '%{http_code}' https://box.thu.onebee.internal/dangnhap/api/firstfactor
{"status":"OK","data":{"redirect":"https://box.thu.onebee.internal/echo/"}} 200
Set-Cookie (giá trị đã che): set-cookie: authelia_session=<che>; expires=Sun, 15 Nov 2026 01:22:11 GMT; domain=box.thu.onebee.internal; path=/; HttpOnly; secure; SameSite=Lax
$ curl --cacert pki/root.crt -b jar -w '%{http_code}' https://box.thu.onebee.internal/echo/
{"method": "GET", "path": "/echo/", "body": "", "headers": {"Remote-Email": "an@thu.onebee.internal", "Remote-Groups": "nhan_vien", "Remote-Name": "Nguyá»n An", "Remote-User": "an", "X-Forwarded-For": "172.19.0.1", "X-Forwarded-Host": "box.thu.onebee.internal", "X-Forwarded-Proto": "https"}} 200
$ curl --cacert pki/root.crt -b jar -H 'Remote-User: binh' -H 'Remote-Groups: quan_ly' -w '%{http_code}' https://box.thu.onebee.internal/echo/
{"method": "GET", "path": "/echo/", "body": "", "headers": {"Remote-Email": "an@thu.onebee.internal", "Remote-Groups": "nhan_vien", "Remote-Name": "Nguyá»n An", "Remote-User": "an", ...}} 200
$ curl --cacert pki/root.crt -o /dev/null -w %{http_code} https://box.thu.onebee.internal/dangnhap/static/js/index.CH9gMMud.js
200
```
`Remote-Name` có dấu tiếng Việt tới nơi dưới dạng byte UTF-8 (dịch vụ Python giải mã theo Latin-1 nên in sai); dịch vụ phía sau phải tự giải mã UTF-8.

**Vào bằng IP** (Authelia chạy `configuration-ip.yml`, cookie domain `192.168.72.50`):
```console
$ curl --cacert pki/root.crt --connect-to 192.168.72.50:443:127.0.0.1:443 -o /dev/null -w '%{http_code} %{redirect_url}' https://192.168.72.50/echo/
302 https://192.168.72.50/dangnhap/?rd=https%3A%2F%2F192.168.72.50%2Fecho%2F&rm=GET
$ curl ... -c jar -d '{"username":"an","password":"<mật khẩu thử>",...}' https://192.168.72.50/dangnhap/api/firstfactor
{"status":"OK","data":{"redirect":"https://192.168.72.50/echo/"}} 200
Set-Cookie (giá trị đã che): set-cookie: authelia_session=<che>; ...; domain=192.168.72.50; path=/; HttpOnly; secure; SameSite=Lax
$ curl ... -b jar -w '%{http_code}' https://192.168.72.50/echo/
{... "Remote-User": "an", "X-Forwarded-Host": "192.168.72.50", ...} 200
$ curl ... -b jar -H 'Remote-User: binh' -H 'Remote-Groups: quan_ly' -w '%{http_code}' https://192.168.72.50/echo/
{... "Remote-Groups": "nhan_vien", "Remote-User": "an", ...} 200
```
Chỉ thử bằng `curl`; chưa thử trình duyệt nào nhận `Set-Cookie: domain=<IP>`.

**(a).4 — trang đăng nhập ở cổng TLS riêng 9443** (`server.address: 'tcp://:9091/'`, `authelia_url: 'https://box.thu.onebee.internal:9443/'`):
```console
$ curl --cacert pki/root.crt -o /dev/null -w '%{http_code} %{redirect_url}' https://box.thu.onebee.internal/echo/
302 https://box.thu.onebee.internal:9443/?rd=https%3A%2F%2Fbox.thu.onebee.internal%2Fecho%2F&rm=GET
$ curl ... -c jar -d '{"username":"an",...}' -w '%{http_code}' https://box.thu.onebee.internal:9443/api/firstfactor
{"status":"OK","data":{"redirect":"https://box.thu.onebee.internal/echo/"}} 200
$ curl ... -b jar -w '%{http_code}' https://box.thu.onebee.internal/echo/
{... "Remote-User": "an", ...} 200
```
Kết luận: đạt. Chưa có phiên → 302 tới trang đăng nhập (trình duyệt) hoặc 401 (`Accept: application/json`); đăng nhập xong → 200; `Remote-User`/`Remote-Groups` do máy khách tự gửi bị Caddy thay bằng giá trị của Authelia (có phiên) hoặc không lọt qua (chưa phiên). Authelia 4.39.28 nhận IP làm tên miền cookie (trái với dự kiến), nhưng tài liệu không hỗ trợ nên không dựa vào (QĐ2). Đường dẫn con và cổng riêng đều chạy; đường dẫn con phải chỉ gồm chữ và số.

### (b) Danh tính tới PostgREST và RLS
PostgREST 16.5 (đọc tài liệu trong kho đúng tag, vì trang docs.postgrest.org dễ trả 429):
- Bí mật: khóa `jwt-secret` / biến `PGRST_JWT_SECRET`, "must be **at least 32 characters long**"; nhận cả JWK/JWKS —
  https://github.com/PostgREST/postgrest/blob/v16.5/docs/references/configuration.rst#jwt-secret
- Khóa chọn vai trò: `jwt-role-claim-key` / `PGRST_JWT_ROLE_CLAIM_KEY`, mặc định `$.role` (JSONPath RFC 9535; cú pháp JSPath cũ bị khai tử) —
  https://github.com/PostgREST/postgrest/blob/v16.5/docs/references/auth.rst#jwt-role-extraction
- Khán giả: `jwt-aud` / `PGRST_JWT_AUD`; `exp`, `iat`, `nbf` được kiểm, cho lệch đồng hồ 30 giây — cùng tệp `auth.rst`.
- SQL đọc claim: `current_setting('request.jwt.claims', true)::json->>'sub'` —
  https://github.com/PostgREST/postgrest/blob/v16.5/docs/references/transactions.rst
- Không đặt `db-anon-role` → không có JWT hợp lệ thì không có vai trò nào (PGRST302, 401).

Bảng thử RLS (`db-init/10-loi.sh`):
```sql
CREATE ROLE authenticator LOGIN NOINHERIT NOCREATEDB NOCREATEROLE PASSWORD '<mật khẩu thử>';
CREATE ROLE nhan_vien NOLOGIN;
GRANT nhan_vien TO authenticator;
CREATE SCHEMA api;
GRANT USAGE ON SCHEMA api TO nhan_vien;
CREATE TABLE api.ghi_chu (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  chu_so_huu text NOT NULL DEFAULT (current_setting('request.jwt.claims', true)::json->>'sub'),
  noi_dung text NOT NULL,
  nhung vector(3)
);
ALTER TABLE api.ghi_chu ENABLE ROW LEVEL SECURITY;
ALTER TABLE api.ghi_chu FORCE ROW LEVEL SECURITY;
CREATE POLICY chi_cua_minh ON api.ghi_chu
  USING (chu_so_huu = current_setting('request.jwt.claims', true)::json->>'sub')
  WITH CHECK (chu_so_huu = current_setting('request.jwt.claims', true)::json->>'sub');
GRANT SELECT, INSERT ON api.ghi_chu TO nhan_vien;
```
PostgREST: `PGRST_DB_SCHEMAS=api`, `PGRST_JWT_SECRET=<64 ký tự hex>`, `PGRST_JWT_AUD=onebee-api`, không có `PGRST_DB_ANON_ROLE`.

**Phương án A — cầu nối danh tính.** Lõi của dịch vụ thử (Python thư viện chuẩn): không có `Remote-User` → 401; ký JWT HS256 sống 60 giây;
bỏ `Authorization`, `Cookie`, `Remote-*` của máy khách rồi chuyển tiếp tới `postgrest:3000`.
```python
def ky_jwt(sub: str, role: str) -> str:
    bay_gio = int(time.time())
    dau = b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    than = b64(json.dumps({"sub": sub, "role": role, "aud": "onebee-api", "iat": bay_gio, "exp": bay_gio + 60},
                          separators=(",", ":")).encode())
    chu_ky = hmac.new(BI_MAT, f"{dau}.{than}".encode(), hashlib.sha256).digest()
    return f"{dau}.{than}.{b64(chu_ky)}"
```
```console
$ curl -b jar-an -w ' %{http_code}' https://box.thu.onebee.internal/api/ghi_chu?select=chu_so_huu,noi_dung
[{"chu_so_huu":"an","noi_dung":"ghi chú của An"}] 200
$ curl -b jar-binh -w ' %{http_code}' https://box.thu.onebee.internal/api/ghi_chu?select=chu_so_huu,noi_dung
[{"chu_so_huu":"binh","noi_dung":"ghi chú của Bình"}] 200
$ curl -b jar-an -H 'Content-Type: application/json' -H 'Prefer: return=representation' -d '{"noi_dung":"An ghi them"}' -w ' %{http_code}' https://box.thu.onebee.internal/api/ghi_chu?select=chu_so_huu,noi_dung
[{"chu_so_huu":"an","noi_dung":"An ghi them"}] 201
$ curl -b jar-an -H 'Content-Type: application/json' -d '{"chu_so_huu":"binh","noi_dung":"gia mao"}' -w ' %{http_code}' https://box.thu.onebee.internal/api/ghi_chu
{"code":"42501","details":null,"hint":null,"message":"new row violates row-level security policy for table \"ghi_chu\""} 403
$ curl -b jar-an -H 'Authorization: Bearer <JWT ký bằng khóa sai, sub=binh>' -w ' %{http_code}' https://box.thu.onebee.internal/api/ghi_chu?select=chu_so_huu
[{"chu_so_huu":"an"}, {"chu_so_huu":"an"}] 200
$ curl -w ' %{http_code}' $PGRST/ghi_chu   # gọi thẳng PostgREST, không có JWT
{"code":"PGRST302","details":null,"hint":null,"message":"Anonymous access is disabled"} 401
$ curl -H 'Authorization: Bearer <JWT ký bằng khóa sai>' -w ' %{http_code}' $PGRST/ghi_chu
{"code":"PGRST301","details":"None of the keys was able to decode the JWT","hint":null,"message":"No suitable key or wrong key type"} 401
$ curl -H 'Authorization: Bearer <JWT đúng khóa, sub=an, hết hạn 120 giây trước>' -w ' %{http_code}' $PGRST/ghi_chu
{"code":"PGRST303","details":null,"hint":null,"message":"JWT expired"} 401
$ docker exec thu-db psql -U postgres -d onebee -Atc "SELECT extversion FROM pg_extension WHERE extname='vector'; SELECT chu_so_huu FROM api.ghi_chu ORDER BY nhung <-> '[0.9,0.1,0]' LIMIT 1;"
0.8.7
an
```
**Phương án B — Authelia làm nhà cung cấp OIDC, PostgREST kiểm bằng JWKS** (một PostgREST thứ hai tạm thời,
`PGRST_JWT_SECRET=<JWKS của Authelia>`, `PGRST_JWT_ROLE_CLAIM_KEY=$.groups[?(@ == 'nhan_vien')]`; client công khai, PKCE S256,
`access_token_signed_response_alg: RS256`, `claims_policy` chép `preferred_username`, `groups` vào access token):
```console
$ curl https://box.thu.onebee.internal/dangnhap/jwks.json
[('thu', 'RSA', 'RS256', 'sig')]
$ curl -b jar-an -o /dev/null -w '%{http_code} %{redirect_url}' '.../dangnhap/api/oidc/authorization?client_id=onebee-thu&response_type=code&scope=openid profile groups&...&audience=onebee-api'
303 https://box.thu.onebee.internal/oidc-ve?code=<che>&iss=https%3A%2F%2Fbox.thu.onebee.internal%2Fdangnhap&scope=openid+profile+groups&state=thu12345678
$ curl -d grant_type=authorization_code -d code=<mã> -d client_id=onebee-thu -d redirect_uri=... -d code_verifier=<...> .../dangnhap/api/oidc/token
{'access_token': '<che>', 'expires_in': 3599, 'id_token': '<che>', 'scope': 'openid profile groups', 'token_type': 'bearer'}
{'alg': 'RS256', 'kid': 'thu', 'typ': 'at+jwt'}
{'aud': ['onebee-api'], 'client_id': 'onebee-thu', 'groups': ['nhan_vien'], 'iss': 'https://box.thu.onebee.internal/dangnhap', 'preferred_username': 'an', 'sub': '<uuid>', ...}
$ curl -H 'Authorization: Bearer <access token của Authelia>' -w ' %{http_code}' $PGRST_B/ghi_chu?select=chu_so_huu,noi_dung
[] 200
```
PostgREST nhận chữ ký RS256 qua JWKS và vai trò từ `groups`, nhưng `sub` là UUID của Authelia (không phải tên đăng nhập) nên RLS theo `sub` trả rỗng;
token sống 1 giờ và ứng dụng phải tự làm luồng OAuth.

Kết luận: đạt với phương án A — người A không đọc, không ghi được dòng của người B; JWT sai chữ ký, hết hạn, hoặc không có JWT đều nhận 401; JWT giả do máy khách gửi bị cầu nối bỏ. Phương án B chạy được về chữ ký nhưng cần đổi RLS sang `preferred_username` và token 1 giờ, không chọn (QĐ4).

### (c) Tải tệp qua API tới SeaweedFS, kiểm dịch bằng ClamAV
Dịch vụ thử `kho-tep` (Python thư viện chuẩn): `PUT /files/<tên>` → gửi nội dung tới `clamd` bằng `zINSTREAM` → sạch thì `PUT` vào filer
`/tep/<Remote-User>/<tên>`, nhiễm → 422, `clamd` không trả lời → 503 (không bao giờ ghi tệp chưa quét).
```console
$ docker exec thu-clamav clamdscan --version
ClamAV 1.5.4/28178/Mon Nov  9 06:24:16 2026
$ curl -T bao-cao.txt -w ' %{http_code}' https://box.thu.onebee.internal/files/bao-cao.txt   # không có phiên
303
$ curl -b jar-an -T bao-cao.txt -w ' %{http_code}' https://box.thu.onebee.internal/files/bao-cao.txt
{"duong_dan": "/tep/an/bao-cao.txt", "clamd": "stream: OK", "filer": 201} 201
$ curl -b jar-an -T eicar.com -w ' %{http_code}' https://box.thu.onebee.internal/files/eicar.com
{"loi": "tep bi chan", "clamd": "stream: Eicar-Test-Signature FOUND"} 422
$ curl -H 'Accept: application/json' $FILER/tep/an/   # liệt kê thư mục trên SeaweedFS filer
['/tep/an/bao-cao.txt']
$ curl -w ' %{http_code}' $FILER/tep/an/bao-cao.txt
Bao cao thang 11 cua HTX
 200
$ curl -o /dev/null -w '%{http_code}' $FILER/tep/an/eicar.com
404
```
`clamscan` từng lượt cho cùng kết quả (`OK` / `Eicar-Test-Signature FOUND`, xem phần Số đo).

Kết luận: đạt. Tệp sạch được ghi vào SeaweedFS, tệp chứa chuỗi thử EICAR bị chặn (422) và không có trên filer (404); chưa có phiên thì không tải lên được (303 tới trang đăng nhập).

### (d) Hai lớp không cần SMTP
```console
$ docker exec thu-authelia authelia storage user totp generate kythuat --config /config/configuration.yml
Successfully generated TOTP configuration for user 'kythuat' with URI 'otpauth://totp/OneBee%20Box%20thu:kythuat?algorithm=SHA1&digits=6&issuer=OneBee+Box+thu&period=30&secret=<che>'
```
Người dùng tự ghi danh, mã xác minh danh tính lấy từ tệp của `notifier.filesystem` (`thu-d.sh`):
```console
$ curl -b jar-binh -X POST -w ' %{http_code}' https://box.thu.onebee.internal/dangnhap/api/user/session/elevation
{"status":"OK","data":{"delete_id":"<che>"}} 200
$ docker exec thu-authelia tail -n 40 /data/thong-bao.txt   # mã đã che
Recipient: {Trần Bình binh@thu.onebee.internal}
Subject: Confirm your identity
...
The following one-time code should only be used in the prompt displayed in your browser.
----------------------------------------
<MÃ 8 KÝ TỰ>
----------------------------------------
$ curl -b jar-binh -X PUT -d '{"otc":"<mã trong tệp>"}' -w ' %{http_code}' https://box.thu.onebee.internal/dangnhap/api/user/session/elevation
{"status":"OK"} 200
$ curl -b jar-binh -X PUT -d '{"algorithm":"SHA1","length":6,"period":30}' -w ' %{http_code}' https://box.thu.onebee.internal/dangnhap/api/secondfactor/totp/register
{"status":"OK","data":{"base32_secret":"<che>","otpauth_url":"otpauth://totp/OneBee%20Box%20thu:binh?algorithm=SHA1&digits=6&issuer=OneBee+Box+thu&period=30&secret=<che>"}} 200
$ curl -b jar-binh -X POST -d '{"token":"<mã TOTP hiện tại>"}' -w ' %{http_code}' https://box.thu.onebee.internal/dangnhap/api/secondfactor/totp/register
{"status":"OK"} 200
$ curl -b jar-binh -X POST -d '{"token":"<mã TOTP hiện tại>"}' -w ' %{http_code}' https://box.thu.onebee.internal/dangnhap/api/secondfactor/totp
{"status":"OK","data":{"redirect":"https://box.thu.onebee.internal/"}} 200
$ curl -b jar-binh https://box.thu.onebee.internal/dangnhap/api/state
{"status":"OK","data":{"username":"binh","authentication_level":2,"factor_knowledge":true,"default_redirection_url":"https://box.thu.onebee.internal/"}}
```
Kết luận: đạt. `totp generate` in một URI `otpauth://` chứa khóa bí mật (thêm `--path` để ghi mã QR ra tệp PNG); bộ thông báo ghi tệp đủ cho bước xác minh danh tính: mã 8 ký tự nằm trong `/data/thong-bao.txt`, nhập vào thì ghi danh và đăng nhập hai lớp được (`authentication_level: 2`).

### (e) Uptime Kuma sau SSO
Thử bằng một bản sao `onebee-kuma.js` thêm biến `KUMA_TAT_DANG_NHAP` (đọc `getSettings`, gửi lại nguyên cài đặt với `disableAuth`, giống cách script đang làm với `trustProxy`):
```js
if (process.env.KUMA_TAT_DANG_NHAP) {
  const muon = process.env.KUMA_TAT_DANG_NHAP === "1";
  const g = await call("getSettings");
  if (!g.ok) out(1, `LỖI: không đọc được cài đặt Uptime Kuma: ${g.msg}`);
  if (Boolean(g.data.disableAuth) !== muon) {
    const r = await call("setSettings", { ...g.data, disableAuth: muon }, pass);
    if (!r.ok) out(1, `LỖI: không lưu được disableAuth: ${r.msg}`);
    doi++;
  }
}
```
Luật Authelia **không phân biệt cổng**: với cổng 13001 của Kuma, nhân viên vẫn khớp luật `^/api/` và vào được `/api/badge/...` của Kuma:
```console
$ curl -b jar-an -o /dev/null -w %{http_code} https://box.thu.onebee.internal:13001/api/badge/1/status
200
```
Sửa trong Caddy: gắn tiền tố `/giam-sat` vào đường dẫn Authelia thấy, bỏ tiền tố đó khi Authelia trả người dùng về:
```caddyfile
https://box.thu.onebee.internal:13001 {
	import onebee_tls
	route {
		uri strip_prefix /giam-sat
		forward_auth authelia:9091 {
			uri /api/authz/forward-auth
			header_up X-Forwarded-Uri /giam-sat{http.request.uri}
			copy_headers Remote-User Remote-Groups Remote-Email Remote-Name
		}
		reverse_proxy uptime-kuma:3001
	}
}
```
```console
$ curl -b jar-an -o /dev/null -w %{http_code} https://box.thu.onebee.internal:13001/api/badge/1/status
403
$ curl -o /dev/null -w "%{http_code} %{redirect_url}" https://box.thu.onebee.internal:13001/dashboard
302 https://box.thu.onebee.internal/dangnhap/?rd=https%3A%2F%2Fbox.thu.onebee.internal%3A13001%2Fgiam-sat%2Fdashboard&rm=GET
$ curl -b jar-an -o /dev/null -w '%{http_code}' https://box.thu.onebee.internal:13001/dashboard   # nhân viên
403
$ curl -b jar-kythuat -o /dev/null -w '%{http_code} %{redirect_url}' https://box.thu.onebee.internal:13001/dashboard   # kỹ thuật mới qua một lớp
302 https://box.thu.onebee.internal/dangnhap/?rd=https%3A%2F%2Fbox.thu.onebee.internal%3A13001%2Fdashboard&rm=GET
$ curl -b jar-kythuat -o /dev/null -w %{http_code} https://box.thu.onebee.internal:13001/giam-sat/dashboard   # đã qua lớp hai
200
$ docker exec -i -w /app -e KUMA_USER=quantri -e KUMA_PASS=<mật khẩu thử> -e KUMA_TAT_DANG_NHAP=0 thu-uptime-kuma node - < dich-vu/onebee-kuma.js
Uptime Kuma: đã tạo tài khoản quản trị
Uptime Kuma: đã cập nhật (1 thay đổi)
socket.io (polling) qua https://box.thu.onebee.internal:13001/socket.io/ với jar-kythuat: 40 42["info" 42["loginRequired"
$ docker exec -i -w /app -e KUMA_USER=quantri -e KUMA_PASS=<mật khẩu thử> -e KUMA_TAT_DANG_NHAP=1 thu-uptime-kuma node - < dich-vu/onebee-kuma.js
Uptime Kuma: đã cập nhật (1 thay đổi)
socket.io (polling) qua https://box.thu.onebee.internal:13001/socket.io/ với jar-kythuat: 40 42["apiKeyList" 42["autoLogin" 42["dockerHostList" 42["info" 42["monitorList" ...
```
Kết luận: đạt. Sau `forward_auth` (chỉ `ky_thuat`, hai lớp), đặt `disableAuth` qua `onebee-kuma.js` thì Kuma gửi `autoLogin` thay cho `loginRequired` — kỹ thuật chỉ đăng nhập một lần ở Authelia; nhân viên nhận 403. Cần thêm tiền tố `/giam-sat` ở Caddy vì luật Authelia không phân biệt cổng.

## Quyết định (nhiệm vụ 1.4)

### QĐ1 — Thành phần được chọn và bản ghim
Digest là của bản đa kiến trúc (index), lấy bằng `docker buildx imagetools inspect <image>:<tag>` ngày 14/11/2026; tất cả có `linux/amd64` và `linux/arm64`.

| Dịch vụ | Image ghim |
|---|---|
| Định danh, SSO, hai lớp | `docker.io/authelia/authelia:4.39.28@sha256:bd97cff4fcbf715b5ff1f9ae286afbe6033afce385302520b0368122d43a6f54` |
| Cổng API (đang có, thêm `forward_auth`) | `docker.io/library/caddy:2.11.4@sha256:0c994536bddb66445885237f1a5dcc1916bccea922661c76b4e9fc24061f9b52` (giữ nguyên, ADR 0005) |
| CSDL + vector | `docker.io/pgvector/pgvector:0.8.7-pg18-trixie@sha256:ab49524d18df7200b74ac9a475e1db6297fc1eb57da4c214c63d10ecc4b754fa` |
| API tự sinh | `docker.io/postgrest/postgrest:v16.5@sha256:1347d7552b88f17832912c06afbf7c43209af6eeeb60834b04aae12c9bd9d5cc` |
| Cầu nối danh tính, dịch vụ tệp (mã trong repo, MIT) | `docker.io/library/python:3.14.10-slim-trixie@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f` |
| Kho tệp phi cấu trúc | `docker.io/chrislusf/seaweedfs:4.53@sha256:ccad23e18639c8b98cee17e7100b95830a06077b56d8e5b006d6dcf8ec5e94a0` |
| Kiểm dịch | Dựng từ `docker.io/clamav/clamav:1.5.4-debian13-slim@sha256:76a9c3b63764b78178dc68fa7efcceca0cde2c8c9d4f925a8e697cb4511f8fdc`, bỏ `libclamunrar` và dồn về một lớp (QĐ5); nơi dựng chờ anh Thiện quyết |
| Động cơ quy trình | `docker.io/nodered/node-red:5.0.9@sha256:2ccd38b4066648bd5e17430c50a2f8102c566a82fd4f2fc5c342e61664d6896f` (+ gói `node-red-node-email` 5.2.5) |
| Mô hình AI | Ollama `0.34.4` + `gemma4:e2b-it-qat` (giữ nguyên) |

Đã thử nhưng không chọn: `docker.io/flowable/flowable-rest:8.0.0@sha256:708dfa32f27b93180bb6e7a30684d881d995fe257f5b8413e14b20a55c25672d`,
`docker.io/kestra/kestra:v2.0.10-slim@sha256:eb1ff43db0a1008cdc7d8a8967928f1a2bdf8ae07942f2ba1679dc27e208f793`.
Chỉ dùng khi thử: `docker.io/axllent/mailpit:v1.33.1@sha256:aef2aacc11f075ec0fb6874275ee4a421e688e11a96ebb296134d1735c7761ce`.

### QĐ2 — SSO bằng tên, không bằng IP
Người dùng vào SSO bằng `https://box.<mã>.onebee.internal/` (đã nằm trong ràng buộc tên của CA, ADR 0005). Session cookie đặt cho đúng tên này.
`https://<IP>/` vẫn mở trang chủ (kèm hướng dẫn mở bằng tên); các tuyến lõi `/dangnhap/`, `/api/`, `/files/`, `/ai/` chỉ phục vụ trên tên.
Lý do: Authelia 4.39.28 có nhận IP (mục (a)), nhưng tài liệu yêu cầu tên miền chuẩn và không nói tới IP, chưa thử trình duyệt nào, và Docker Hub
của Authelia có tag nhánh `feat-session-ip` (suy ra từ tên tag là hỗ trợ IP còn đang làm; chưa đọc mã của nhánh đó). Dựa vào hành vi không có trong tài liệu thì một bản vá có thể làm hỏng
đăng nhập của mọi người.
Phân giải tên:
- Máy trạm OneBee: dòng `/etc/hosts` `<IP Box> box.<mã>.onebee.internal`, đẩy xuống qua `them-may`/`dong-bo-may` cùng lúc với CA.
- Điện thoại, máy ngoài quản lý: một bản ghi DNS tĩnh trên router của đơn vị (cách khuyến nghị) hoặc dòng hosts; vẫn phải cài CA như ADR 0005 QĐ7.
- Kỹ thuật qua Tailscale: như ADR 0005 QĐ7.
Xem lại khi Authelia ghi rõ hỗ trợ IP trong tài liệu.

### QĐ3 — Trang đăng nhập ở đường dẫn con `/dangnhap` của cổng 443
`server.address: 'tcp://:9091/dangnhap'`, `authelia_url: 'https://box.<mã>.onebee.internal/dangnhap'`; Caddy `handle /dangnhap* { reverse_proxy authelia:9091 }`.
Cả hai cách đã thử đều chạy; chọn đường dẫn con vì không thêm cổng nào vào tường lửa, cookie vẫn dùng chung giữa các cổng (cookie không tách theo cổng).
Tên đường dẫn phải chỉ gồm chữ và số (Authelia từ chối `/dang-nhap`).

### QĐ4 — Danh tính tới PostgREST: phương án A, JWT 60 giây
Caddy `forward_auth` (Authelia) → cầu nối danh tính (Python thư viện chuẩn, mã trong repo) → PostgREST. Cầu nối đọc `Remote-User`, `Remote-Groups`,
ánh xạ nhóm sang vai trò PostgreSQL, ký JWT HS256 với `sub` = tên đăng nhập, `role`, `aud: onebee-api`, `iat`, `exp` = 60 giây; bỏ `Authorization`,
`Cookie`, `Remote-*` do máy khách gửi. PostgREST: `PGRST_JWT_SECRET` (≥ 32 ký tự, sinh ngẫu nhiên 64 ký tự hex), `PGRST_JWT_AUD=onebee-api`,
`jwt-role-claim-key` để mặc định `$.role`, không đặt `db-anon-role`. RLS đọc `current_setting('request.jwt.claims', true)::json->>'sub'`.
Không chọn B vì: `sub` của Authelia là UUID nên mọi chính sách RLS phải dựa vào `preferred_username`; access token sống 1 giờ, không thu hồi được;
mỗi ứng dụng phải tự làm luồng OAuth + PKCE thay cho cookie SSO sẵn có. B vẫn là phương án lùi đã thử chạy được.

### QĐ5 — ClamAV chạy từng lượt; cập nhật chữ ký không cần Internet
Không chạy `clamd` thường trú. Tệp tải lên vào vùng chờ kiểm dịch; một tác vụ duy nhất (không chạy song song) gọi `clamscan` trên cả lô
(`docker run --rm --network none` với kho chữ ký chỉ đọc), tệp sạch mới được chuyển vào SeaweedFS, tệp nhiễm bị giữ lại và báo.
Lý do: theo số đo, ngân sách 1,5 GB phải đúng cả lúc đỉnh. `clamscan` từng lượt: rảnh 0, đỉnh 962,6 MiB trong ~10 giây → tổng lúc quét 1.237,9 MiB.
`clamd`: thường trú 1,009 GiB, đỉnh cgroup 2.058,0 MiB khi nạp/cập nhật chữ ký → riêng ClamAV đã vượt ngưỡng lúc đỉnh. Đổi lại: tệp có độ trễ
tới lần quét kế tiếp (~10 giây mỗi lượt), không chặn ngay ở lúc tải lên.
Cập nhật chữ ký khi Box không có Internet: kỹ thuật chạy `cvd update` (cvdupdate, Apache-2.0) trên máy có Internet, chép `main.cvd`, `daily.cvd`,
`bytecode.cvd` sang Box (USB hoặc qua Tailscale) bằng một lệnh `onebee-box` ở giai đoạn kho tệp; `clamscan` đọc chữ ký mới ở lượt kế tiếp, không cần
nạp lại tiến trình nào. Có máy trong LAN làm gương thì đặt `PrivateMirror` cho `freshclam`. Box có Internet thì `freshclam` chạy theo lịch.

**Mô-đun UnRAR (giấy phép ngoài OSI).** Image chính chủ đã ghim có `libclamunrar`; `libclamav` không liên kết cứng với nó mà nạp bằng `dlopen`
(`ldd /usr/lib/libclamav.so.12 | grep -i unrar` rỗng, chuỗi `libclamunrar_iface` nằm trong `libclamav.so.12.1.0`):
```console
$ docker run --rm --entrypoint sh clamav/clamav:1.5.4-debian13-slim@sha256:76a9c3b6… -c "find / -xdev -name 'libclamunrar*' 2>/dev/null | xargs ls -la"
lrwxrwxrwx 1 root root     18 Nov  9 06:02 /usr/lib/libclamunrar.so -> libclamunrar.so.12
lrwxrwxrwx 1 root root     22 Nov  9 06:02 /usr/lib/libclamunrar.so.12 -> libclamunrar.so.12.1.0
-rw-r--r-- 1 root root 347008 Nov  9 06:01 /usr/lib/libclamunrar.so.12.1.0
lrwxrwxrwx 1 root root     24 Nov  9 06:02 /usr/lib/libclamunrar_iface.so -> libclamunrar_iface.so.12
lrwxrwxrwx 1 root root     28 Nov  9 06:02 /usr/lib/libclamunrar_iface.so.12 -> libclamunrar_iface.so.12.1.0
-rw-r--r-- 1 root root  20736 Nov  9 06:02 /usr/lib/libclamunrar_iface.so.12.1.0
```
Đã thử ba cách loại (`thu-unrar.sh`, chữ ký tải bằng `freshclam` vào một volume riêng; `eicar.zip` là EICAR trong tệp zip):

| Cách | Còn `libclamunrar` trong image | `clamscan` bao-cao.txt / eicar.com / eicar.zip | Ghi chú |
|---|---|---|---|
| 1. `FROM` image ghim + `RUN rm -f /usr/lib/libclamunrar*` | **Còn** trong lớp gốc (lớp trên chỉ có tệp che `.wh.libclamunrar*`) | OK / FOUND / FOUND | Không đạt: tệp vẫn được tải về và nằm trong image |
| 2. Như 1 rồi `FROM scratch` + `COPY --from=goc / /` (một lớp) | **Không** (0 lớp có `libclamunrar`) | OK / FOUND / FOUND | Đạt; ClamAV vẫn là 1.5.4 chính chủ, 551 MB |
| 3. Gói `clamav` kho main của Debian 13 trên `debian:trixie-slim@sha256:a72b4433…` | **Không** (gói `1.4.3+dfsg-1`; `libclamunrar12` không có trong kho main) | OK / FOUND / FOUND | Đạt; dòng 1.4 LTS được vá tới 15/08/2027 nhưng Debian đang ở 1.4.3, thượng nguồn đã có 1.4.6 |

```console
$ docker save onebee-thu/clamav-khong-unrar:1.5.4 | tar -x; tìm libclamunrar trong từng lớp     # cách 1
lớp b66c239f… (gồm: usr/lib/libclamunrar.so usr/lib/libclamunrar.so.12 usr/lib/libclamunrar.so.12.1.0 usr/lib/libclamunrar_iface.so …)
lớp d31c6395… (gồm: usr/lib/.wh.libclamunrar.so usr/lib/.wh.libclamunrar.so.12 usr/lib/.wh.libclamunrar.so.12.1.0 …)
số lớp có libclamunrar: 2
$ docker save onebee-thu/clamav-khong-unrar:1.5.4-mot-lop | tar -x; đếm lớp có libclamunrar     # cách 2
lớp chứa clamscan: 1; lớp có libclamunrar: 0
$ docker run --rm --network none -v <chữ ký>:/var/lib/clamav:ro -v <thư mục>:/quet:ro --entrypoint sh onebee-thu/clamav-khong-unrar:1.5.4-mot-lop -c "clamscan --version; clamscan --no-summary /quet/bao-cao.txt /quet/eicar.com /quet/eicar.zip; …"
ClamAV 1.5.4/28183/Sat Nov 14 06:24:17 2026
/quet/bao-cao.txt: OK
/quet/eicar.com: Eicar-Test-Signature FOUND
/quet/eicar.zip: Eicar-Test-Signature FOUND
mã thoát: 1
LibClamAV debug: Cannot dlopen libclamunrar_iface: /usr/lib/libclamunrar_iface..a: cannot open shared object file: No such file or directory - unrar support unavailable
$ (đối chứng, image gốc) clamscan --debug … | grep -i unrar
LibClamAV debug: unrar support loaded from /usr/lib/libclamunrar_iface.so.12.1.0
$ docker run --rm -v <chữ ký>:/var/lib/clamav:ro -v <thư mục>:/quet:ro debian:trixie-slim@sha256:a72b4433… sh -c 'apt-get install -y clamav; …'   # cách 3
  Installed: 1.4.3+dfsg-1
ClamAV 1.4.3/28183/Sat Nov 14 06:24:17 2026
libclamav12:amd64 1.4.3+dfsg-1
số tệp libclamunrar*: 0
apt-cache show libclamunrar12 (kho):
E: No packages found
/quet/bao-cao.txt: OK
/quet/eicar.com: Eicar-Test-Signature FOUND
/quet/eicar.zip: Eicar-Test-Signature FOUND
```
Chọn cách 2 (giữ đúng bản 1.5.4 đã đo). Dockerfile đã thử:
```dockerfile
FROM docker.io/clamav/clamav:1.5.4-debian13-slim@sha256:76a9c3b63764b78178dc68fa7efcceca0cde2c8c9d4f925a8e697cb4511f8fdc AS goc
RUN rm -f /usr/lib/libclamunrar.so* /usr/lib/libclamunrar_iface.so*

FROM scratch
COPY --from=goc / /
ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC
EXPOSE 3310/tcp 7357/tcp
HEALTHCHECK --start-period=6m CMD clamdcheck.sh
ENTRYPOINT ["/init"]
```
Hệ quả: không mở được bên trong tệp `.rar` (zip vẫn quét được). Còn hai việc cần anh Thiện quyết (mục Rủi ro còn lại).

### QĐ6 — Động cơ quy trình: Node-RED
Node-RED 5.0.9 làm được cả năm việc mẫu, RAM rảnh 66,87–71,36 MiB, khởi động 2,0 giây; là cấu hình duy nhất giữ tổng ≤ 1,5 GB cả lúc rảnh lẫn lúc quét.
Bước duyệt không có sẵn nên tự làm: đơn chờ duyệt lưu trong một bảng PostgreSQL (qua PostgREST, không cần gói thêm; bản thử dùng bộ nhớ ngữ cảnh
nên mất khi khởi động lại), điểm cuối duyệt/từ chối đứng sau `forward_auth` nhóm `quan_ly` và ghi `Remote-User` của người duyệt.
Loại Flowable 8.0.0: có sẵn `userTask`, làm đủ năm việc, nhưng RAM rảnh 371,6 MiB (JVM, bản thử không giới hạn heap) → tổng 1.621,5 MiB với `clamd`
và 1.550,9 MiB lúc quét với `clamscan` từng lượt — vượt ngưỡng trong cả hai cách.
Loại Kestra 2.0.10: có sẵn `Pause`/`resume`, làm đủ năm việc, nhưng RAM rảnh 848,6 MiB; bản `slim` lúc khởi động tự tải plugin từ Internet
(`PluginAutoInstallService`) và webhook trả 500 trong ~30 giây đầu; bản đầy đủ có một lớp image 4,68 GB.

### QĐ7 — Ghi danh hai lớp khi chưa có SMTP; đăng nhập của Uptime Kuma
Hai lớp: dùng `notifier.filesystem` khi Box chưa cấu hình email. Người dùng tự ghi danh TOTP trên trang đăng nhập; mã xác minh 8 ký tự ghi vào tệp
thông báo, quản trị đọc bằng một lệnh `onebee-box` và đưa trực tiếp cho người dùng. Khóa TOTP chỉ hiện trên máy người dùng, quản trị không thấy.
`authelia storage user totp generate <tên> --path <tệp.png>` chỉ dùng khi người dùng không tự làm được (quản trị thấy khóa bí mật). Khi đã có SMTP
thì chuyển `notifier` sang `smtp`.
Uptime Kuma: đứng sau `forward_auth`, luật Authelia chỉ cho `ky_thuat` với `two_factor`, Caddy gắn tiền tố `/giam-sat` như mục (e);
`onebee-kuma.js` thêm việc đặt `disableAuth` để kỹ thuật không phải đăng nhập hai lần. Chỉ tắt đăng nhập riêng khi HTTPS và SSO có hiệu lực.

## Rủi ro còn lại
- **Cần anh Thiện quyết — nơi dựng image ClamAV không có UnRAR.** Cách 2 ở QĐ5 vẫn phải kéo image chính chủ (có `libclamunrar`) về máy dựng.
  (i) Dựng trên CI rồi đẩy lên một registry của dự án (ví dụ GHCR): Box chỉ tải bản sạch, nhưng dự án phải tự duy trì và ký một image;
  (ii) bộ cài dựng ngay trên Box: không cần registry, nhưng image chính chủ có UnRAR vẫn được tải về Box của khách (xóa sau khi dựng);
  (iii) dùng gói Debian `1.4.3+dfsg` (cách 3): không cần image chính chủ, nhưng chậm bản vá hơn thượng nguồn. Chưa chọn.
- **Cần anh Thiện quyết — tệp `.rar`.** Không có UnRAR thì `clamscan` không mở được tệp `.rar`; chưa thử tệp `.rar` thật (không có công cụ tạo RAR
  nguồn mở) nên chưa biết nó báo `OK` hay lỗi. Đề xuất: dịch vụ tệp từ chối tệp có chữ ký đầu `Rar!` thay vì cho qua mà không quét.
- **Cầu nối danh tính, dịch vụ tệp và Uptime Kuma (khi `disableAuth`) tin bất kỳ ai nối được tới chúng trong mạng Docker.** Mọi container cùng mạng
  (Node-RED có nút function chạy mã tùy ý) gửi được `Remote-User: <bất kỳ>` thẳng tới `cau-noi:8080`. Phải tách mạng Docker: chỉ Caddy nối được tới
  cầu nối, dịch vụ tệp, Kuma; chỉ cầu nối nối được tới PostgREST.
- **Trình chỉnh sửa Node-RED là nơi chạy mã**: phải đứng sau `forward_auth` nhóm `ky_thuat` hai lớp và bật `adminAuth`; bản thử để mở trong mạng Docker.
- **Luật Authelia không phân biệt cổng**: mọi dịch vụ ở cổng khác 443 phải gắn tiền tố đường dẫn như mục (e), không thì luật của nhân viên khớp nhầm.
- `notifier.filesystem` được tài liệu Authelia khuyên chỉ dùng để thử; chấp nhận cho tới khi đơn vị có SMTP, quản trị phải giữ kín tệp thông báo.
- Tên `box.<mã>.onebee.internal` cần DNS hoặc hosts trên mọi thiết bị ngoài quản lý; thiết bị không làm được thì không dùng được SSO.
- Đỉnh 962,6 MiB của `clamscan` cộng thêm vào lúc Ollama đang nạp model: trên Box 8 GB chưa đo cùng lúc. Lượt quét nên tránh chạy song song với hỏi đáp AI nặng.
- Số đo trên máy ảo 4 vCPU/10 GB, chưa có tải thật; chưa đo trên Box thật hay CI `box=true`.

## Hệ quả
- Giai đoạn SSO + cổng API: thêm Authelia, cầu nối danh tính; Caddy thêm `/dangnhap`, `/api/`, `/files/`, `/ai/` trên tên `box.<mã>.onebee.internal`;
  `them-may`/`dong-bo-may` đẩy thêm dòng hosts; `onebee-kuma.js` thêm `disableAuth`. Cầu nối phải tự giải mã `Remote-Name` theo UTF-8.
- Giai đoạn dữ liệu cấu trúc: PostgreSQL + pgvector + PostgREST, RLS theo claim `sub` (= tên đăng nhập) của JWT 60 giây.
- Giai đoạn động cơ quy trình: Node-RED thay n8n; phải đóng gói sẵn `node-red-node-email` (Box có thể không có Internet lúc cài) và bảng trạng thái duyệt.
- Giai đoạn kho tệp: SeaweedFS + hàng chờ kiểm dịch `clamscan` từng lượt (image ClamAV không có UnRAR) + lệnh nhập chữ ký ClamAV ngoại tuyến.
- Mỗi image mới có một dòng trong `LICENSES.md`, ghim tag + digest trong `group_vars/all.yml`, `no-new-privileges`, không có `ports:`.
