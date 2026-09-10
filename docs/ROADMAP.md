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
| patch + rebuild + sign APK | `BuildPatchedApk.yml` | 🔄 first run dispatched |

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

## Patch design (Phase 1 — SHIPPED in patches/)

New helper class `X/TTrueReelHelper` (smali_classes16):

- `A00(Fragment)` APPLY — saves window state then applies TikTok-style edge-to-edge:
  `systemUiVisibility = (saved | 0x700) & ~0x10 & ~0x2000` (layout under bars + white icons),
  transparent status & nav bar colors, clears translucent flags, adds
  FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS, cutout SHORT_EDGES (API 28+), contrast scrims off
  (API 29+), `requestApplyInsets()`. Idempotent; owner-window tracked; all in try/catch.
- `A01(Fragment)` RESTORE — puts back the saved colors/flags/cutout mode.
- `A02(Fragment, hidden)` — onHiddenChanged bridge.

Hooks (injected by `patches/apply_patches.py`, idempotent, marker-commented):

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

Injected calls use `invoke-static/range {p0 .. p0}` because `p0` can be ≥ v16 in methods
with many locals (35c format limit). All patched files verified to assemble with smali 2.5.2.

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
