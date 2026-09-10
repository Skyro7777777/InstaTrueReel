.class public final LX/TTrueReelHelper;
.super Ljava/lang/Object;
.source "TTrueReelHelper"


# static fields
.field public static A00:Landroid/view/Window;      # saved window while reels active
.field public static A01:I                          # saved statusBarColor
.field public static A02:I                          # saved navigationBarColor
.field public static A03:I                          # saved decor systemUiVisibility
.field public static A04:I                          # saved layoutInDisplayCutoutMode (API>=28)
.field public static A05:Z                          # ACTIVE flag (reels showing)
.field public static A07:Landroid/os/Handler;       # re-apply scheduler
.field public static A08:Ljava/lang/Runnable;       # re-apply runnable
.field public static A09:Landroid/app/Activity;     # saved activity (scope for interceptors)


# direct methods

# A00(Landroidx/fragment/app/Fragment;)V == APPLY TikTok-style edge-to-edge to the activity window.
# Saves prior state once, applies transparent-system-bar window chrome, marks ACTIVE,
# shows a confirmation toast on every fresh reels entry (proves patched build is running),
# logs to logcat (tag "InstaTrueReel") and schedules delayed re-applies.
# v0.3: native edge-to-edge is driven by the forced 9Wz.EEr()=true patch; this helper now
# provides scoping (ACTIVE), transparency enforcement and verification.
.method public static A00(Landroidx/fragment/app/Fragment;)V
    .locals 6

    :try_start_0
    sget-object v0, LX/TTrueReelHelper;->A00:Landroid/view/Window;
    if-nez v0, :cond_active

    invoke-virtual {p0}, Landroidx/fragment/app/Fragment;->getActivity()Landroidx/fragment/app/FragmentActivity;
    move-result-object v4
    if-eqz v4, :cond_skip

    invoke-virtual {v4}, Landroid/app/Activity;->getWindow()Landroid/view/Window;
    move-result-object v0
    if-eqz v0, :cond_skip

    invoke-virtual {v0}, Landroid/view/Window;->getDecorView()Landroid/view/View;
    move-result-object v1
    if-eqz v1, :cond_skip

    # ---- save original window state ----
    invoke-virtual {v0}, Landroid/view/Window;->getStatusBarColor()I
    move-result v2
    sput v2, LX/TTrueReelHelper;->A01:I

    invoke-virtual {v0}, Landroid/view/Window;->getNavigationBarColor()I
    move-result v2
    sput v2, LX/TTrueReelHelper;->A02:I

    invoke-virtual {v1}, Landroid/view/View;->getSystemUiVisibility()I
    move-result v2
    sput v2, LX/TTrueReelHelper;->A03:I

    sget v2, Landroid/os/Build$VERSION;->SDK_INT:I
    const/16 v3, 0x1c
    if-lt v2, v3, :cond_skip_save_cutout
    invoke-virtual {v0}, Landroid/view/Window;->getAttributes()Landroid/view/Window$LayoutParams;
    move-result-object v2
    iget v2, v2, Landroid/view/Window$LayoutParams;->layoutInDisplayCutoutMode:I
    sput v2, LX/TTrueReelHelper;->A04:I
    :cond_skip_save_cutout

    sput-object v0, LX/TTrueReelHelper;->A00:Landroid/view/Window;
    sput-object v4, LX/TTrueReelHelper;->A09:Landroid/app/Activity;

    # ---- apply edge-to-edge core ----
    invoke-static {v0}, LX/TTrueReelHelper;->A06(Landroid/view/Window;)V

    # ---- confirmation toast on every fresh reels entry ----
    invoke-virtual {p0}, Landroidx/fragment/app/Fragment;->getActivity()Landroidx/fragment/app/FragmentActivity;
    move-result-object v0
    if-eqz v0, :cond_no_toast
    const-string v1, "InstaTrueReel v0.3: true 9:16 Reels ON"
    const/4 v2, 0x0
    invoke-static {v0, v1, v2}, Landroid/widget/Toast;->makeText(Landroid/content/Context;Ljava/lang/CharSequence;I)Landroid/widget/Toast;
    move-result-object v0
    invoke-virtual {v0}, Landroid/widget/Toast;->show()V
    :cond_no_toast

    const-string v1, "InstaTrueReel"
    const-string v2, "v0.3 apply: edge-to-edge engaged (fresh entry)"
    invoke-static {v1, v2}, Landroid/util/Log;->e(Ljava/lang/String;Ljava/lang/String;)I

    :cond_active
    # ---- mark ACTIVE (enables 1fC/1fI interceptors) ----
    const/4 v0, 0x1
    sput-boolean v0, LX/TTrueReelHelper;->A05:Z

    # ---- schedule delayed re-applies ----
    invoke-static {}, LX/TTrueReelHelper;->A05()V

    :cond_skip
    :try_end_0
    .catch Ljava/lang/Throwable; {:try_start_0 .. :try_end_0} :catch_0

    return-void

    :catch_0
    move-exception v0
    const-string v1, "InstaTrueReel"
    const-string v2, "v0.3 apply: exception (recovered)"
    invoke-static {v1, v2, v0}, Landroid/util/Log;->e(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I
    const/4 v1, 0x0
    sput-object v1, LX/TTrueReelHelper;->A00:Landroid/view/Window;
    return-void
.end method


# A01(Landroidx/fragment/app/Fragment;)V == RESTORE original window state
.method public static A01(Landroidx/fragment/app/Fragment;)V
    .locals 4

    :try_start_0
    # ---- deactivate interceptors FIRST ----
    const/4 v0, 0x0
    sput-boolean v0, LX/TTrueReelHelper;->A05:Z

    # ---- cancel pending re-applies ----
    sget-object v0, LX/TTrueReelHelper;->A07:Landroid/os/Handler;
    if-eqz v0, :cond_no_cancel
    sget-object v1, LX/TTrueReelHelper;->A08:Ljava/lang/Runnable;
    if-eqz v1, :cond_no_cancel
    invoke-virtual {v0, v1}, Landroid/os/Handler;->removeCallbacks(Ljava/lang/Runnable;)V
    :cond_no_cancel

    # ---- drop runnable window ref ----
    sget-object v1, LX/TTrueReelHelper;->A08:Ljava/lang/Runnable;
    if-eqz v1, :cond_no_clear
    check-cast v1, LX/TTrueReelReapply;
    const/4 v2, 0x0
    iput-object v2, v1, LX/TTrueReelReapply;->A00:Landroid/view/Window;
    :cond_no_clear

    sget-object v0, LX/TTrueReelHelper;->A00:Landroid/view/Window;
    if-eqz v0, :cond_done

    invoke-virtual {v0}, Landroid/view/Window;->getDecorView()Landroid/view/View;
    move-result-object v1
    if-eqz v1, :cond_reset

    sget v2, LX/TTrueReelHelper;->A03:I
    invoke-virtual {v1, v2}, Landroid/view/View;->setSystemUiVisibility(I)V

    sget v2, LX/TTrueReelHelper;->A01:I
    invoke-virtual {v0, v2}, Landroid/view/Window;->setStatusBarColor(I)V

    sget v2, LX/TTrueReelHelper;->A02:I
    invoke-virtual {v0, v2}, Landroid/view/Window;->setNavigationBarColor(I)V

    sget v2, Landroid/os/Build$VERSION;->SDK_INT:I
    const/16 v3, 0x1c
    if-lt v2, v3, :cond_skip_cutout
    invoke-virtual {v0}, Landroid/view/Window;->getAttributes()Landroid/view/Window$LayoutParams;
    move-result-object v2
    sget v3, LX/TTrueReelHelper;->A04:I
    iput v3, v2, Landroid/view/Window$LayoutParams;->layoutInDisplayCutoutMode:I
    invoke-virtual {v0, v2}, Landroid/view/Window;->setAttributes(Landroid/view/Window$LayoutParams;)V
    :cond_skip_cutout

    sget v2, Landroid/os/Build$VERSION;->SDK_INT:I
    const/16 v3, 0x1d
    if-lt v2, v3, :cond_skip_contrast
    const/4 v2, 0x1
    invoke-virtual {v0, v2}, Landroid/view/Window;->setStatusBarContrastEnforced(Z)V
    invoke-virtual {v0, v2}, Landroid/view/Window;->setNavigationBarContrastEnforced(Z)V
    :cond_skip_contrast

    invoke-virtual {v1}, Landroid/view/View;->requestApplyInsets()V

    const-string v2, "InstaTrueReel"
    const-string v3, "v0.3 restore: original window chrome restored"
    invoke-static {v2, v3}, Landroid/util/Log;->e(Ljava/lang/String;Ljava/lang/String;)I

    :cond_reset
    const/4 v2, 0x0
    sput-object v2, LX/TTrueReelHelper;->A00:Landroid/view/Window;
    const/4 v2, 0x0
    sput-object v2, LX/TTrueReelHelper;->A09:Landroid/app/Activity;

    :cond_done
    :try_end_0
    .catch Ljava/lang/Throwable; {:try_start_0 .. :try_end_0} :catch_0

    return-void

    :catch_0
    move-exception v0
    const/4 v1, 0x0
    sput-object v1, LX/TTrueReelHelper;->A00:Landroid/view/Window;
    return-void
.end method


# A02(Landroidx/fragment/app/Fragment;Z)V == onHiddenChanged bridge
.method public static A02(Landroidx/fragment/app/Fragment;Z)V
    .locals 0

    if-eqz p1, :cond_show
    invoke-static {p0}, LX/TTrueReelHelper;->A01(Landroidx/fragment/app/Fragment;)V
    return-void

    :cond_show
    invoke-static {p0}, LX/TTrueReelHelper;->A00(Landroidx/fragment/app/Fragment;)V
    return-void
.end method


# A03(Landroid/app/Activity;I)I == status-bar-color interceptor for X/1fC.A04.
# While reels ACTIVE on the SAME activity, force fully transparent (0x00000000).
# Choke point for ALL status-bar color writes incl. Choreographer-deferred branch.
.method public static A03(Landroid/app/Activity;I)I
    .locals 1

    sget-boolean v0, LX/TTrueReelHelper;->A05:Z
    if-eqz v0, :cond_pass

    sget-object v0, LX/TTrueReelHelper;->A09:Landroid/app/Activity;
    if-eqz v0, :cond_pass
    if-ne v0, p0, :cond_pass

    const/4 v0, 0x0
    return v0

    :cond_pass
    return p1
.end method


# A07(Landroid/app/Activity;I)I == navigation-bar-color interceptor for X/1fI.A04.
# While reels ACTIVE on the SAME activity, force fully transparent (0x00000000).
# NEW in v0.3: covers the nav-bar strip (was opaque black in v0.2).
.method public static A07(Landroid/app/Activity;I)I
    .locals 1

    sget-boolean v0, LX/TTrueReelHelper;->A05:Z
    if-eqz v0, :cond_pass

    sget-object v0, LX/TTrueReelHelper;->A09:Landroid/app/Activity;
    if-eqz v0, :cond_pass
    if-ne v0, p0, :cond_pass

    const/4 v0, 0x0
    return v0

    :cond_pass
    return p1
.end method


# A05()V == schedule delayed re-applies on the main thread (100/400/1000/2500 ms)
.method public static A05()V
    .locals 4

    :try_start_0
    sget-object v0, LX/TTrueReelHelper;->A07:Landroid/os/Handler;
    if-nez v0, :cond_have_handler
    invoke-static {}, Landroid/os/Looper;->getMainLooper()Landroid/os/Looper;
    move-result-object v0
    new-instance v1, Landroid/os/Handler;
    invoke-direct {v1, v0}, Landroid/os/Handler;-><init>(Landroid/os/Looper;)V
    sput-object v1, LX/TTrueReelHelper;->A07:Landroid/os/Handler;
    sget-object v0, LX/TTrueReelHelper;->A07:Landroid/os/Handler;
    :cond_have_handler

    sget-object v1, LX/TTrueReelHelper;->A08:Ljava/lang/Runnable;
    if-nez v1, :cond_have_runnable
    new-instance v1, LX/TTrueReelReapply;
    invoke-direct {v1}, LX/TTrueReelReapply;-><init>()V
    sput-object v1, LX/TTrueReelHelper;->A08:Ljava/lang/Runnable;
    :cond_have_runnable

    invoke-virtual {v0, v1}, Landroid/os/Handler;->removeCallbacks(Ljava/lang/Runnable;)V

    check-cast v1, LX/TTrueReelReapply;
    sget-object v2, LX/TTrueReelHelper;->A00:Landroid/view/Window;
    iput-object v2, v1, LX/TTrueReelReapply;->A00:Landroid/view/Window;

    const-wide/16 v2, 0x64
    invoke-virtual {v0, v1, v2, v3}, Landroid/os/Handler;->postDelayed(Ljava/lang/Runnable;J)Z
    const-wide/16 v2, 0x190
    invoke-virtual {v0, v1, v2, v3}, Landroid/os/Handler;->postDelayed(Ljava/lang/Runnable;J)Z
    const-wide/16 v2, 0x3e8
    invoke-virtual {v0, v1, v2, v3}, Landroid/os/Handler;->postDelayed(Ljava/lang/Runnable;J)Z
    const-wide/16 v2, 0x9c4
    invoke-virtual {v0, v1, v2, v3}, Landroid/os/Handler;->postDelayed(Ljava/lang/Runnable;J)Z

    :try_end_0
    .catch Ljava/lang/Throwable; {:try_start_0 .. :try_end_0} :catch_0

    return-void

    :catch_0
    move-exception v0
    return-void
.end method


# A06(Landroid/view/Window;)V == REAPPLY core (idempotent, no state save).
# Forces: layout-stable|layout-fullscreen|layout-hide-nav (0x700), white system icons,
# transparent status + nav bar, DRAWS_SYSTEM_BAR_BACKGROUNDS, cutout SHORT_EDGES (1),
# contrast scrims off (API>=29), insets re-dispatch.
.method public static A06(Landroid/view/Window;)V
    .locals 4

    :try_start_0
    if-eqz p0, :cond_done

    invoke-virtual {p0}, Landroid/view/Window;->getDecorView()Landroid/view/View;
    move-result-object v1
    if-eqz v1, :cond_done

    # vis = vis | 0x700 & ~LIGHT_STATUS_BAR(0x2000) & ~LIGHT_NAVIGATION_BAR(0x10)
    invoke-virtual {v1}, Landroid/view/View;->getSystemUiVisibility()I
    move-result v2
    or-int/lit16 v2, v2, 0x700
    const v3, -0x2001
    and-int/2addr v2, v3
    and-int/lit8 v2, v2, -0x11
    invoke-virtual {v1, v2}, Landroid/view/View;->setSystemUiVisibility(I)V

    # fully transparent status + nav bar
    const/4 v2, 0x0
    invoke-virtual {p0, v2}, Landroid/view/Window;->setStatusBarColor(I)V
    invoke-virtual {p0, v2}, Landroid/view/Window;->setNavigationBarColor(I)V

    # clear legacy translucent bar flags, add DRAWS_SYSTEM_BAR_BACKGROUNDS
    const v2, 0xc000000
    invoke-virtual {p0, v2}, Landroid/view/Window;->clearFlags(I)V
    const/high16 v2, -0x80000000
    invoke-virtual {p0, v2}, Landroid/view/Window;->addFlags(I)V

    # cutout mode SHORT_EDGES (=1) on API >= 28
    sget v2, Landroid/os/Build$VERSION;->SDK_INT:I
    const/16 v3, 0x1c
    if-lt v2, v3, :cond_skip_cutout
    invoke-virtual {p0}, Landroid/view/Window;->getAttributes()Landroid/view/Window$LayoutParams;
    move-result-object v2
    const/4 v3, 0x1
    iput v3, v2, Landroid/view/Window$LayoutParams;->layoutInDisplayCutoutMode:I
    invoke-virtual {p0, v2}, Landroid/view/Window;->setAttributes(Landroid/view/Window$LayoutParams;)V
    :cond_skip_cutout

    # disable contrast scrims on API >= 29
    sget v2, Landroid/os/Build$VERSION;->SDK_INT:I
    const/16 v3, 0x1d
    if-lt v2, v3, :cond_skip_contrast
    const/4 v2, 0x0
    invoke-virtual {p0, v2}, Landroid/view/Window;->setStatusBarContrastEnforced(Z)V
    invoke-virtual {p0, v2}, Landroid/view/Window;->setNavigationBarContrastEnforced(Z)V
    :cond_skip_contrast

    invoke-virtual {v1}, Landroid/view/View;->requestApplyInsets()V

    :cond_done
    :try_end_0
    .catch Ljava/lang/Throwable; {:try_start_0 .. :try_end_0} :catch_0

    return-void

    :catch_0
    move-exception v0
    return-void
.end method
