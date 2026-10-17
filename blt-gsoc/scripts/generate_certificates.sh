#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
certificate_dir="$repo_dir/certificates/2026-interns"
background="$certificate_dir/assets/certificate-background.png"
logo="$repo_dir/images/logo.png"

mkdir -p "$certificate_dir"
name_file="$(mktemp)"
trap 'rm -f "$name_file"' EXIT

serif_regular="/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
serif_bold="/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
sans_bold="/usr/share/fonts/opentype/urw-base35/NimbusSans-Bold.otf"
signature_font="/usr/share/fonts/opentype/urw-base35/Z003-MediumItalic.otf"

generate_certificate() {
  local slug="$1"
  local recipient="$2"
  local project="$3"
  printf '%s' "$recipient" > "$name_file"

  ffmpeg -hide_banner -loglevel error -y \
    -i "$background" -i "$logo" \
    -filter_complex "[0:v]scale=1920:1080[base];[1:v]scale=-1:84[mark];[base][mark]overlay=x=620:y=112,drawtext=fontfile=${sans_bold}:text='OWASP BLT':fontcolor=0B1830:fontsize=62:x=730:y=117,drawtext=fontfile=${serif_bold}:text='CERTIFICATE OF COMPLETION':fontcolor=0B1830:fontsize=54:x=(w-text_w)/2:y=245,drawtext=fontfile=${serif_regular}:text='THIS CERTIFICATE IS PROUDLY PRESENTED TO':fontcolor=A8894A:fontsize=24:x=(w-text_w)/2:y=335,drawtext=fontfile=${serif_bold}:textfile=${name_file}:fontcolor=C8102E:fontsize=70:x=(w-text_w)/2:y=390,drawtext=fontfile=${serif_regular}:text='in recognition of the successful completion of the':fontcolor=26354D:fontsize=28:x=(w-text_w)/2:y=500,drawtext=fontfile=${serif_bold}:text='OWASP BLT 2026 INTERNSHIP PROGRAM':fontcolor=0B1830:fontsize=34:x=(w-text_w)/2:y=550,drawtext=fontfile=${serif_regular}:text='and outstanding open-source security contributions to':fontcolor=26354D:fontsize=28:x=(w-text_w)/2:y=605,drawtext=fontfile=${serif_bold}:text='${project}':fontcolor=C8102E:fontsize=38:x=(w-text_w)/2:y=655,drawtext=fontfile=${serif_regular}:text='Awarded August 30, 2026':fontcolor=6B5B3E:fontsize=24:x=(w-text_w)/2:y=725,drawtext=fontfile=${signature_font}:text='Donnie Brown':fontcolor=13213A:fontsize=58:x=1280:y=795,drawtext=fontfile=${serif_bold}:text='Donnie Brown':fontcolor=13213A:fontsize=22:x=1325:y=866,drawtext=fontfile=${serif_regular}:text='OWASP BLT Project Lead':fontcolor=6B5B3E:fontsize=19:x=1285:y=900" \
    -frames:v 1 -threads 1 "$certificate_dir/$slug.png"
}

generate_certificate "savio-dsouza" "Savio D'souza" "BLT-Preflight"
generate_certificate "ojaswa" "Ojaswa" "BLT-Toasty"
generate_certificate "nachiket-roy" "Nachiket Roy" "BLT-MCP"
generate_certificate "karuna-rapolu" "Karuna Rapolu" "BLT-SafeCloak"
generate_certificate "rudra-pratap-singh" "Rudra Pratap Singh" "BLT-Hackerhouse"
generate_certificate "sidd190" "Sidd190" "BLT-Autopatch"
generate_certificate "jayant" "Jayant" "BLT-MAYO"

echo "Generated certificates in $certificate_dir"
