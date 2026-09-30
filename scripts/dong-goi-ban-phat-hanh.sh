#!/usr/bin/env bash
# Đóng gói bản phát hành OneBee OS: dist/onebee-os-<phiên-bản>.tar.gz + SHA256SUMS + ghi-chu-phat-hanh.md
# Cách dùng: scripts/dong-goi-ban-phat-hanh.sh 0.5.0
# Chỉ đóng gói file đã commit (git archive) → không lẫn file tạm, khóa, mật khẩu trên máy người đóng gói.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
ver="${1:-}"
die() { printf 'LỖI: %s\n' "$*" >&2; exit 1; }
[[ "${ver}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "Cách dùng: $0 <phiên-bản, ví dụ 0.5.0>"
[[ -z "$(git status --porcelain)" ]] || die "Còn thay đổi chưa commit — commit trước khi đóng gói"
grep -q "^onebee_version: \"${ver}\"$" desktop/ansible/group_vars/all.yml || die "desktop/ansible/group_vars/all.yml chưa ghi phiên bản ${ver}"
grep -q "^onebee_box_version: \"${ver}\"$" box/ansible/group_vars/all.yml || die "box/ansible/group_vars/all.yml chưa ghi phiên bản ${ver}"
grep -q "^## \[${ver}\]" docs/project-changelog.md || die "docs/project-changelog.md chưa có mục [${ver}]"
# Không đóng gói file trông như khóa bí mật (phòng ai đó lỡ commit)
if git ls-files | grep -Eq '(^|/)(\.env|.*\.pem|id_(rsa|ed25519)|.*secrets?/.+)$'; then die "Có file giống khóa bí mật trong repo: $(git ls-files | grep -E '(^|/)(\.env|.*\.pem|id_(rsa|ed25519)|.*secrets?/.+)$')"; fi

ten="onebee-os-${ver}"
mkdir -p dist
rm -f "dist/${ten}.tar.gz" dist/SHA256SUMS dist/ghi-chu-phat-hanh.md
# Gói sản phẩm: bộ cài, tài liệu, kiểm thử, giấy phép. Không gồm hồ sơ hội thi, kế hoạch nội bộ, demo mô phỏng.
git archive --format=tar.gz --prefix="${ten}/" -o "dist/${ten}.tar.gz" HEAD \
  desktop box tests scripts docs/huong-dan docs/adr docs/kinh-doanh docs/project-changelog.md LICENSES.md README.md
(cd dist && sha256sum "${ten}.tar.gz" > SHA256SUMS)
# Ghi chú phát hành = mục của phiên bản này trong changelog
awk -v v="## [${ver}]" 'index($0, v) == 1 {p = 1; print; next} p && /^## \[/ {exit} p' docs/project-changelog.md \
  > dist/ghi-chu-phat-hanh.md
echo "Đã tạo:"; ls -la dist; cat dist/SHA256SUMS
echo "Kiểm tra trên máy tải về: sha256sum -c SHA256SUMS"
