#!/usr/bin/env bash
# dong-goi-usb-offline.sh — Chuẩn bị gói cài đặt OneBee Box Offline ra USB/Thư mục
# Chạy trên máy kỹ thuật viên có Internet để chuẩn bị gói mang đi triển khai tại cơ sở.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${HERE}/.." && pwd)"
ALL_YML="${ROOT}/box/ansible/group_vars/all.yml"

THU_MUC_DICH="${1:-}"
BO_QUA_DOCKER="${2:-}"
if [[ -z "${THU_MUC_DICH}" ]]; then
  echo "Cách dùng: $0 <đường-dẫn-thư-mục-usb-hoặc-thư-mục-đích> [--bo-qua-docker]"
  echo "Ví dụ:    $0 /Volumes/USB_ONEBEE/onebee-bundle"
  echo "          $0 /tmp/onebee-offline-bundle --bo-qua-docker"
  exit 1
fi

mkdir -p "${THU_MUC_DICH}/images"
mkdir -p "${THU_MUC_DICH}/repo"

echo "=== BẮT ĐẦU ĐÓNG GÓI BỘ CÀI ONEBEE BOX OFFLINE ==="
echo "Thư mục đích: ${THU_MUC_DICH}"

# 1. Đọc danh sách image ghim digest từ all.yml
echo "--> Đang trích xuất danh sách Docker image ghim digest..."
IMAGES=()
while IFS= read -r img; do
  [[ -n "${img}" ]] && IMAGES+=("${img}")
done < <(grep -E '^\s+[a-z_]+:\s+\S+@sha256:[a-f0-9]+' "${ALL_YML}" | awk '{print $2}')

if [[ ${#IMAGES[@]} -eq 0 ]]; then
  echo "LỖI: Không tìm thấy danh sách Docker image trong ${ALL_YML}" >&2
  exit 1
fi

echo "Đã tìm thấy ${#IMAGES[@]} Docker images cần lưu trữ:"
for img in "${IMAGES[@]}"; do
  echo "  • ${img}"
done

# 2. Tải và lưu Docker images
TARGET_TAR="${THU_MUC_DICH}/images/onebee-docker-images.tar.gz"
echo "--> Đang tải và đóng gói Docker images (lưu vào ${TARGET_TAR})..."
if [[ "${BO_QUA_DOCKER}" == "--bo-qua-docker" ]]; then
  echo "  (Bỏ qua tải Docker images theo tùy chọn --bo-qua-docker)"
  touch "${TARGET_TAR}"
elif command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  for img in "${IMAGES[@]}"; do
    echo "  Kéo image: ${img}..."
    docker pull "${img}" || true
  done
  echo "  Lưu toàn bộ images vào file nén..."
  docker save "${IMAGES[@]}" | gzip > "${TARGET_TAR}"
  echo "  ✓ Đã lưu xong Docker images."
else
  echo "CẢNH BÁO: Docker daemon không khả dụng. Tạo file mẫu rỗng."
  touch "${TARGET_TAR}"
fi

# 3. Sao chép mã nguồn repo sang USB
echo "--> Đang đồng bộ mã nguồn OneBee OS sang ${THU_MUC_DICH}/repo..."
# Sao chép các tệp cần thiết, loại bỏ thư mục tạm/git thừa
if command -v rsync >/dev/null 2>&1; then
  rsync -a --exclude='.git' --exclude='.worktrees' --exclude='.claude' --exclude='reports' "${ROOT}/" "${THU_MUC_DICH}/repo/"
else
  cp -R "${ROOT}/"* "${THU_MUC_DICH}/repo/" || true
fi

# 4. Sao chép script cài offline vào thư mục gốc USB
cp "${HERE}/cai-tu-usb-offline.sh" "${THU_MUC_DICH}/"
chmod +x "${THU_MUC_DICH}/cai-tu-usb-offline.sh"

# 5. Tạo file checksum xác thực tính toàn vẹn
echo "--> Tạo file băm kiểm tra toàn vẹn (SHA-256)..."
(
  cd "${THU_MUC_DICH}"
  find images repo -type f -exec sha256sum {} + > CHECKSUMS.sha256 2>/dev/null || true
)

echo "=== HOÀN TẤT ĐÓNG GÓI BỘ CÀI OFFLINE! ==="
echo "Khi đến cơ sở HTX:"
echo "1. Cắm USB vào máy chủ Box."
echo "2. Chuyển vào thư mục: cd ${THU_MUC_DICH}"
echo "3. Chạy lệnh cài đặt: sudo ./cai-tu-usb-offline.sh"
