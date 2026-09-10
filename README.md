# InstaTrueReel

**Immersive True 9:16 Reel Experience** — makes Instagram Reels play TikTok-style:
full-bleed edge-to-edge video under a transparent status bar, transparent nav bar,
floating UI. Built entirely with GitHub Actions (decompile → smali patch → rebuild → sign).

## 📦 Downloads

| Release | APK | What |
|---|---|---|
| [v0.1.0-phase1](https://github.com/Skyro7777777/InstaTrueReel/releases/tag/v0.1.0-phase1) | `Instagram-v435.0.0.37.76-InstaTrueReel-signed.apk` | Edge-to-edge reels: video under transparent status bar, true full-height 9:16 |

### Install

1. **Uninstall** your current Instagram build first (this APK is signed with the InstaTrueReel key —
   it cannot update over other signatures).
2. Download the APK from the release page on your phone and install it (allow "unknown sources").
3. Log in → open **Reels** → the video now plays under the status bar (no black strip), full height,
   with transparent system bars, like TikTok.

### What Phase 1 changes

- Entering Reels: window goes **edge-to-edge** — transparent status bar (white icons over the video),
  transparent navigation bar, `LAYOUT_FULLSCREEN | LAYOUT_STABLE | LAYOUT_HIDE_NAVIGATION`,
  cutout `SHORT_EDGES`, contrast scrims off (API 29+).
- Reel video therefore renders at **true full-screen 9:16** (on a 9:16 display = pixel-perfect).
- Leaving Reels (tab switch / close / pause): original window state is restored — feed, stories,
  DMs etc. keep their normal look.
- Works on Android 10 (tested target); also compatible with newer Androids (legacy window flags
  are translated by the platform).

### Reporting issues / Phase 2 feedback

Open an issue on this repo with:
- Phone model + Android version + nav mode (gesture / 3-button)
- What looks off: e.g. "Reels top bar overlaps the clock", "feed also went edge-to-edge",
  "comment box sits too low/high", "video doesn't fill the screen"
- Screenshot if possible

## 🔧 How it works (technical)

- Base APK: `Instagram-v435.0.0.37.76-patches-v3.8.0.apk` (251 MB, stored in Git LFS).
- Reels viewer identified as `X/9Wz` (`ClipsViewerFragment`) and reels tab as `X/AFt`
  (`ClipsTabFragment`) via Redex `__redex_internal_original_name` metadata.
- New smali class `X/TTrueReelHelper` saves/restores window state and applies the edge-to-edge
  configuration; hooks are injected into `onResume` / `onPause` / `onDestroyView` /
  `onHiddenChanged` of both fragments. All injections use `invoke-static/range {p0 .. p0}`
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
  apply_patches.py            # idempotent smali patcher (verified, marker-commented)
  helper_TTrueReelHelper.smali# window edge-to-edge helper class (smali)
signing/
  instatruereel.jks           # dedicated mod signing key (RSA-4096, PKCS12)
scripts/
  analyze.sh                  # grep battery used by AnalyzeSmali.yml
docs/
  ROADMAP.md                  # living plan + verified findings
```
