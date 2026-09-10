#!/usr/bin/env bash
# ============================================================================
# InstaTrueReel — smali analysis grep battery
# Usage: ./analyze.sh <decoded-dir> [extra_patterns_csv]
# Produces ./reports/*.txt with contextual grep results.
# ============================================================================
set -u
DECODED="${1:-decoded}"
EXTRA="${2:-}"
mkdir -p reports

ctx() { # name pattern [context-lines]
  local name="$1" pat="$2" c="${3:-8}"
  grep -rn -C "$c" --include="*.smali" "$pat" "$DECODED"/smali* > "reports/${name}.txt" 2>/dev/null || true
  echo "  [${name}] $(wc -l < "reports/${name}.txt") lines"
}

files() { # name pattern
  local name="$1" pat="$2"
  grep -rl --include="*.smali" "$pat" "$DECODED"/smali* > "reports/${name}-files.txt" 2>/dev/null || true
  echo "  [${name}] $(wc -l < "reports/${name}-files.txt") files"
}

echo "=== Window / insets APIs ==="
files "setOnApplyWindowInsetsListener" "setOnApplyWindowInsetsListener"
ctx  "setOnApplyWindowInsetsListener" "setOnApplyWindowInsetsListener" 14
files "setStatusBarColor" "setStatusBarColor"
ctx  "setStatusBarColor" "setStatusBarColor" 10
files "setNavigationBarColor" "setNavigationBarColor"
ctx  "setNavigationBarColor" "setNavigationBarColor" 10
files "setDecorFitsSystemWindows" "setDecorFitsSystemWindows"
ctx  "setDecorFitsSystemWindows" "setDecorFitsSystemWindows" 12
files "setSystemUiVisibility" "setSystemUiVisibility"
ctx  "setSystemUiVisibility" "setSystemUiVisibility" 8
files "WindowInsetsController-hide" "WindowInsetsController;->hide"
ctx  "WindowInsetsController-hide" "WindowInsetsController;->hide" 10
files "setFitsSystemWindows" "setFitsSystemWindows"
ctx  "setFitsSystemWindows" "setFitsSystemWindows" 6
files "getSystemWindowInsetTop" "getSystemWindowInsetTop"
ctx  "getSystemWindowInsetTop" "getSystemWindowInsetTop" 10
files "getSystemWindowInsetBottom" "getSystemWindowInsetBottom"
ctx  "getSystemWindowInsetBottom" "getSystemWindowInsetBottom" 10
files "WindowInsets-getInsets" "Landroid/view/WindowInsets;->getInsets"
ctx  "WindowInsets-getInsets" "Landroid/view/WindowInsets;->getInsets" 10
files "layoutInDisplayCutoutMode" "layoutInDisplayCutoutMode"
files "WindowInsetsController" "WindowInsetsController;"

echo "=== Window flag constants ==="
# 0x400 = FLAG_FULLSCREEN, 0x800 = FLAG_FORCE_NOT_FULLSCREEN,
# 0x80000000 = FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS, 0x2000000 = FLAG_LAYOUT_NO_LIMITS
grep -rn --include="*.smali" -B2 "0x80000000" "$DECODED"/smali* | grep -B2 "addFlags" > reports/addFlags-drawsSystemBars.txt 2>/dev/null || true
grep -rn --include="*.smali" -B2 "0x2000000" "$DECODED"/smali* | grep -B2 "addFlags" > reports/addFlags-noLimits.txt 2>/dev/null || true
echo "  [addFlags-drawsSystemBars] $(wc -l < reports/addFlags-drawsSystemBars.txt) lines"
echo "  [addFlags-noLimits] $(wc -l < reports/addFlags-noLimits.txt) lines"

echo "=== Reels / Clips surface ==="
files "reel_viewer_media_container" "reel_viewer_media_container"
ctx  "reel_viewer_media_container" "reel_viewer_media_container" 8
files "clips_viewer-str" "clips_viewer"
files "ClipsViewerSource" "ClipsViewerSource"
files "reels_viewer-str" "reels_viewer"
files "IGWindowInsets" "IgWindowInsets\|WindowInsetsUtil\|InsetsUtil"

echo "=== Known helper classes (from jadx mapping) ==="
for cls in "X/ked.smali" "X/2Ib.smali" "X/0Wu.smali"; do
  found=$(find "$DECODED"/smali* -path "*/$cls" 2>/dev/null | head -2)
  echo "  $cls -> ${found:-NOT FOUND}"
done

echo "=== Class-name matches (reel/clip/inset) ==="
find "$DECODED"/smali* -name "*.smali" 2>/dev/null | grep -iE "reel|clips" | sort > reports/classnames-reel-clips.txt || true
echo "  [classnames-reel-clips] $(wc -l < reports/classnames-reel-clips.txt) files"
find "$DECODED"/smali* -name "*.smali" 2>/dev/null | grep -iE "inset" | sort > reports/classnames-inset.txt || true
echo "  [classnames-inset] $(wc -l < reports/classnames-inset.txt) files"

if [ -n "$EXTRA" ]; then
  echo "=== Extra patterns from input ==="
  IFS=',' read -ra PATS <<< "$EXTRA"
  i=0
  for pat in "${PATS[@]}"; do
    pat=$(echo "$pat" | xargs)
    [ -z "$pat" ] && continue
    i=$((i+1))
    ctx "extra-$i" "$pat" 10
  done
fi

echo "=== Report inventory ==="
ls -la reports/
