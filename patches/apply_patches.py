#!/usr/bin/env python3
"""
InstaTrueReel — smali patcher (v4, Phase 3 — TIKTOK-STYLE OVERLAYS).

State of the world (v0.3 field-tested on Android 10, 9:16):
  * EEr() forced TRUE works: reel video now draws behind the status bar.
  * Remaining problems (user report): overlay bars still look OPAQUE and the
    bottom-most edge is uncertain.

Root causes found by deep smali exploration (E-1/E-3 subagents + orchestrator
verification against the raw opcodes of the exact base decode):

  1. TOP overlay opacity is BY DESIGN in native EEr mode: X/2Iv.A03() builds
     the action-bar background as a black GradientDrawable with **alpha 0.6**
     (const-wide 0x3fe3333333333333L in A03, EEr==true branch). That scrim is
     fed into 0jS.A1K (Reels-tab action bar), the legacy ClipsViewerActionBar
     (feed path, via 2LO.A00) and the GeW re-apply path. 60% black over video
     reads as nearly opaque. TikTok uses ~20%.
  2. BOTTOM comment bar (ClipsViewerNavigationBar.A00): whenever ANY of the 5
     A8e state floats is > 0, the bar paints the drawable
     clips_viewer_action_bar_gradient_background (0x7f08042b) — a strong black
     gradient strip across the bottom. The all-zero path already yields
     setBackground(null) = transparent.
  3. THE HELPER WAS CRASHING ON-DEVICE (user's logcat, logOfInstaTrueReel.txt):
     TTrueReelHelper.A00 threw NoSuchMethodError on every Reels entry because the
     smali referenced Landroid/view/Window$LayoutParams; — a NONEXISTENT framework
     class. The real type is Landroid/view/WindowManager$LayoutParams;. This
     explains v0.3's "no toast" + "nav bar still black at the bottom" while the
     EEr()=true patch (native path) still fixed the top. FIXED in v0.4 (8 sites).
  4. NOTE (explored, then intentionally NOT patched): the 2Iv.APx A1g==true
     branch actually sets the bar background to bds_transparent (E-3 initially
     misread the opcode order; direct reading shows 0bF.A04(ctx)->v5->A03:I
     while A01(I) receives bds_transparent) — so A1g needs no patch. The
     9Wz@6135 v99 QE->2IW.A0I consumer turned out to be a TextView text-size
     tweak — also intentionally skipped. The 9Wz@61725 ModalActivity lOn
     bottom-pad gate is left server-false ON PURPOSE: enabling it would PAD
     the root up by the nav-bar inset and BREAK bottom full-bleed.

Patches applied to the decoded smali tree (all idempotent, fail loudly):

  v0.3 (kept):
    1. X/9Wz.EEr()Z -> FORCED TRUE (native edge-to-edge reels master switch).
    2. X/TTrueReelHelper + X/TTrueReelReapply installed (window apply/restore,
       activity-scoped interceptors, per-entry toast + logcat, re-apply engine).
    3. ClipsViewerFragment (X/9Wz) + ClipsTabFragment (X/AFt) lifecycle hooks.
    4. X/1fC.A04(Activity,I) status-bar color interceptor (transparent while
       Reels active — defeats every repaint incl. Choreographer-deferred).
    5. X/1fI.A04(Activity,I) navigation-bar color interceptor (same pattern).

  v0.4 (NEW — TikTok-style overlays):
    6. X/2Iv.A03(): top scrim alpha 0.6 -> 0.2 (const-wide
       0x3fe3333333333333L -> 0x3fc999999999999aL). One edit covers ALL top
       bars: Reels-tab action bar, feed-path legacy bar, GeW re-apply.
    7. ClipsViewerNavigationBar.A00(): :cond_e now yields a null background
       (transparent bottom comment bar, TikTok-style floating row) instead of
       the 0x7f08042b gradient strip.
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
REELS_DELEGATE = os.path.join(DECODED, "smali_classes17", "X", "2Iv.smali")
NAVBAR_CLASS = os.path.join(
    DECODED, "smali_classes10", "instagram", "features", "clips", "viewer",
    "navigationbar", "ClipsViewerNavigationBar.smali",
)

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

# ---- v0.4 patch 6: top scrim alpha 0.6 -> 0.2 in 2Iv.A03() ----
# The literal is unique in the file (verified against the exact base decode).
SCRIM_OLD_RE = re.compile(r"const-wide v4, 0x3fe3333333333333L[^\n]*\n")
SCRIM_NEW = (
    "const-wide v4, 0x3fc999999999999aL    "
    "# instatruereel: 0.2 TikTok-style scrim (was 0.6)\n"
)
SCRIM_MARKER = "instatruereel: 0.2 TikTok-style scrim"

# ---- v0.4 patch 7: bottom comment bar always transparent ----
# :cond_e currently paints drawable 0x7f08042b; we make it produce null.
NAVBAR_OLD_RE = re.compile(
    r"    :cond_e\n"
    r"    const v0, 0x7f08042b\n"
    r"\n"
    r"    invoke-virtual \{v7, v0\}, Landroid/content/Context;->getDrawable\(I\)Landroid/graphics/drawable/Drawable;\n"
    r"\n"
    r"    move-result-object v0\n"
    r"\n"
    r"    goto/16 :goto_0\n"
)
NAVBAR_NEW = (
    "    :cond_e\n"
    "    # instatruereel: bottom comment bar always transparent (TikTok-style)\n"
    "    const/4 v0, 0x0\n"
    "\n"
    "    goto/16 :goto_0\n"
)
NAVBAR_MARKER = "instatruereel: bottom comment bar always transparent"

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


def replace_unique(content, regex, replacement, marker, label):
    """Replace exactly ONE occurrence of a regex. Idempotent via marker."""
    if marker in content:
        report.append(f"  [skip] {label}: already patched")
        return content
    matches = regex.findall(content)
    if len(matches) != 1:
        errors.append(f"{label}: expected exactly 1 match, found {len(matches)}")
        return content
    new, n = regex.subn(replacement, content, count=1)
    if n != 1:
        errors.append(f"{label}: substitution failed")
        return content
    report.append(f"  [ ok ] {label}: patched")
    return new


def main():
    # ---------- sanity: targets exist ----------
    for path in (CLIPS_VIEWER, CLIPS_TAB, WINDOW_CHROME, NAV_CHROME,
                 REELS_DELEGATE, NAVBAR_CLASS):
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

    # ---------- 7. v0.4: top scrim alpha 0.6 -> 0.2 (X/2Iv.A03) ----------
    report.append("Reels delegate top scrim (X/2Iv.A03):")
    src = read(REELS_DELEGATE)

    if ".method private final A03()Landroid/graphics/drawable/Drawable;" not in src:
        errors.append("2Iv: A03() method not found (version drift?)")
    if "EEr()Z" not in src:
        errors.append("2Iv: EEr() call not found (version drift?)")

    src = replace_unique(src, SCRIM_OLD_RE, SCRIM_NEW, SCRIM_MARKER, "2Iv.A03 scrim 0.6 -> 0.2")
    write(REELS_DELEGATE, src)

    # ---------- 8. v0.4: bottom comment bar transparent ----------
    report.append("Bottom comment bar (ClipsViewerNavigationBar.A00):")
    src = read(NAVBAR_CLASS)

    if ".super Landroid/widget/LinearLayout;" not in src:
        errors.append("ClipsViewerNavigationBar: unexpected superclass (expected LinearLayout)")
    if ".method public static final A00(Linstagram/features/clips/viewer/navigationbar/ClipsViewerNavigationBar;LX/A8e;)V" not in src:
        errors.append("ClipsViewerNavigationBar: A00 method not found (version drift?)")

    src = replace_unique(src, NAVBAR_OLD_RE, NAVBAR_NEW, NAVBAR_MARKER, "navbar cond_e -> null background")
    write(NAVBAR_CLASS, src)

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
        (HELPER_DST, 'const-string v1, "InstaTrueReel v0.4: TikTok-style Reels ON"', "toast marker v0.4 present"),
        (REAPPLY_DST, ".implements Ljava/lang/Runnable;", "reapply runnable present"),
        (REELS_DELEGATE, SCRIM_MARKER, "2Iv top scrim 0.2 marker present"),
        (REELS_DELEGATE, "0x3fc999999999999aL", "2Iv top scrim 0.2 literal present"),
        (NAVBAR_CLASS, NAVBAR_MARKER, "navbar transparent marker present"),
    ]
    for path, needle, label in checks:
        if needle in read(path):
            report.append(f"  [ ok ] {label}")
        else:
            report.append(f"  [FAIL] {label}")
            errors.append(f"verification failed: {label}")

    # negative check: opaque gradient const must be GONE from the navbar
    if "0x7f08042b" in read(NAVBAR_CLASS):
        report.append("  [FAIL] navbar opaque gradient const still present")
        errors.append("verification failed: navbar 0x7f08042b still present")
    else:
        report.append("  [ ok ] navbar opaque gradient const removed")

    finish()


def finish():
    print("InstaTrueReel patch report (v4)")
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
    print()
    print("v0.4 = v0.3 (EEr=true + interceptors + helper) + TikTok-style overlays:")
    print("  - top action-bar scrim 0.6 -> 0.2 alpha (2Iv.A03)")
    print("  - bottom comment bar fully transparent (ClipsViewerNavigationBar.A00)")


if __name__ == "__main__":
    main()
