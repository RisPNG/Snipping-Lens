from typing import Optional

from .clr_error import ClrError

__all__ = ["get_hostfxr_error"]


def get_hostfxr_error(hresult: int) -> Optional[ClrError]:
    if hresult in HOSTFXR_ERRORS:
        return ClrError(hresult, HOSTFXR_ERRORS[hresult])
    else:
        return None


_ERRORS = dict(
    Success=0,
    Success_HostAlreadyInitialized=0x00000001,
    Success_DifferentRuntimeProperties=0x00000002,
    # Failure
    InvalidArgFailure=0x80008081,
    CoreHostLibLoadFailure=0x80008082,
    CoreHostLibMissingFailure=0x80008083,
    CoreHostEntryPointFailure=0x80008084,
    CoreHostCurHostFindFailure=0x80008085,
    #  unused                           = 0x80008086,
    CoreClrResolveFailure=0x80008087,
    CoreClrBindFailure=0x80008088,
    CoreClrInitFailure=0x80008089,
    CoreClrExeFailure=0x8000808A,
    ResolverInitFailure=0x8000808B,
    ResolverResolveFailure=0x8000808C,
    LibHostCurExeFindFailure=0x8000808D,
    LibHostInitFailure=0x8000808E,
    #  unused                           = 0x8000808f,
    LibHostExecModeFailure=0x80008090,
    LibHostSdkFindFailure=0x80008091,
    LibHostInvalidArgs=0x80008092,
    InvalidConfigFile=0x80008093,
    AppArgNotRunnable=0x80008094,
    AppHostExeNotBoundFailure=0x80008095,
    FrameworkMissingFailure=0x80008096,
    HostApiFailed=0x80008097,
    HostApiBufferTooSmall=0x80008098,
    LibHostUnknownCommand=0x80008099,
    LibHostAppRootFindFailure=0x8000809A,
    SdkResolverResolveFailure=0x8000809B,
    FrameworkCompatFailure=0x8000809C,
    FrameworkCompatRetry=0x8000809D,
    #  unused                           = 0x8000809e,
    BundleExtractionFailure=0x8000809F,
    BundleExtractionIOError=0x800080A0,
    LibHostDuplicateProperty=0x800080A1,
    HostApiUnsupportedVersion=0x800080A2,
    HostInvalidState=0x800080A3,
    HostPropertyNotFound=0x800080A4,
    CoreHostIncompatibleConfig=0x800080A5,
)


HOSTFXR_ERRORS = {v: k for k, v in _ERRORS.items()}
