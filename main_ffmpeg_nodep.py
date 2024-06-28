import ctypes
import os
import time
import subprocess
from ctypes import wintypes as wt

GAME_WIN_TILE = 'I Wanna Be The Boshy'
HOURGLASS_TEXT_HANDLE = wt.HWND(eval(os.getenv('HGT_HWND') or '0'))
FPS = 50.0
STREAM_TYPE = 'rawvideo'
CODEC = 'mpeg4'
DEPTH = 32
FORMAT = 'rgb32'
BIT_RATE = '5000k'
OUTPUT = 'out%i%.mp4'

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = (
        ("biSize", wt.DWORD),
        ("biWidth", wt.LONG),
        ("biHeight", wt.LONG),
        ("biPlanes", wt.WORD),
        ("biBitCount", wt.WORD),
        ("biCompression", wt.DWORD),
        ("biSizeImage", wt.DWORD),
        ("biXPelsPerMeter", wt.LONG),
        ("biYPelsPerMeter", wt.LONG),
        ("biClrUsed", wt.DWORD),
        ("biClrImportant", wt.DWORD),
    )


class BITMAPINFO(ctypes.Structure):
    _fields_ = (("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wt.DWORD * 3))

u32 = ctypes.windll.user32
u32.GetForegroundWindow.argtypes = ()
u32.GetForegroundWindow.restype = wt.HWND
u32.GetWindowTextW.argtypes = (wt.HWND, wt.LPWSTR, ctypes.c_int)
u32.GetWindowTextW.restype = ctypes.c_int
u32.FindWindowW.argtypes = (wt.LPCWSTR, wt.LPCWSTR)
u32.FindWindowW.restype = wt.HWND
u32.GetClientRect.argtypes = (wt.HWND, wt.LPRECT)
u32.GetClientRect.restype = wt.BOOL
u32.GetWindowRect.argtypes = (wt.HWND, wt.LPRECT)
u32.GetWindowRect.restype = wt.BOOL
u32.ScreenToClient.argtypes = (wt.HWND, wt.LPPOINT)
u32.ScreenToClient.restype = wt.BOOL
u32.ClientToScreen.argtypes = (wt.HWND, wt.LPPOINT)
u32.ClientToScreen.restype = wt.BOOL
u32.GetSystemMetrics.argtypes = (wt.INT, )
u32.GetSystemMetrics.restype = wt.INT
u32.GetWindowDC.argtypes = (wt.HWND, )
u32.GetWindowDC.restype = wt.HDC
u32.ReleaseDC.argtypes = (wt.HWND, wt.HDC)
u32.ReleaseDC.restype = ctypes.c_int

g32 = ctypes.windll.gdi32
g32.BitBlt.argtypes = (wt.HDC, wt.INT, wt.INT, wt.INT, wt.INT, wt.HDC, wt.INT, wt.INT, wt.DWORD)
g32.BitBlt.restype = wt.BOOL
g32.CreateCompatibleBitmap.argtypes = (wt.HDC, wt.INT, wt.INT)
g32.CreateCompatibleBitmap.restype = wt.HBITMAP
g32.CreateCompatibleDC.argtypes = (wt.HDC, )
g32.CreateCompatibleDC.restype = wt.HDC
g32.DeleteDC.argtypes = (wt.HDC, )
g32.DeleteDC.restype = wt.HDC
g32.DeleteObject.argtypes = (wt.HGDIOBJ, )
g32.DeleteObject.restype = wt.HWND
g32.GetDeviceCaps.argtypes = (wt.HWND, wt.INT)
g32.GetDeviceCaps.restype = wt.INT
g32.GetDIBits.argtypes = (wt.HDC, wt.HBITMAP, wt.UINT, wt.UINT, ctypes.c_void_p, ctypes.POINTER(BITMAPINFO), wt.UINT)
g32.GetDIBits.restype = wt.BOOL
g32.SelectObject.argtypes = (wt.HDC, wt.HGDIOBJ)
g32.SelectObject.restype = wt.HGDIOBJ

CAPTUREBLT = 0x40000000
DIB_RGB_COLORS = 0
SRCCOPY = 0x00CC0020


def get_win_size(hwnd: wt.HWND) -> tuple:
    rect_buf = wt.RECT(0, 0, 0, 0)
    u32.GetClientRect(hwnd, rect_buf)
    return rect_buf.right, rect_buf.bottom


def get_win_top_left(hwnd: wt.HWND) -> tuple:
    point_buf = wt.POINT(0, 0)
    u32.ClientToScreen(hwnd, point_buf)
    return point_buf.x, point_buf.y


def get_win_cap(hwnd: wt.HWND) -> str:
    buf = (ctypes.c_wchar * 1337)()
    if u32.GetWindowTextW(hwnd, buf, 1336) <= 0:
        return ''
    return buf.value


class ScreenShot:
    def __init__(self, data, size) -> None:
        self.__pixels = None
        self.__rgb = None
        self.raw = data
        self.size = size

    @property
    def __array_interface__(self):
        return {
            "version": 3,
            "shape": (self.size[0], self.size[1], 4),
            "typestr": "|u1",
            "data": self.raw,
        }


bmp = None
srcdc = u32.GetWindowDC(0)
memdc = g32.CreateCompatibleDC(srcdc)

bmi = BITMAPINFO()
bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
bmi.bmiHeader.biPlanes = 1  # Always 1
bmi.bmiHeader.biBitCount = 32  # See grab.__doc__ [2]
bmi.bmiHeader.biCompression = 0  # 0 = BI_RGB (no compression)
bmi.bmiHeader.biClrUsed = 0  # See grab.__doc__ [3]
bmi.bmiHeader.biClrImportant = 0  # See grab.__doc__ [3]

game_hwnd = u32.FindWindowW(None, GAME_WIN_TILE)
hg_hwnd = HOURGLASS_TEXT_HANDLE
if not game_hwnd:
    raise RuntimeError('Failed to find game window')
if not hg_hwnd or not get_win_cap(hg_hwnd):
    raise RuntimeError('Failed to find hourglass text window')
win_size = get_win_size(game_hwnd)
cnt = 0
hg_text = 'Dummy Text'
out = None
region_width_height = (win_size[0], win_size[1])
bmi.bmiHeader.biWidth = win_size[0]
bmi.bmiHeader.biHeight = -win_size[1]
data = ctypes.create_string_buffer(win_size[0] * win_size[1] * 4)
bmp = g32.CreateCompatibleBitmap(srcdc, win_size[0], win_size[1])
g32.SelectObject(memdc, bmp)
command = [
    'ffmpeg',
    '-y',
    '-f', STREAM_TYPE,
    '-vcodec', STREAM_TYPE,
    '-s', str(win_size[0]) + 'x' + str(win_size[1]),
    '-pix_fmt', FORMAT,
    '-r', str(FPS),
    '-i', '-',
    '-an',
    '-vcodec', CODEC,
    '-b', BIT_RATE,
    OUTPUT.replace('%i%', str(cnt))
]
proc = subprocess.Popen(
    command,
    stdin=subprocess.PIPE,
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
)

print('Trying to capture...')
try:
    while 1:
        if not u32.FindWindowW(None, GAME_WIN_TILE):
            print('Window Closed')
            break
        if not u32.GetForegroundWindow() == game_hwnd:
            # Not Focused
            continue
        new_text = get_win_cap(hg_hwnd)
        if new_text == hg_text:
            continue
        hg_text = new_text
        real_x, real_y = get_win_top_left(game_hwnd)
        if not get_win_size(game_hwnd) == win_size:
            win_size = get_win_size(game_hwnd)
            cnt += 1
            raise RuntimeError('Window Size changed')
        time.sleep(0.001)
        g32.BitBlt(memdc, 0, 0, win_size[0], win_size[1], srcdc, real_x, real_y, SRCCOPY | CAPTUREBLT)
        bits = g32.GetDIBits(memdc, bmp, 0, win_size[1], data, bmi, DIB_RGB_COLORS)
        if bits != win_size[1]:
            msg = "gdi32.GetDIBits() failed."
            raise RuntimeError(msg)
        proc.stdin.write(bytearray(data))
        proc.stdin.flush()
except Exception as err:
    print()
    print(err)
    print()
    pass

proc.stdin.close()
print('Normal exit')
