# InstaTrueReel — Living Plan

Goal: Make Instagram Reels play **TikTok-style** on the user's device (Android 10, 9:16 display):

1. **True 9:16 / edge-to-edge media**: reel video drawn *under* the status bar (no black strip).
2. **Transparent status bar** (icons overlay the video, like TikTok).
3. **Transparent / floating top bar + bottom bar**: UI overlays float above full-bleed media instead of shrinking it.
4. Keep everything else working (login, feed, stories, comments…).

Base APK: `Instagram-v435.0.0.37.76-patches-v3.8.0.apk` (251 MB, Git LFS, already third-party-patched once).

## Pipeline (all heavy work in GitHub Actions)

| Stage | Workflow | Status |
|---|---|---|
| jadx decompile (readable Java, deobf) | `DeCompileTheApk.yml` | ✅ done (run 34439742856) |
| apktool smali decode + grep battery | `AnalyzeSmali.yml` | 🔄 being set up |
| targeted smali patch scripts | `patches/` + `BuildPatchedApk.yml` | ⏳ pending analysis |
| rebuild + zipalign + sign APK | `BuildPatchedApk.yml` | ⏳ pending patches |

## Technical findings so far (deobf jadx pass)

- `X.ked` (smali `X/ked.smali`) — SystemUI helper:
  - `ked.A00(Window)` — near edge-to-edge: transparent status bar, transparent nav bar (API 29+),
    cutout mode ALWAYS (API 30+), translucent nav scrim. Currently only used by a React dialog path.
  - `ked.A02(Window, true)` — legacy immersive: `setDecorFitsSystemWindows(false)` + `FLAG_FULLSCREEN`.
  - `ked.A01(Window, "dark-content")` — light status-bar icons toggle.
- `X.2Ib` — full edge-to-edge helper (`A01`): translucent flag clear + `FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS` +
  `setDecorFitsSystemWindows(false)` + fully transparent status & nav bars.
- androidx `WindowInsetsCompat` backport present (`X.0Wu` etc.) — generic.
- Reels surface = "ClipsViewer"; reel media container view id: `reel_viewer_media_container`.
- User-visible problem on Android 10: main window keeps `decorFits=true` + black status bar color → reels
  feed starts below status bar → perceived shrink/black strip.

## Patch strategy (hypothesis — refine after smali analysis)

P1. **Window-level edge-to-edge for the reels surface**: force the hosting Activity/Fragment window into
    `ked`-style edge-to-edge (transparent status bar + `setDecorFitsSystemWindows(false)` on API 30+ /
    legacy `FLAG_LAYOUT_NO_LIMITS`/`FLAG_FULLSCREEN`-equivalent flags for Android 10 user).
P2. **Remove insets padding/margin from the reels media container** so the pager/media view spans the full
    screen height (insets listener or programmatic padding — find exact site in smali).
P3. **Keep overlay UI usable**: top bar / bottom bar / comment sheet should get manual inset offsets so
    icons don't collide with system bars (TikTok-style). Prefer Instagram's own inset-aware overlay logic
    if present; otherwise add offsets.
P4. Re-sign the patched APK with a dedicated keystore (committed to repo) for stable updates.

## Open questions

- Which Activity hosts the reels viewer in v435? (find raw smali class)
- Does the reels container get insets via code (`setOnApplyWindowInsetsListener`) or XML (`fitsSystemWindows`/padding)?
- Which "patches-v3.8.0" patches are already in the base APK (patcher identity TBD via APK inspection)?
- Status bar icon color handling in reels (light icons on video? Instagram may already toggle per-frame).
