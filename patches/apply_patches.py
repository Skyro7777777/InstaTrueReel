#!/usr/bin/env python3
"""
InstaTrueReel — smali patcher (v3, Phase 2 — NATIVE EDGE-TO-EDGE).

Root cause (verified against base APK smali + decoded layouts):
  Instagram v435 already CONTAINS a native edge-to-edge Reels mode gated by
  X/9Wz.EEr()Z  ==  !ClipsViewerConfig.A2g && (A3H || QE flag BHQ 0x8109d400023873).
  When false, X/2Iv feeds bds_black (0x7f060052) into the window-chrome writer
  X/1fC.A04 -> opaque status-bar scrim = THE BLACK STRIP. The media container
  (layout_clips_viewer_fragment: ViewPager2 0x7F0B3F45) is already match_parent
  x match_parent and the window already runs 0x700 flags — only the opaque bar
  color hides the full-bleed video.

Patches applied to the decoded smali tree:

  1. X/9Wz.EEr()Z  -> FORCED TRUE (native edge-to-edge reels mode: transparent
     status bar via bds_transparent, action-bar/overlay self-padding through
     2Iv.A0A -> 6BM insets listener -> 0jS.A15(statusBarHeight), icon appearance
     via 0Xm, EEr-aware overlay layout in ACN/ACO binders). Both entry points
     are covered: the Reels tab delegates AFt.EEr() -> child 9Wz (X/3Cz).
  2. Installs X/TTrueReelHelper (window apply/restore/reapply helper, activity
     scoped interceptors, per-entry toast + logcat) and X/TTrueReelReapply.
  3. ClipsViewerFragment (X/9Wz):
       onResume        -> helper.apply()
       onPause         -> helper.restore()
       onDestroyView   -> helper.restore()
       onHiddenChanged -> added override -> helper bridge
  4. ClipsTabFragment (X/AFt):
       onResume        -> helper.apply()
       onPause         -> added override -> helper.restore()
       onDestroyView   -> helper.restore()
       onHiddenChanged -> added override -> helper bridge
  5. X/1fC.A04(Activity, color) interceptor: color forced fully transparent while
     Reels is active on the same Activity (defeats EVERY status-bar repaint,
     including the Choreographer-deferred WindowChromeColorDeferer branch).
  6. X/1fI.A04(Activity, color) interceptor: navigation-bar color forced fully
     transparent while Reels is active (NEW in v0.3 — nav strip stays black in
     v0.2).
  7. REMOVED vs v0.2: the X/1fC.A06 interceptor (A06 is dead code in v435 —
     zero callers app-wide, verified by full-tree scan).

Idempotent: safe to re-run. Fails loudly (exit 1) if any anchor is not found.
"""
import os
import re
import shutil
import sys

DECODED = sys.argv[1] if len(sys.argv) > 1 else "decoded"
HERE = os.path.dirname(os.path.abspath(__file__))

HELPER_SRC = os.path.join(HERE, "helper_TTrueReelHelper.smali")
HELPER_DST = os.path.join(DECODED, "smali_classes16", "X", "TTrueReelHelper.smali")
REAPPLY_SRC = os.path.join(HERE, "helper_TTrueReelReapply.smali")
REAPPLY_DST = os.path.join(DECODED, "smali_classes16", "X", "TTrueReelReapply.smali")

CLIPS_VIEWER = os.path.join(DECODED, "smali_classes16", "X", "9Wz.smali")
CLIPS_TAB = os.path.join(DECODED, "smali_classes16", "X", "AFt.smali")
WINDOW_CHROME = os.path.join(DECODED, "smali_classes13", "X", "1fC.smali")
NAV_CHROME = os.path.join(DECODED, "smali_classes13", "X", "1fI.smali")

APPLY = "invoke-static/range {p0 .. p0}, LX/TTrueReelHelper;->A00(Landroidx/fragment/app/Fragment;)V"
RESTORE = "invoke-static/range {p0 .. p0}, LX/TTrueReelHelper;->A01(Landroidx/fragment/app/Fragment;)V"
HIDDEN = "invoke-static {p0, p1}, LX/TTrueReelHelper;->A02(Landroidx/fragment/app/Fragment;Z)V"

# Interceptor injections for X/1fC.A04 and X/1fI.A04 (both .locals 4 with two
# params -> p0=v4, p1=v5; all < 16 so non-range invoke-static is valid).
INTERCEPT_STATUS_COLOR = (
    "invoke-static {p0, p1}, LX/TTrueReelHelper;->A03(Landroid/app/Activity;I)I\n"
    "    move-result p1"
)
INTERCEPT_NAV_COLOR = (
    "invoke-static {p0, p1}, LX/TTrueReelHelper;->A07(Landroid/app/Activity;I)I\n"
    "    move-result p1"
)

# Forced-true replacement body for 9Wz.EEr()Z (native edge-to-edge master switch).
EER_METHOD_OLD = re.compile(
    r"\.method public final EEr\(\)Z\n"
    r"(?:[^\n]*\n)*?"
    r"\.end method\n",
    re.MULTILINE,
)
EER_METHOD_NEW = (
    ".method public final EEr()Z\n"
    "    .locals 1\n"
    "\n"
    "    # instatruereel: EEr forced true -> native edge-to-edge reels mode ON\n"
    "    # (transparent status bar + inset-padded overlays; overrides A2g/A3H/QE)\n"
    "    const/4 v0, 0x1\n"
    "\n"
    "    return v0\n"
    ".end method\n"
)
EER_MARKER = "instatruereel: EEr forced true"

ON_HIDDEN_OVERRIDE_2YN = (
    "\n.method public onHiddenChanged(Z)V\n"
    "    .locals 0\n"
    "\n"
    "    invoke-super {p0, p1}, LX/2yN;->onHiddenChanged(Z)V\n"
    "\n"
    "    " + HIDDEN + "\n"
    "\n"
    "    return-void\n"
    ".end method\n"
)

ON_PAUSE_OVERRIDE_ANDROIDX = (
    "\n.method public onPause()V\n"
    "    .locals 0\n"
    "\n"
    "    invoke-super {p0}, Landroidx/fragment/app/Fragment;->onPause()V\n"
    "\n"
    "    " + RESTORE + "\n"
    "\n"
    "    return-void\n"
    ".end method\n"
)

errors = []
report = []


def read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def write(path, content):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def inject_after_locals(content, method_pattern, inject_text, label):
    """Insert inject_text (may be multi-line) right after the `.locals` directive
    of the first method matching method_pattern. Idempotent via marker.
    Returns (new_content, ok)."""
    marker = "# instatruereel:" + label
    if marker in content:
        report.append(f"  [skip] {label}: already patched")
        return content, True
    m = re.search(
        r"(?m)^\.method[^\n]*" + re.escape(method_pattern) + r"[^\n]*\n(?:[ \t]*\n|[ \t]*#[^\n]*\n)*[ \t]*\.locals \d+\n",
        content,
    )
    if not m:
        errors.append(f"{label}: method/method-header not found: {method_pattern}")
        return content, False
    insert_at = m.end()
    block = "    " + marker + "\n    " + inject_text + "\n"
    new = content[:insert_at] + block + content[insert_at:]
    report.append(f"  [ ok ] {label}: injected")
    return new, True


def append_method(content, method_text, marker, label):
    if marker in content:
        report.append(f"  [skip] {label}: already present")
        return content
    if not content.endswith("\n"):
        content += "\n"
    report.append(f"  [ ok ] {label}: appended")
    return content + method_text


def replace_method(content, regex, replacement, marker, label, expect=1):
    """Replace whole method bodies matched by regex. Idempotent via marker."""
    if marker in content:
        report.append(f"  [skip] {label}: already patched")
        return content
    new, n = regex.subn(replacement, content, count=expect)
    if n != expect:
        errors.append(f"{label}: expected {expect} match(es), found {n}")
        return content
    report.append(f"  [ ok ] {label}: replaced ({n})")
    return new


def main():
    # ---------- sanity: targets exist ----------
    for path in (CLIPS_VIEWER, CLIPS_TAB, WINDOW_CHROME, NAV_CHROME):
        if not os.path.isfile(path):
            errors.append(f"missing target file: {path}")

    if errors:
        finish()

    # ---------- 1. install helpers ----------
    os.makedirs(os.path.dirname(HELPER_DST), exist_ok=True)
    if os.path.isfile(HELPER_DST):
        report.append("  [skip] helper TTrueReelHelper already installed")
    else:
        shutil.copyfile(HELPER_SRC, HELPER_DST)
        report.append("  [ ok ] helper TTrueReelHelper installed -> smali_classes16/X/TTrueReelHelper.smali")

    if os.path.isfile(REAPPLY_DST):
        report.append("  [skip] helper TTrueReelReapply already installed")
    else:
        shutil.copyfile(REAPPLY_SRC, REAPPLY_DST)
        report.append("  [ ok ] helper TTrueReelReapply installed -> smali_classes16/X/TTrueReelReapply.smali")

    # ---------- 2. THE CORE PATCH: force 9Wz.EEr() = true ----------
    report.append("ClipsViewerFragment native edge-to-edge switch (X/9Wz.EEr):")
    src = read(CLIPS_VIEWER)

    if ".super LX/2yN;" not in src:
        errors.append("9Wz: unexpected superclass (expected LX/2yN;)")
    if '__redex_internal_original_name:Ljava/lang/String; = "ClipsViewerFragment"' not in src:
        errors.append("9Wz: expected ClipsViewerFragment redex name not found (version drift?)")
    if ".method public final EEr()Z" not in src:
        errors.append("9Wz: EEr()Z method not found (version drift?)")

    src = replace_method(src, EER_METHOD_OLD, EER_METHOD_NEW, EER_MARKER, "9Wz.EEr -> forced true")
    write(CLIPS_VIEWER, src)

    # ---------- 3. fragment lifecycle hooks ----------
    report.append("ClipsViewerFragment lifecycle (X/9Wz):")
    src = read(CLIPS_VIEWER)
    src, _ = inject_after_locals(src, "onResume()V", APPLY, "9Wz.onResume -> apply")
    src, _ = inject_after_locals(src, "onPause()V", RESTORE, "9Wz.onPause -> restore")
    src, _ = inject_after_locals(src, "onDestroyView()V", RESTORE, "9Wz.onDestroyView -> restore")
    src = append_method(src, ON_HIDDEN_OVERRIDE_2YN, "onHiddenChanged(Z)V", "9Wz.onHiddenChanged override")
    write(CLIPS_VIEWER, src)

    # ---------- 4. ClipsTabFragment (X/AFt) ----------
    report.append("ClipsTabFragment (X/AFt):")
    src = read(CLIPS_TAB)

    if ".super LX/2yN;" not in src:
        errors.append("AFt: unexpected superclass (expected LX/2yN;)")
    if '__redex_internal_original_name:Ljava/lang/String; = "ClipsTabFragment"' not in src:
        errors.append("AFt: expected ClipsTabFragment redex name not found (version drift?)")

    src, _ = inject_after_locals(src, "onResume()V", APPLY, "AFt.onResume -> apply")
    src, _ = inject_after_locals(src, "onDestroyView()V", RESTORE, "AFt.onDestroyView -> restore")
    src = append_method(src, ON_HIDDEN_OVERRIDE_2YN, "onHiddenChanged(Z)V", "AFt.onHiddenChanged override")
    src = append_method(src, ON_PAUSE_OVERRIDE_ANDROIDX, "onPause()V", "AFt.onPause override")
    write(CLIPS_TAB, src)

    # ---------- 5. status-bar color interceptor (X/1fC.A04) ----------
    report.append("WindowChromeController status bar (X/1fC.A04):")
    src = read(WINDOW_CHROME)

    if ".super Ljava/lang/Object;" not in src:
        errors.append("1fC: unexpected superclass (expected Ljava/lang/Object;)")

    src, _ = inject_after_locals(
        src,
        "A04(Landroid/app/Activity;I)V",
        INTERCEPT_STATUS_COLOR,
        "1fC.A04 -> transparent-while-reels",
    )
    write(WINDOW_CHROME, src)

    # ---------- 6. navigation-bar color interceptor (X/1fI.A04) ----------
    report.append("WindowChromeController navigation bar (X/1fI.A04):")
    src = read(NAV_CHROME)

    if ".super Ljava/lang/Object;" not in src:
        errors.append("1fI: unexpected superclass (expected Ljava/lang/Object;)")

    src, _ = inject_after_locals(
        src,
        "A04(Landroid/app/Activity;I)V",
        INTERCEPT_NAV_COLOR,
        "1fI.A04 -> transparent-while-reels",
    )
    write(NAV_CHROME, src)

    # ---------- verify ----------
    report.append("Verification:")
    checks = [
        (CLIPS_VIEWER, EER_MARKER, "9Wz.EEr forced-true present"),
        (CLIPS_VIEWER, "const/4 v0, 0x1", "9Wz.EEr returns true"),
        (CLIPS_VIEWER, APPLY, "9Wz apply present"),
        (CLIPS_VIEWER, RESTORE, "9Wz restore present"),
        (CLIPS_VIEWER, HIDDEN, "9Wz hidden bridge present"),
        (CLIPS_TAB, APPLY, "AFt apply present"),
        (CLIPS_TAB, RESTORE, "AFt restore present"),
        (CLIPS_TAB, HIDDEN, "AFt hidden bridge present"),
        (WINDOW_CHROME, "LX/TTrueReelHelper;->A03(Landroid/app/Activity;I)I", "1fC color interceptor present"),
        (NAV_CHROME, "LX/TTrueReelHelper;->A07(Landroid/app/Activity;I)I", "1fI nav interceptor present"),
        (HELPER_DST, ".method public static A00(", "helper apply method present"),
        (HELPER_DST, ".method public static A01(", "helper restore method present"),
        (HELPER_DST, ".method public static A02(", "helper hidden bridge present"),
        (HELPER_DST, ".method public static A03(", "helper color interceptor present"),
        (HELPER_DST, ".method public static A07(", "helper nav interceptor present"),
        (HELPER_DST, ".method public static A05()V", "helper scheduler present"),
        (HELPER_DST, ".method public static A06(", "helper reapply core present"),
        (HELPER_DST, 'const-string v1, "InstaTrueReel v0.3: true 9:16 Reels ON"', "toast marker v0.3 present"),
        (REAPPLY_DST, ".implements Ljava/lang/Runnable;", "reapply runnable present"),
    ]
    for path, needle, label in checks:
        if needle in read(path):
            report.append(f"  [ ok ] {label}")
        else:
            report.append(f"  [FAIL] {label}")
            errors.append(f"verification failed: {label}")

    finish()


def finish():
    print("InstaTrueReel patch report (v3)")
    print("===============================")
    for line in report:
        print(line)
    if errors:
        print()
        print("ERRORS:")
        for e in errors:
            print("  !! " + e)
        sys.exit(1)
    print()
    print("All patches applied cleanly.")


if __name__ == "__main__":
    main()
