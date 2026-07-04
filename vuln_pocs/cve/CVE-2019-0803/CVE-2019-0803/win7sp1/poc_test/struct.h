#pragma once

#define DDE_SERVER_APP_NAME		L"MyDDEService"
#define DDE_SERVER_TOPIC_NAME	L"Topic"
#define DDE_SERVER_ITEM_NAME	L"Item"

#define DDE_SERVER_WINDOW_CAPTION L"DDEServerPoc"
#define DDE_CLIENT_WINDOW_CAPTION L"DDEClientPoc"

#define MSG_DDESERVER_EXIT			        WM_USER + 1
#define MSG_DDESERVER_SET_GDI_OBJ_ADDR	    WM_USER + 2

#define LENGTH_TAGWND 0x128
#define OFFSET_SPWNDPARENT_WIN7 0x58
#define OFFSET_STRNAME_WIN7 0xD8
#define OFFSET_CBWNDEXTRA_WIN7 0xE8
#define OFFSET_APCADDR_WIN7 0x50
#define OFFSET_APCEPROCESS_WIN7 0x20
#define OFFSET_SECTOKEN_WIN7 0x208
#define OFFSET_EPROCESSPID_WIN7 0x180
#define OFFSET_EPROCESSBLINK_WIN7 0x188

typedef struct _HANDLEENTRY {
    PVOID   phead;
    PVOID   pOwner;
    BYTE    bType;
    BYTE    bFlags;
    WORD    wUniq;
} HANDLEENTRY, * PHANDLEENTRY;

typedef struct _SERVERINFO {
    WORD    wRIPFlags;
    WORD    wSRVIFlags;
    WORD    wRIPPID;
    WORD    wRIPError;
    ULONG   cHandleEntries;
} SERVERINFO, * PSERVERINFO;

typedef struct _SHAREDINFO {
    PSERVERINFO  psi;
    PHANDLEENTRY aheList;
    ULONG        HeEntrySize;
} SHAREDINFO, * PSHAREDINFO;


typedef struct _LARGE_STRING {
    ULONG Length;
    ULONG MaximumLength : 31;
    ULONG bAnsi : 1;
    PVOID Buffer;
} LARGE_STRING, * PLARGE_STRING;

typedef struct _PEB
{
    BOOLEAN InheritedAddressSpace;
    BOOLEAN ReadImageFileExecOptions;
    BOOLEAN BeingDebugged;
    union
    {
        BOOLEAN BitField;
        struct
        {
            BOOLEAN ImageUsesLargePages : 1;
            BOOLEAN IsProtectedProcess : 1;
            BOOLEAN IsLegacyProcess : 1;
            BOOLEAN IsImageDynamicallyRelocated : 1;
            BOOLEAN SkipPatchingUser32Forwarders : 1;
            BOOLEAN SpareBits : 3;
        };
    };
    HANDLE Mutant;

    PVOID ImageBaseAddress;
    PVOID Ldr;
    PVOID ProcessParameters;
    PVOID SubSystemData;
    PVOID ProcessHeap;
    PRTL_CRITICAL_SECTION FastPebLock;
    PVOID AtlThunkSListPtr;
    PVOID IFEOKey;
    union
    {
        ULONG CrossProcessFlags;
        struct
        {
            ULONG ProcessInJob : 1;
            ULONG ProcessInitializing : 1;
            ULONG ProcessUsingVEH : 1;
            ULONG ProcessUsingVCH : 1;
            ULONG ProcessUsingFTH : 1;
            ULONG ReservedBits0 : 27;
        };
        ULONG EnvironmentUpdateCount;
    };
    union
    {
        PVOID KernelCallbackTable;
        PVOID UserSharedInfoPtr;
    };
} PEB, * PPEB;

typedef struct _CLIENT_ID {
    HANDLE UniqueProcess;
    HANDLE UniqueThread;
} CLIENT_ID, * PCLIENT_ID;

typedef struct _TEB
{
    NT_TIB NtTib;
    PVOID EnvironmentPointer;
    CLIENT_ID ClientId;
    PVOID ActiveRpcHandle;
    PVOID ThreadLocalStoragePointer;
    PPEB ProcessEnvironmentBlock;
    ULONG LastErrorValue;
    ULONG CountOfOwnedCriticalSections;
    PVOID CsrClientThread;
    PVOID Win32ThreadInfo;
}TEB, * PTEB;

typedef
PVOID
(WINAPI* pfRtlAllocateHeap)(
    PVOID HeapHandle,
    ULONG Flags,
    SIZE_T Size
    );

extern "C"
HACCEL
NtUserCreateAcceleratorTable(
    LPACCEL Entries,
    ULONG EntriesCount
);

extern "C"
BOOL
NtUserShowWindow(
    IN HWND hwnd,
    IN int nCmdShow
);

extern "C"
HDC
NtUserBeginPaint(
    IN HWND hwnd,
    OUT LPPAINTSTRUCT lpPaint
);

extern "C"
BOOL
NtUserDestroyWindow(
    IN HWND hwnd
);