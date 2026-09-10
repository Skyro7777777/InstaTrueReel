#!/usr/bin/env python3
"""
InstaTrueReel — smali patcher (v2, Phase 1.1).

Applies TikTok-style edge-to-edge (true 9:16 reels) patches to the decoded
Instagram smali tree:

  1. Installs X/TTrueReelHelper (window edge-to-edge apply/restore/reapply
     helper + activity-scoped interceptors) and X/TTrueReelReapply (Runnable).
  2. ClipsViewerFragment (X/9Wz):
       onResume        -> helper.apply()
       onPause         -> helper.restore()
       onDestroyView   -> helper.restore()
       onHiddenChanged -> added override -> helper bridge
  3. ClipsTabFragment (X/AFt):
       onResume        -> helper.apply()
       onPause         -> added override -> helper.restore()
       onDestroyView   -> helper.restore()
       onHiddenChanged -> added override -> helper bridge
  4. X/1fC (Instagram window-chrome controller) interceptors, active ONLY
     while Reels is showing (activity-scoped):
       A04(Activity, color)  -> color forced to fully transparent (0x00000000)
                                while Reels active on the same Activity.
                                Defeats every status-bar repaint, including the
                                Choreographer-deferred WindowChromeColorDeferer.
       A06(View, Window, Z)  -> forced to the "exit fullscreen" branch so the
                                status bar stays VISIBLE (TikTok style) while
                                Reels active on the same Window.

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

APPLY = "invoke-static/range {p0 .. p0}, LX/TTrueReelHelper;->A00(Landroidx/fragment/app/Fragment;)V"
RESTORE = "invoke-static/range {p0 .. p0}, LX/TTrueReelHelper;->A01(Landroidx/fragment/app/Fragment;)V"
HIDDEN = "invoke-static {p0, p1}, LX/TTrueReelHelper;->A02(Landroidx/fragment/app/Fragment;Z)V"

# Interceptor injections for X/1fC (params are low-index registers here:
# 1fC.A04 .locals 4 -> p0=v4, p1=v5; 1fC.A06 .locals 2 -> p1=v3, p2=v4; all < 16).
INTERCEPT_COLOR = (
    "invoke-static {p0, p1}, LX/TTrueReelHelper;->A03(Landroid/app/Activity;I)I\n"
    "    move-result p1"
)
INTERCEPT_FULLSCREEN = (
    "invoke-static {p1, p2}, LX/TTrueReelHelper;->A04(Landroid/view/Window;Z)Z\n"
    "    move-result p2"
)

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


def main():
    # ---------- sanity: targets exist ----------
    for path in (CLIPS_VIEWER, CLIPS_TAB, WINDOW_CHROME):
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

    # ---------- 2. patch ClipsViewerFragment (X/9Wz) ----------
    report.append("ClipsViewerFragment (X/9Wz):")
    src = read(CLIPS_VIEWER)

    if ".super LX/2yN;" not in src:
        errors.append("9Wz: unexpected superclass (expected LX/2yN;)")
    if '__redex_internal_original_name:Ljava/lang/String; = "ClipsViewerFragment"' not in src:
        errors.append("9Wz: expected ClipsViewerFragment redex name not found (version drift?)")

    src, _ = inject_after_locals(src, "onResume()V", APPLY, "9Wz.onResume -> apply")
    src, _ = inject_after_locals(src, "onPause()V", RESTORE, "9Wz.onPause -> restore")
    src, _ = inject_after_locals(src, "onDestroyView()V", RESTORE, "9Wz.onDestroyView -> restore")
    src = append_method(src, ON_HIDDEN_OVERRIDE_2YN, "onHiddenChanged(Z)V", "9Wz.onHiddenChanged override")
    write(CLIPS_VIEWER, src)

    # ---------- 3. patch ClipsTabFragment (X/AFt) ----------
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

    # ---------- 4. patch window-chrome controller (X/1fC) ----------
    report.append("WindowChromeController (X/1fC):")
    src = read(WINDOW_CHROME)

    if ".super Ljava/lang/Object;" not in src:
        errors.append("1fC: unexpected superclass (expected Ljava/lang/Object;)")

    src, _ = inject_after_locals(
        src,
        "A04(Landroid/app/Activity;I)V",
        INTERCEPT_COLOR,
        "1fC.A04 -> transparent-while-reels",
    )
    src, _ = inject_after_locals(
        src,
        "A06(Landroid/view/View;Landroid/view/Window;Z)V",
        INTERCEPT_FULLSCREEN,
        "1fC.A06 -> no-fullscreen-while-reels",
    )
    write(WINDOW_CHROME, src)

    # ---------- verify ----------
    report.append("Verification:")
    checks = [
        (CLIPS_VIEWER, APPLY, "9Wz apply present"),
        (CLIPS_VIEWER, RESTORE, "9Wz restore present"),
        (CLIPS_VIEWER, HIDDEN, "9Wz hidden bridge present"),
        (CLIPS_TAB, APPLY, "AFt apply present"),
        (CLIPS_TAB, RESTORE, "AFt restore present"),
        (CLIPS_TAB, HIDDEN, "AFt hidden bridge present"),
        (WINDOW_CHROME, "LX/TTrueReelHelper;->A03(Landroid/app/Activity;I)I", "1fC color interceptor present"),
        (WINDOW_CHROME, "LX/TTrueReelHelper;->A04(Landroid/view/Window;Z)Z", "1fC fullscreen interceptor present"),
        (HELPER_DST, ".method public static A00(", "helper apply method present"),
        (HELPER_DST, ".method public static A01(", "helper restore method present"),
        (HELPER_DST, ".method public static A02(", "helper hidden bridge present"),
        (HELPER_DST, ".method public static A03(", "helper color interceptor present"),
        (HELPER_DST, ".method public static A04(", "helper fullscreen interceptor present"),
        (HELPER_DST, ".method public static A05()V", "helper scheduler present"),
        (HELPER_DST, ".method public static A06(", "helper reapply core present"),
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
    print("InstaTrueReel patch report")
    print("==========================")
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
