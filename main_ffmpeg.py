import ctypes
import mss  # noqa
import os
import time
import mss.tools
import numpy
import subprocess
from ctypes import wintypes as wt

GAME_WIN_TILE = 'I Wanna Be The Boshy'
HOURGLASS_TEXT_HANDLE = wt.HWND(eval(os.getenv('HGT_HWND') or 0))
FPS = 50.0
STREAM_TYPE = 'rawvideo'
CODEC = 'mpeg4'
DEPTH = 32
FORMAT = 'rgb32'
BIT_RATE = '5000k'
OUTPUT = 'out%i%.mp4'

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


game_hwnd = u32.FindWindowW(None, GAME_WIN_TILE)
hg_hwnd = HOURGLASS_TEXT_HANDLE
if not game_hwnd:
    raise RuntimeError('Failed to find game window')
if not hg_hwnd or not get_win_cap(hg_hwnd):
    raise RuntimeError('Failed to find hourglass text window')
win_size = get_win_size(game_hwnd)
sct = mss.mss()
cnt = 0
hg_text = 'Dummy Text'
out = None
command = [
    'ffmpeg',
    '-y',
    '-f', STREAM_TYPE,
    '-vcodec', STREAM_TYPE,
    '-s', f'{win_size[0]}x{win_size[1]}',
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
        sct_img = sct.grab({
            'left': real_x,
            'top': real_y,
            'width': win_size[0],
            'height': win_size[1]
        })
        img = numpy.array(sct_img).astype('uint8')  # noqa
        proc.stdin.write(img.tobytes())
        proc.stdin.flush()
except KeyboardInterrupt:
    pass

proc.stdin.close()
sct.close()
print('Normal exit')
