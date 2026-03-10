import os
import sys
import winreg

# 레지스트리에 등록될 프로그램의 고유 이름입니다.
APP_NAME = "DailyScraper"


def get_executable_path():
    if getattr(sys, "frozen", False):
        return sys.executable
    else:
        return os.path.abspath(sys.argv[0])


def is_startup_enabled():
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_READ,
        ) as key:
            winreg.QueryValueEx(key, APP_NAME)

        return True
    except FileNotFoundError:
        return False


def set_startup(enable=True):
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_ALL_ACCESS,
        ) as key:
            if enable:
                exe_path = get_executable_path()
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass

        return True
    except Exception as e:
        print(f"시작 프로그램 설정 중 오류 발생: {e}")
        return False
