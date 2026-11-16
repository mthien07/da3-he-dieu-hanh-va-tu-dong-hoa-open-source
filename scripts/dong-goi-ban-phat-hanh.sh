#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
# Đóng gói bản phát hành OneBee OS: dist/onebee-os-<phiên-bản>.tar.gz + SHA256SUMS + ghi-chu-phat-hanh.md
# Cách dùng: scripts/dong-goi-ban-phat-hanh.sh 0.5.0
#   Gói thử từ cây đang làm việc: scripts/dong-goi-ban-phat-hanh.sh 1.3.0-dev (ghi chú lấy từ mục [Unreleased];
#   không kiểm phiên bản trong group_vars; từ chối chạy trong GitHub Actions để không phát hành nhầm).
# Chỉ đóng gói file đã commit (git archive) → không lẫn file tạm, khóa, mật khẩu trên máy người đóng gói.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
ver="${1:-}"
die() { printf 'LỖI: %s\n' "$*" >&2; exit 1; }
[[ "${ver}" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-rc\.[0-9]+|-dev)?$ ]] || die "Cách dùng: $0 <phiên-bản, ví dụ 1.0.0, 1.0.0-rc.1 hoặc 1.0.0-dev>"
muc_ghi_chu="## [${ver}]"
if [[ "${ver}" == *-dev ]]; then
  [[ "${GITHUB_ACTIONS:-}" != "true" ]] || die "Gói thử -dev không dùng để phát hành"
  muc_ghi_chu="## [Unreleased]"
fi
[[ -z "$(git status --porcelain)" ]] || die "Còn thay đổi chưa commit — commit trước khi đóng gói"
if [[ "${ver}" != *-dev ]]; then
  grep -q "^onebee_version: \"${ver}\"$" desktop/ansible/group_vars/all.yml || die "desktop/ansible/group_vars/all.yml chưa ghi phiên bản ${ver}"
  grep -q "^onebee_box_version: \"${ver}\"$" box/ansible/group_vars/all.yml || die "box/ansible/group_vars/all.yml chưa ghi phiên bản ${ver}"
fi
awk -v v="${muc_ghi_chu}" 'index($0, v) == 1 {f = 1} END {exit !f}' CHANGELOG.md || die "CHANGELOG.md chưa có mục ${muc_ghi_chu#\#\# }"
# Không đóng gói file trông như khóa bí mật (phòng ai đó lỡ commit)
if git ls-files | grep -Eq '(^|/)(\.env|.*\.pem|id_(rsa|ed25519)|.*secrets?/.+)$'; then die "Có file giống khóa bí mật trong repo: $(git ls-files | grep -E '(^|/)(\.env|.*\.pem|id_(rsa|ed25519)|.*secrets?/.+)$')"; fi

ten="onebee-os-${ver}"
mkdir -p dist
rm -f "dist/${ten}.tar.gz" dist/SHA256SUMS dist/ghi-chu-phat-hanh.md
# Gói sản phẩm: bộ cài, tài liệu, kiểm thử, giấy phép. Không gồm hồ sơ hội thi, kế hoạch nội bộ, demo mô phỏng.
git archive --format=tar.gz --prefix="${ten}/" -o "dist/${ten}.tar.gz" HEAD \
  desktop box tests scripts docs/huong-dan docs/adr docs/kinh-doanh LICENSE LICENSES.md CHANGELOG.md CONTRIBUTING.md SECURITY.md README.md
(cd dist && sha256sum "${ten}.tar.gz" > SHA256SUMS)
# Ghi chú phát hành = mục của phiên bản này trong changelog
awk -v v="${muc_ghi_chu}" 'index($0, v) == 1 {p = 1; print; next} p && /^## \[/ {exit} p' CHANGELOG.md \
  > dist/ghi-chu-phat-hanh.md
echo "Đã tạo:"; ls -la dist; cat dist/SHA256SUMS
echo "Kiểm tra trên máy tải về: sha256sum -c SHA256SUMS"
