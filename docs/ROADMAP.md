# InstaTrueReel — Living Plan

Goal: Make Instagram Reels play **TikTok-style** on the user's device (Android 10, 9:16 display):

1. **True 9:16 / edge-to-edge media**: reel video drawn *under* the status bar (no black strip).
2. **Transparent status bar** (white icons overlay the video, like TikTok).
3. **Transparent nav bar / floating UI**: overlay UI floats above full-bleed media instead of shrinking it.
4. Keep everything else working (login, feed, stories, comments…).

Base APK: `Instagram-v435.0.0.37.76-patches-v3.8.0.apk` (251 MB, Git LFS, already third-party-patched once).

## Pipeline (all heavy work in GitHub Actions)

| Stage | Workflow | Status |
|---|---|---|
| jadx decompile (readable Java, deobf) | `DeCompileTheApk.yml` | ✅ done (run 34439742856) |
| apktool smali decode + grep battery | `AnalyzeSmali.yml` | ✅ done (run 34451536246) |
| patch + rebuild + sign APK | `BuildPatchedApk.yml` | ✅ v0.1.0-phase1 (run 34455447077) → ✅ v0.2.0-phase1.1 (run 34472181694) |

## Field test of v0.1.0 (user device, Android 10) + root-cause analysis

User report: entering Reels (tab + feed reel) → **no visible change**; black strip behind the
status bar remains. Deep-dive into the smali found the actual window-chrome machinery:

- **`X/1fC` = Instagram's central window-chrome controller** (Kotlin object):
  - `A04(Activity, color)` — the status-bar color setter, **with a Choreographer-deferred write
    path** (`WindowChromeColorDeferer`, `X/9wE` + `X/ktp` frame callback). Colors can land a
    frame (or more) AFTER a fragment's `onResume` — silently reverting any flags we set there.
  - `A06(View, Window, boolean)` — fullscreen toggle (`true` = show bar, `false` =
    FLAG_FULLSCREEN + SYSTEM_UI_FLAG_FULLSCREEN hide).
  - `A05/A07` — icon appearance helpers.
- **`InstagramMainActivity` already sets `systemUiVisibility(0x700)`** on the decor in its
  startup path (`A0h`/`A0i`) — the window is already laid out edge-to-edge-capable; the black
  strip the user sees is the **opaque `statusBarColor` scrim painted over the top of the
  content** by `1fC.A04` writes (theme black + deferred repaints).
- Phase-1 helper bug: `layoutInDisplayCutoutMode` was set to **2 = NEVER** instead of 1 =
  SHORT_EDGES (cosmetic on non-notch devices but wrong).
- Conclusion: Phase-1's single onResume apply could be (and was) overwritten after the fact.
  Fix = intercept the repaints themselves, not just apply once.

## Patch design (Phase 1.1 — SHIPPED in patches/, release v0.2.0-phase1.1)

`X/TTrueReelHelper` v2 (smali_classes16) — fields: saved window/activity/state, `A05` ACTIVE
flag, toast-shown flag, scheduler Handler + Runnable:

- `A00(Fragment)` APPLY — saves state once, applies edge-to-edge core, sets ACTIVE, shows a
  **one-time toast** ("InstaTrueReel v0.2: true 9:16 Reels ON") so users can verify the build,
  and schedules the re-apply engine.
- `A01(Fragment)` RESTORE — deactivates interceptors FIRST, cancels scheduled re-applies,
  restores saved window state.
- `A02(Fragment, hidden)` — onHiddenChanged bridge.
- `A03(Activity, color)I` — **interceptor**: while ACTIVE and activity == saved activity →
  returns 0x00000000 (fully transparent). Injected at the top of `1fC.A04` — defeats every
  status-bar repaint, deferred or not, scoped to Reels' own activity.
- `A04(Window, boolean)Z` — **interceptor**: while ACTIVE and window == saved window → returns
  true ("keep bar visible"). Injected at the top of `1fC.A06` — Instagram can never hide the
  status bar while Reels is showing (TikTok keeps it visible too).
- `A05()V` — schedules `X/TTrueReelReapply` at 100 / 400 / 1000 / 2500 ms (main Handler);
  cancels + re-targets on each apply; cancelled on restore.
- `A06(Window)V` — idempotent reapply core: 0x700 layout flags, white icons, transparent bars,
  SHORT_EDGES cutout (**fixed from NEVER**), contrast off, `requestApplyInsets()`.

Hooks (injected by `patches/apply_patches.py` v2, idempotent, marker-commented):

| Class | Method | Effect |
|---|---|---|
| X/9Wz (ClipsViewerFragment) | `onResume` | apply |
| X/9Wz | `onPause` | restore |
| X/9Wz | `onDestroyView` | restore |
| X/9Wz | `onHiddenChanged` (added override) | bridge |
| X/AFt (ClipsTabFragment) | `onResume` | apply |
| X/AFt | `onPause` (added override) | restore |
| X/AFt | `onDestroyView` | restore |
| X/AFt | `onHiddenChanged` (added override) | bridge |
| **X/1fC (window-chrome controller)** | `A04(Activity,I)` | color → transparent while Reels active |
| **X/1fC** | `A06(View,Window,Z)` | never hide status bar while Reels active |

Injected calls use `invoke-static/range {p0 .. p0}` where needed (35c limit); interceptor calls
use plain `invoke-static` (low register indices in 1fC methods). **Invoke arity is verified by
local baksmali round-trip** — an arity bug (`{p1}` vs a 2-arg method) assembles silently and
would crash at runtime with VerifyError; always round-trip check.

## Verified technical findings (raw smali = ground truth)

- Reels viewer = **`X/9Wz`** (`__redex_internal_original_name = "ClipsViewerFragment"`), in
  `smali_classes16`, extends `X/2yN` ("IgFragment") → `X/2Tg` → androidx Fragment.
- Reels tab host = **`X/AFt`** ("ClipsTabFragment"), also in `smali_classes16`, hosts a
  ViewPager2 whose child is the ClipsViewerFragment.
- `X.ked` / `X.2Ib` / `X.0Vv` are Instagram's own edge-to-edge/window helpers:
  - `0Vv.A00(window,false)` on API<30 = `systemUiVisibility |= 0x700`
    (LAYOUT_STABLE | LAYOUT_FULLSCREEN | LAYOUT_HIDE_NAVIGATION) — the TikTok-style window layout.
- `X.PNB` = Android-15 edge-to-edge enforcement shim (content padding + scrims) — only active
  on API 35+; NOT the cause of the black strip on Android 10.
- On Android 10 the "black strip + shrunken reel" = window-level: `decorFits=true`
  (default) + opaque black `statusBarColor` from theme. The clips fragment content simply
  fills the window content area below the status bar.
- Clips viewer fragment inflates `layout_clips_viewer_fragment` = compressed-blob layout
  ("L|offset|len|hash" resource format) → **resource XML patching is not possible**;
  all patches are pure smali.
- `X/fit` (gesture bottom padding) and `X/lOn`/`X/lOz` (top/bottom inset padding) are only
  attached in special paths (tablet / fullscreen-config / ModalActivity) — the normal phone
  reels path applies no insets itself; the fragment content would extend edge-to-edge
  automatically once the window is patched.

## Signing

`signing/instatruereel.jks` (PKCS12, RSA-4096, 30y) — dedicated mod key committed to the repo.
Signed with apksigner (v1+v2+v3). Installing over the previous third-party-patched build
requires uninstall first (signature change). **Never install over the official Instagram.**

## Known risks / follow-ups (Phase 2 candidates)

1. If the main tab host uses neither pause nor hide for tab fragments, the edge-to-edge state
   could leak to the main feed (cosmetic, not fatal). Fix: add restore-guards to home/search/
   profile tab fragments (`X/6Tt` HomeTabFragment, `X/1gE` MainFeedFragment, …).
2. Reels top bar (camera/search row) may sit very close to / overlap the status bar icons;
   TikTok offsets its top chrome by the status bar inset. If needed: add top-margin patch for
   the action bar container in the clips viewer (`instagram/features/clips/viewer/actionbar/`).
3. Comment sheet / reply bar inside reels may need bottom-inset tweaks while window is
   edge-to-edge (`ClipsViewerNavigationBar` = the bottom comment bar).
4. Status-bar icon color is forced light (white) in reels — matches TikTok over video.
5. Base APK is "patches-v3.8.0" (unknown third-party patcher; not InstaEclipse-the-Xposed-module
   — that ships v0.x). Patcher identity TBD; our patches are layered on top regardless.

---

# Phase 2 — v0.3.0 (NATIVE EDGE-TO-EDGE) — the real fix

## Field test of v0.2.0 (user device, Android 10)

User report: still **no change** and — critically — **no toast**. The v0.2 release artifact
was re-verified (helper class + toast string present in shipped dex), so the patched code
never executed on the device. Most likely cause: **signature-mismatch install failure** —
the user still had the base Piko APK (or v0.1.0) installed; Android silently refuses
"different signature" upgrades, leaving the old app running. v0.3 therefore: (a) shows the
toast on **every** Reels entry with the version string, (b) logs to logcat
(`adb logcat -s InstaTrueReel`), (c) README install section rewritten around the
uninstall-first requirement.

## Deep exploration (this phase) — the actual root cause of the black strip

Four parallel investigations (R-1 web research; E-1/E-2/E-4 smali deep-dives; local layout
decoding) converged on one mechanism:

- **`X/9Wz.EEr()Z` is Instagram's own edge-to-edge Reels master switch:**
  `EEr() = !ClipsViewerConfig.A2g && (A3H || QE flag BHQ(0x8109d400023873))`
  (server-config / Quick-Experiment gated — off for the user's account/device).
- `EEr()==false` → `X/2Iv` (reels delegate, classes17) feeds **`bds_black` (0x7f060052)**
  into `0jS.A1K → 1fC.A03 → 1fC.A04` → **opaque status-bar scrim = the black strip.**
- `EEr()==true` → `bds_transparent` (0x7f0600a9) + `2Iv.A0A()` registers a `6BM` insets
  listener on `8ug` (WindowInsetsManager) → `Fji(statusH, navH)` → `0jS.A15(statusBarHeight)`
  **pads the action-bar top containers by status-bar height** (TikTok-style self-padding
  overlays) and sets `0jS.A0D=true` so every activity resume repaints transparent.
- **The media container was already full-bleed all along**: decoded
  `layout_clips_viewer_fragment` (res/3da.xml, mapped from 0x7f0e0a4c via resources.arsc):
  root ConstraintLayout `match_parent × match_parent`, inner **ViewPager2 (0x7F0B3F45)
  `match_parent × match_parent`**, zero `fitsSystemWindows`. The window already runs
  `0x700` flags (MainActivity `A0h`/`A0i`). Only the opaque bar color hides the video.
- Both entry points funnel through the same switch: the Reels **tab** (`AFt.EEr()`)
  delegates to its child `9Wz` (interface `X/3Cz`); the **viewer** calls `9Wz.EEr()` directly.
  EEr's boolean also flows into the viewer item binders (`ACN → ACO.A0w → I45/XXz`).
- Dead code found: `1fC.A06` has **zero callers** in v435 (full-tree scan) — the v0.2
  interceptor on it was harmless but useless. Removed in v0.3.
- Gap found: navigation bar color flows through a twin writer `1fI.A04` (same deferred
  engine) — v0.2 left the bottom strip black. v0.3 intercepts it.
- R-1 research: base APK = **crimera/piko v3.8.0 applied via Morphe Manager** (static smali
  patcher, ReVanced-style — NOT LSPatch; our dex edits are live code). Piko settings =
  gear icon on feed top bar; "developer options" = **long-press home icon** (Instagram-native
  QE menu unlocked by Piko). Neither has any edge-to-edge option; no competing solution
  exists anywhere — InstaTrueReel is first.

## v0.3.0 patch set (SHIPPED)

1. **`9Wz.EEr()Z` → forced `true`** (method body replaced with `const/4 v0,0x1; return v0`)
   — turns on Instagram's own, fully-engineered edge-to-edge Reels mode.
2. `1fC.A04` color interceptor kept (transparent while Reels active — defeats all repaint
   paths incl. Choreographer-deferred writes).
3. **`1fI.A04` nav-bar interceptor added** (same pattern; bottom strip now transparent too).
4. `1fC.A06` interceptor dropped (dead code).
5. Fragment lifecycle hooks kept (scoping for interceptors + restore-on-exit).
6. Toast on **every fresh Reels entry** ("InstaTrueReel v0.3: true 9:16 Reels ON") +
   logcat markers (`InstaTrueReel` tag) + per-entry `Log.e` breadcrumbs.
7. Workflow: added "Verify patches are inside the final APK" step (string checks on the
   signed APK's dexes) + patch report artifact.

Pre-flight validation (local): full patch → `apktool b` assembly → jadx round-trip confirmed
`EEr() { return true; }` and `1fC.A04`/`1fI.A04` calling `TTrueReelHelper.A03/A07` first,
before the parent-climb and both write branches.

## Next (Phase 3 candidates — only if user reports residual issues)

- Comment sheet / bottom overlays inset tuning (if the comment bar overlaps the nav area).
- Top overlay ("Reels" header) offset polish if status-bar-height padding looks off.
- Non-9:16 reel letterboxing (fit vs fill) investigation if user reports pillarboxing.
- Optional Piko-settings-style toggle UI (out of scope unless requested).

---

# Phase 3 — v0.4.0 (TIKTOK-STYLE OVERLAYS)

## Field test of v0.3.0 (user device, Android 10, 9:16)

User report: reel video NOW stretches to the uppermost part of the screen and draws
behind the status bar — the EEr()=true patch is confirmed ACTIVE on-device. Remaining
problems: (a) the overlay bars did not become transparent ("any of the UI didn't became
transparent"), (b) the bottom-most edge is possibly not full-bleed. (Toast: user did not
focus on it; adb logcat file was captured but never reached the sandbox upload folder —
runtime confirmation of helper execution still pending.)

## Deep exploration (this phase) — subagent-driven, ground-truth smali

Three exploration subagents (E-1: top overlay; E-2: bottom overlay — hit turn limit,
re-done by orchestrator directly; E-3: complete EEr consumer map) ran against the
jadx Java artifact (44.8 MB, 90k files) and the FULL apktool smali decode (183 MB
artifact from the AnalyzeSmali run — the jadx artifact turned out to be missing 95%
of the ClipsViewerSource cluster, smali is the ground truth). Orchestrator then
re-verified every claim against the raw opcodes.

Key findings:

1. **EEr()==true top overlay is a 60%-alpha black gradient BY DESIGN.**
   `X/2Iv.A03()` (classes17) — the scrim provider — calls
   `34d.A01(ctx, TOP_BOTTOM, null, 0.6)` in the EEr==true branch (unique const-wide
   `0x3fe3333333333333L`). This scrim is THE action-bar background: it flows into
   `360.A09` -> `35U` -> `0jS.A1K` (Reels tab), into the legacy
   `ClipsViewerActionBar` (feed path, via `2LO.A00 = A03()`), and into the GeW
   re-apply. 60% black over video reads as near-opaque. TikTok uses ~20%.
2. **The EEr color choice (bds_black vs bds_transparent) is the STATUS BAR color**
   (`0jS.A1K -> 1fC.A03 -> 1fC.A04`), NOT the bar background. This corrects the
   v0.3 assumption in this document.
3. **Bottom comment bar:** `ClipsViewerNavigationBar.A00(bar, A8e-state)` — if ANY
   of the 5 A8e floats > 0 -> background = drawable `clips_viewer_action_bar_
   gradient_background` (0x7f08042b, strong black gradient strip). All-zero ->
   `setBackground(null)` (transparent). The gradient path is what the user sees.
4. **2Iv.APx has TWO theme builders** (tab path via source.A0C()==true; feed path
   otherwise). The feed-path `A1g==true` branch sets the bar bg to
   **bds_transparent** (ColorDrawable) — ALREADY transparent; E-3 initially misread
   the opcode order (0bF.A04(ctx)->v5 actually lands in `360.A03:I`, while
   `360.A01(I)` receives bds_transparent). => A1g needs NO patch.
5. **9Wz@6135 v99 QE gate -> 2IW ctor bool #56 -> field 2IW.A0I** — consumer found:
   a TextView text-size tweak in 2Iv (~line 14908). Visually irrelevant => NOT patched.
6. **9Wz@61719-61725 ModalActivity QE gate -> `0Ug.A02(root, lOn)`**: lOn = one-shot
   root BOTTOM pad by the nav-bar inset (type 0x207). Forcing it TRUE would PAD THE
   ROOT UP and BREAK bottom full-bleed => deliberately left server-false.
7. **9Wz.onViewCreated @61687-61695**: `A2C==true` pads root bottom by
   `tab_bar_height_panorama` (0x7f070254). A2C is server config; left alone for now
   (revisit only if user still reports a bottom gap).
8. EEr also offsets per-item litho content (`I45.A06` @876 pads by statusBarHeight)
   — already active via EEr=true.
9. `0jS.A0D()V` (a METHOD) clears click listeners — unrelated to insets; the `A0D`
   FIELD (set by A15) is the status-bar-padded flag. (Corrects v0.3 notes.)
10. `9Wz.A03:I` (top_of_feed_container top pad) has no writer in the base — stays 0.


## THE LOG (user's adb logcat, committed as logOfInstaTrueReel.txt) — root cause of v0.3's missing pieces

The user captured a full logcat (UTF-16 encoded, 5149 lines) and uploaded it to the repo root.
Decoded and analyzed: **the helper DID run — and crashed twice** (once per Reels entry,
23:14:44 tab path and 23:15:08):

```
E InstaTrueReel: v0.3 apply: exception (recovered)
E InstaTrueReel: java.lang.NoSuchMethodError: No virtual method getAttributes()
  Landroid/view/Window$LayoutParams; in class Landroid/view/Window;
E InstaTrueReel:     at X.TTrueReelHelper.A00(TTrueReelHelper:46)
E InstaTrueReel:     at X.9Wz.onResume(:0)
```

**Helper authoring bug:** the smali referenced `Landroid/view/Window$LayoutParams;`
—a class that does not exist in the Android framework. The real type is
`Landroid/view/WindowManager$LayoutParams;` (what `Window.getAttributes()` actually
returns). The bad descriptor assembled fine (smali does not resolve framework types)
and only failed lazily at first invoke on-device. Consequences:

- apply() died BEFORE the toast (explains "no toast") and BEFORE any window flags were
  set (explains the still-black bottom nav strip — "maybe not stretched up-to downmost").
- ACTIVE was never set -> the 1fC.A04/1fI.A04 interceptors never engaged.
- The visible top improvement came ENTIRELY from the EEr()=true patch (native pipeline
  feeds bds_transparent to the status bar) — consistent with the user's screenshots.
- The try/catch swallowed the error each time; zero successful applies, zero restores.

**Fix (v0.4): all 8 `Window$LayoutParams` references in helper_TTrueReelHelper.smali
corrected to `WindowManager$LayoutParams`.** With the helper alive, v0.4 gains: the
per-entry toast, 0x700 layout flags + transparent nav bar + contrast scrims off +
cutout SHORT_EDGES on the Reels window, ACTIVE-gated color interceptors, and the
100/400/1000/2500 ms re-apply engine — on top of the EEr native mode and the two new
TikTok-style overlay patches.

## v0.4.0 patch set (SHIPPED — updated after log analysis)

1. ALL v0.3 patches kept (EEr forced true; 1fC.A04 + 1fI.A04 color interceptors;
   9Wz/AFt lifecycle hooks; TTrueReelHelper + TTrueReelReapply + toast/logcat).
   **FIX: helper Window$LayoutParams -> WindowManager$LayoutParams (8 sites) — the
   crash found in the user's logcat.**
2. **NEW: `2Iv.A03()` scrim alpha 0.6 -> 0.2** (const-wide
   `0x3fe3333333333333L` -> `0x3fc999999999999aL`, marked
   `# instatruereel: 0.2 TikTok-style scrim`). One edit covers every top bar
   (tab action bar, feed legacy bar, GeW re-apply). TikTok-like legibility gradient.
3. **NEW: `ClipsViewerNavigationBar.A00` `:cond_e` -> null background** (replaces
   the `getDrawable(0x7f08042b)` block with `const/4 v0, 0x0`). The bottom comment
   bar is now always fully transparent — TikTok-style floating row over the video.
4. Helper version strings bumped v0.3 -> v0.4 (toast: "InstaTrueReel v0.4:
   TikTok-style Reels ON").
5. apply_patches.py v4: two new `replace_unique` patches with uniqueness
   pre-checks, method-signature sanity checks, marker/idempotency, a NEGATIVE
   verification (0x7f08042b must be gone), full report.
   Locally validated against the exact base decode (all 22 checks [ ok ],
   idempotent re-run clean).

## Next (Phase 4 candidates — after v0.4 field test)

- Get the user's adb logcat (upload failed to reach the sandbox so far) to confirm
  helper execution, nav-bar transparency writes, and per-path behavior.
- If bottom-most still not full-bleed: investigate A2C / tab_bar_height_panorama
  padding and the nav-bar color write path on the Reels tab (MainActivity).
- If the top bar sits too close to the status bar icons: 0jS.A15 padding polish.
- If legibility suffers at 0.2 alpha: consider 0.25-0.3.
