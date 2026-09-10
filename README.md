# InstaTrueReel

**Immersive True 9:16 Reel Experience** — makes Instagram Reels play TikTok-style:
full-bleed edge-to-edge video under a transparent status bar, transparent nav bar,
floating UI. Built entirely with GitHub Actions (decompile → smali patch → rebuild → sign).

## 📦 Downloads

| Release | APK | What |
|---|---|---|
| [v0.2.0-phase1.1](https://github.com/Skyro7777777/InstaTrueReel/releases/tag/v0.2.0-phase1.1) | `Instagram-v435.0.0.37.76-InstaTrueReel-signed.apk` | Robust edge-to-edge reels (window-chrome interceptors + re-apply engine + toast marker) |
| [v0.1.0-phase1](https://github.com/Skyro7777777/InstaTrueReel/releases/tag/v0.1.0-phase1) | `Instagram-v435.0.0.37.76-InstaTrueReel-signed.apk` | Initial edge-to-edge reels (superseded — IG could repaint the bar after resume) |

> **Always grab the newest release.** v0.1.0 could be silently reverted by Instagram's
> own status-bar repaints; v0.2.0 intercepts them.

### Install

1. **Uninstall** your current Instagram build first (this APK is signed with the InstaTrueReel key —
   it cannot update over other signatures).
2. Download the APK from the release page on your phone and install it (allow "unknown sources").
3. Log in → open **Reels**.

### Do I need to enable anything in Piko settings / developer options?

**No.** Nothing is toggled from Piko settings or the hidden developer options — those belong to
the base patched APK and are unrelated to InstaTrueReel. The mod is **fully automatic**:
it activates the moment you enter Reels (tab or feed reel) and deactivates when you leave.

**How to confirm you're running the patched build:** the first time you open Reels after
installing/launching the app, a toast appears:

```
InstaTrueReel v0.2: true 9:16 Reels ON
```

- **Toast shows + no black strip** → working.
- **Toast shows + still a black strip behind the status bar** → the window chrome is being
  handled by a path we haven't intercepted yet — please open an issue (see below).
- **No toast at all** → you are not running this build (old APK still installed, or install
  failed with a signature mismatch — uninstall Instagram fully, then install again).

### What Phase 1.1 changes

- Entering Reels (tab **or** reel from feed): window goes **edge-to-edge** — status bar fully
  transparent (white icons over the video), transparent navigation bar,
  `LAYOUT_FULLSCREEN | LAYOUT_STABLE | LAYOUT_HIDE_NAVIGATION`, cutout `SHORT_EDGES`,
  contrast scrims off (API 29+).
- Instagram's own status-bar controller (`X/1fC`) is **intercepted while Reels is showing**:
  every attempt to repaint the status bar color is forced to fully transparent, and every
  attempt to enter fullscreen-hide is forced to the "bar visible" branch. This defeats
  Instagram's Choreographer-deferred chrome writes that reverted Phase 1.
- A delayed re-apply engine re-asserts the edge-to-edge state at 100 / 400 / 1000 / 2500 ms
  after entering Reels, so late writes (theme changes, React surface config, dialogs) lose.
- Reel video therefore renders at **true full-screen 9:16** (on a 9:16 display = pixel-perfect).
- Leaving Reels (tab switch / close / pause): interceptors deactivate and the original window
  state is restored — feed, stories, DMs etc. keep their normal look.
- Works on Android 10 (tested target); also compatible with newer Androids (legacy window flags
  are translated by the platform).

### Reporting issues / Phase 2 feedback

Open an issue on this repo with:
- Phone model + Android version + nav mode (gesture / 3-button)
- Whether the **toast** appeared when entering Reels
- What looks off: e.g. "Reels top bar overlaps the clock", "feed also went edge-to-edge",
  "comment box sits too low/high", "video doesn't fill the screen"
- Screenshot if possible

## 🔧 How it works (technical)

- Base APK: `Instagram-v435.0.0.37.76-patches-v3.8.0.apk` (251 MB, stored in Git LFS).
- Reels viewer identified as `X/9Wz` (`ClipsViewerFragment`) and reels tab as `X/AFt`
  (`ClipsTabFragment`) via Redex `__redex_internal_original_name` metadata.
- New smali classes `X/TTrueReelHelper` (window state machine + interceptors) and
  `X/TTrueReelReapply` (scheduled re-apply Runnable); hooks are injected into
  `onResume` / `onPause` / `onDestroyView` / `onHiddenChanged` of both fragments.
- `X/1fC` is Instagram's window-chrome controller (`A04` = status bar color with a
  Choreographer-deferred write path, `A06` = fullscreen toggle). Both are intercepted at
  method entry with activity/window-scoped guards, active only while Reels is showing.
- All injections use `invoke-static/range {p0 .. p0}` where register indices may exceed 15
  (35c register limit safe) and are idempotent (marker comments).
- Instagram's layout resources in this build are in compressed-blob format (`L|offset|len|hash`),
  so patches are **pure smali** — resources and manifest are passed through untouched.

### Workflows

| Workflow | Purpose |
|---|---|
| `AnalyzeSmali.yml` | apktool decode (-r) + grep battery + full smali artifact for offline analysis |
| `BuildPatchedApk.yml` | decode → `patches/apply_patches.py` → apktool build → zipalign → apksigner |

Run them from the **Actions** tab (workflow_dispatch).

### Repo layout

```
patches/
  apply_patches.py             # idempotent smali patcher v2 (16 verification checks)
  helper_TTrueReelHelper.smali # window edge-to-edge helper + interceptors (smali)
  helper_TTrueReelReapply.smali# scheduled re-apply Runnable (smali)
signing/
  instatruereel.jks            # dedicated mod signing key (RSA-4096, PKCS12)
scripts/
  analyze.sh                   # grep battery used by AnalyzeSmali.yml
docs/
  ROADMAP.md                   # living plan + verified findings
```
