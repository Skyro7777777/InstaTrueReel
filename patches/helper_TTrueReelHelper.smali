.class public final LX/TTrueReelHelper;
.super Ljava/lang/Object;
.source "TTrueReelHelper"


# static fields
.field public static A00:Landroid/view/Window;
.field public static A01:I
.field public static A02:I
.field public static A03:I
.field public static A04:I


# direct methods

# A00(Landroidx/fragment/app/Fragment;)V  == APPLY edge-to-edge (TikTok-style) to the activity window
.method public static A00(Landroidx/fragment/app/Fragment;)V
    .locals 6

    :try_start_0
    sget-object v0, LX/TTrueReelHelper;->A00:Landroid/view/Window;
    if-nez v0, :cond_skip

    invoke-virtual {p0}, Landroidx/fragment/app/Fragment;->getActivity()Landroidx/fragment/app/FragmentActivity;
    move-result-object v0
    if-eqz v0, :cond_skip

    invoke-virtual {v0}, Landroid/app/Activity;->getWindow()Landroid/view/Window;
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

    # ---- apply edge-to-edge ----
    # vis = (saved | LAYOUT_STABLE|LAYOUT_FULLSCREEN|LAYOUT_HIDE_NAVIGATION) & ~LIGHT_STATUS_BAR & ~LIGHT_NAVIGATION_BAR
    invoke-virtual {v1}, Landroid/view/View;->getSystemUiVisibility()I
    move-result v2
    or-int/lit16 v2, v2, 0x700
    const v3, -0x2001
    and-int/2addr v2, v3
    and-int/lit8 v2, v2, -0x11
    invoke-virtual {v1, v2}, Landroid/view/View;->setSystemUiVisibility(I)V

    # fully transparent status + nav bar
    const/4 v2, 0x0
    invoke-virtual {v0, v2}, Landroid/view/Window;->setStatusBarColor(I)V
    invoke-virtual {v0, v2}, Landroid/view/Window;->setNavigationBarColor(I)V

    # clear legacy translucent bar flags, add DRAWS_SYSTEM_BAR_BACKGROUNDS
    const v2, 0xc000000
    invoke-virtual {v0, v2}, Landroid/view/Window;->clearFlags(I)V
    const/high16 v2, -0x80000000
    invoke-virtual {v0, v2}, Landroid/view/Window;->addFlags(I)V

    # cutout mode SHORT_EDGES on API >= 28
    sget v2, Landroid/os/Build$VERSION;->SDK_INT:I
    const/16 v3, 0x1c
    if-lt v2, v3, :cond_skip_cutout
    invoke-virtual {v0}, Landroid/view/Window;->getAttributes()Landroid/view/Window$LayoutParams;
    move-result-object v2
    const/4 v3, 0x2
    iput v3, v2, Landroid/view/Window$LayoutParams;->layoutInDisplayCutoutMode:I
    invoke-virtual {v0, v2}, Landroid/view/Window;->setAttributes(Landroid/view/Window$LayoutParams;)V
    :cond_skip_cutout

    # disable contrast scrims on API >= 29 (avoids opaque system-bar scrim)
    sget v2, Landroid/os/Build$VERSION;->SDK_INT:I
    const/16 v3, 0x1d
    if-lt v2, v3, :cond_skip_contrast
    const/4 v2, 0x0
    invoke-virtual {v0, v2}, Landroid/view/Window;->setStatusBarContrastEnforced(Z)V
    invoke-virtual {v0, v2}, Landroid/view/Window;->setNavigationBarContrastEnforced(Z)V
    :cond_skip_contrast

    invoke-virtual {v1}, Landroid/view/View;->requestApplyInsets()V

    :cond_skip
    :try_end_0
    .catch Ljava/lang/Throwable; {:try_start_0 .. :try_end_0} :catch_0

    return-void

    :catch_0
    move-exception v0
    const/4 v1, 0x0
    sput-object v1, LX/TTrueReelHelper;->A00:Landroid/view/Window;
    return-void
.end method


# A01(Landroidx/fragment/app/Fragment;)V  == RESTORE original window state
.method public static A01(Landroidx/fragment/app/Fragment;)V
    .locals 4

    :try_start_0
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

    :cond_reset
    const/4 v2, 0x0
    sput-object v2, LX/TTrueReelHelper;->A00:Landroid/view/Window;

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


# A02(Landroidx/fragment/app/Fragment;Z)V  == onHiddenChanged bridge
.method public static A02(Landroidx/fragment/app/Fragment;Z)V
    .locals 0

    if-eqz p1, :cond_show
    invoke-static {p0}, LX/TTrueReelHelper;->A01(Landroidx/fragment/app/Fragment;)V
    return-void

    :cond_show
    invoke-static {p0}, LX/TTrueReelHelper;->A00(Landroidx/fragment/app/Fragment;)V
    return-void
.end method
