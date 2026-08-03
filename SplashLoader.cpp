#include <windows.h>
#include <commctrl.h>
#include <stdio.h>
#include <stdlib.h>
#include <thread>
#include <chrono>
#include <string>
#include <fstream>
#include <sstream>

#pragma comment(lib, "comctl32.lib")
#pragma comment(linker,"\"/manifestdepend:type='win32' name='Microsoft.Windows.Common-Controls' version='6.0.0.0' processorArchitecture='*' publicKeyToken='6595b64144ccf1df' language='*'\"")

#define IDC_PROGRESS 1001
#define IDC_STATUS_TEXT 1002
#define IDC_LOGO_TEXT 1003

HWND hProgress;
HWND hStatusText;
HWND hWnd;
HWND hLogoText;
volatile bool bShouldClose = false;
int iCurrentProgress = 0;

LRESULT CALLBACK WindowProc(HWND hwnd, UINT uMsg, WPARAM wParam, LPARAM lParam)
{
    switch (uMsg)
    {
    case WM_CREATE:
    {
        // Crear etiqueta de logo/título
        hLogoText = CreateWindowW(L"STATIC", L"⚡ VISO v4.2.4",
            WS_CHILD | WS_VISIBLE | SS_CENTER,
            10, 20, 380, 40,
            hwnd, (HMENU)IDC_LOGO_TEXT, NULL, NULL);
        if (hLogoText)
        {
            HDC hdc = GetDC(hLogoText);
            HFONT hFont = CreateFontW(28, 0, 0, 0, FW_BOLD, FALSE, FALSE, FALSE,
                DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS,
                DEFAULT_QUALITY, DEFAULT_PITCH | FF_DONTCARE, L"Arial");
            SendMessage(hLogoText, WM_SETFONT, (WPARAM)hFont, TRUE);
            ReleaseDC(hLogoText, hdc);
        }

        // Crear control de progreso
        hProgress = CreateWindowW(PROGRESS_CLASSW, NULL,
            WS_CHILD | WS_VISIBLE | PBS_SMOOTH,
            20, 100, 360, 30,
            hwnd, (HMENU)IDC_PROGRESS, NULL, NULL);
        if (hProgress)
        {
            SendMessage(hProgress, PBM_SETRANGE, 0, MAKELPARAM(0, 100));
            SendMessage(hProgress, PBM_SETSTEP, 1, 0);
            SendMessage(hProgress, PBM_SETPOS, 0, 0);
        }

        // Crear etiqueta de estado
        hStatusText = CreateWindowW(L"STATIC", L"Inicializando...",
            WS_CHILD | WS_VISIBLE | SS_CENTER,
            10, 150, 380, 60,
            hwnd, (HMENU)IDC_STATUS_TEXT, NULL, NULL);
        if (hStatusText)
        {
            HDC hdc = GetDC(hStatusText);
            HFONT hFont = CreateFontW(12, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE,
                DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS,
                DEFAULT_QUALITY, DEFAULT_PITCH | FF_DONTCARE, L"Arial");
            SendMessage(hStatusText, WM_SETFONT, (WPARAM)hFont, TRUE);
            ReleaseDC(hStatusText, hdc);
        }

        SetTimer(hwnd, 1, 50, NULL);
        break;
    }
    case WM_PAINT:
    {
        PAINTSTRUCT ps;
        HDC hdc = BeginPaint(hwnd, &ps);

        // Dibujar fondo degradado
        HBRUSH hBrush = CreateSolidBrush(RGB(15, 23, 42)); // Color azul oscuro
        FillRect(hdc, &ps.rcPaint, hBrush);
        DeleteObject(hBrush);

        EndPaint(hwnd, &ps);
        break;
    }
    case WM_TIMER:
    {
        if (bShouldClose)
        {
            PostMessage(hwnd, WM_QUIT, 0, 0);
        }
        break;
    }
    case WM_CLOSE:
        bShouldClose = true;
        break;
    case WM_DESTROY:
        PostQuitMessage(0);
        break;
    default:
        return DefWindowProcW(hwnd, uMsg, wParam, lParam);
    }
    return 0;
}

void UpdateSplashProgress(int progress, const wchar_t* status)
{
    if (hProgress)
    {
        SendMessage(hProgress, PBM_SETPOS, progress, 0);
    }
    if (hStatusText && status)
    {
        SetWindowTextW(hStatusText, status);
    }
}

int WINAPI wWinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, LPWSTR lpCmdLine, int nCmdShow)
{
    InitCommonControls();

    // Registrar clase de ventana
    WNDCLASSW wc = { 0 };
    wc.lpfnWndProc = WindowProc;
    wc.hInstance = hInstance;
    wc.lpszClassName = L"SplashLoaderClass";
    wc.hbrBackground = CreateSolidBrush(RGB(15, 23, 42));
    wc.hCursor = LoadCursor(NULL, IDC_ARROW);

    if (!RegisterClassW(&wc))
    {
        return 1;
    }

    // Obtener dimensiones de la pantalla para centrar
    int screenWidth = GetSystemMetrics(SM_CXSCREEN);
    int screenHeight = GetSystemMetrics(SM_CYSCREEN);
    int windowWidth = 400;
    int windowHeight = 240;
    int xPos = (screenWidth - windowWidth) / 2;
    int yPos = (screenHeight - windowHeight) / 2;

    // Crear ventana principal
    hWnd = CreateWindowW(
        L"SplashLoaderClass",
        L"VISO - Inicializando",
        WS_POPUP | WS_BORDER,
        xPos, yPos, windowWidth, windowHeight,
        NULL, NULL, hInstance, NULL
    );

    if (!hWnd)
    {
        return 1;
    }

    // Mostrar ventana
    ShowWindow(hWnd, SW_SHOW);
    UpdateWindow(hWnd);

    // Thread para ejecutar el programa Python
    std::thread pythonThread([&]()
    {
        // Actualizar estado inicial
        UpdateSplashProgress(30, L"Iniciando sistema...");
        std::this_thread::sleep_for(std::chrono::milliseconds(100));

        // Ejecutar el programa principal
        UpdateSplashProgress(50, L"Ejecutando VISO...");
        
        STARTUPINFOW si = { 0 };
        PROCESS_INFORMATION pi = { 0 };
        si.cb = sizeof(si);

        // Obtener ruta del directorio actual
        wchar_t currentDir[MAX_PATH];
        GetCurrentDirectoryW(MAX_PATH, currentDir);

        // Ejecutar main.py
        wchar_t cmdLine[1024];
        swprintf_s(cmdLine, L"python.exe main.py");

        if (CreateProcessW(
            NULL,
            cmdLine,
            NULL,
            NULL,
            FALSE,
            CREATE_NO_WINDOW,
            NULL,
            currentDir,
            &si,
            &pi))
        {
            UpdateSplashProgress(100, L"✓ VISO iniciado");
            std::this_thread::sleep_for(std::chrono::milliseconds(500));

            // Cerrar la ventana de splash
            bShouldClose = true;

            // Esperar a que termine el proceso Python
            WaitForSingleObject(pi.hProcess, INFINITE);
            CloseHandle(pi.hProcess);
            CloseHandle(pi.hThread);
        }
        else
        {
            UpdateSplashProgress(0, L"✗ Error al iniciar VISO");
            std::this_thread::sleep_for(std::chrono::seconds(3));
            bShouldClose = true;
        }
    });
    pythonThread.detach();

    // Message loop
    MSG msg = { 0 };
    while (GetMessage(&msg, NULL, 0, 0))
    {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }

    return (int)msg.wParam;
}
