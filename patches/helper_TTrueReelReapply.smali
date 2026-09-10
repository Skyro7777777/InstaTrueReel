.class public LX/TTrueReelReapply;
.super Ljava/lang/Object;
.implements Ljava/lang/Runnable;
.source "TTrueReelReapply"


# instance fields
.field public A00:Landroid/view/Window;


# direct methods
.method public constructor <init>()V
    .locals 1

    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    return-void
.end method


# virtual methods
.method public final run()V
    .locals 1

    :try_start_0
    sget-boolean v0, LX/TTrueReelHelper;->A05:Z
    if-eqz v0, :cond_done

    iget-object v0, p0, LX/TTrueReelReapply;->A00:Landroid/view/Window;
    if-eqz v0, :cond_done

    invoke-static {v0}, LX/TTrueReelHelper;->A06(Landroid/view/Window;)V

    :cond_done
    :try_end_0
    .catch Ljava/lang/Throwable; {:try_start_0 .. :try_end_0} :catch_0

    return-void

    :catch_0
    move-exception v0
    return-void
.end method
