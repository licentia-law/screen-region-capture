import os
import re
from pathlib import Path
from datetime import datetime

import sys
import tkinter as tk
from tkinter import messagebox, filedialog

import mss
from PIL import Image
import ctypes


# RESULT_DIR global removed



def normalize_rect(x1, y1, x2, y2):
    left = min(x1, x2)
    top = min(y1, y2)
    right = max(x1, x2)
    bottom = max(y1, y2)
    width = max(1, right - left)
    height = max(1, bottom - top)
    return {"left": int(left), "top": int(top), "width": int(width), "height": int(height)}






class RegionSelectorOverlay:
    """
    전체 화면 오버레이에서 드래그로 영역 선택 (박스 표시)
    선택 완료 시 callback(region_dict) 호출
    ESC로 취소 시 callback(None)
    """
    def __init__(self, on_done):
        self.on_done = on_done

        self.root = tk.Toplevel()
        self.root.title("영역 지정")
        self.root.attributes("-topmost", True)
        self.root.overrideredirect(True)  # 테두리 제거

        # 반투명 오버레이 (지원 안 되는 환경이면 그냥 불투명)
        try:
            self.root.attributes("-alpha", 0.20)
        except Exception:
            pass

        # 전체 화면 크기 (모든 모니터 포함)
        with mss.mss() as sct:
            # monitors[0]는 전체 모니터를 포함하는 가상 화면 정보
            monitor_all = sct.monitors[0]
            self.screen_x = monitor_all["left"]
            self.screen_y = monitor_all["top"]
            self.screen_w = monitor_all["width"]
            self.screen_h = monitor_all["height"]

        self.root.geometry(f"{self.screen_w}x{self.screen_h}+{self.screen_x}+{self.screen_y}")

        self.canvas = tk.Canvas(self.root, highlightthickness=0, cursor="cross")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.start_x = None
        self.start_y = None
        self.rect_id = None

        # 안내 문구
        self.canvas.create_text(
            20, 20, anchor="nw",
            text="마우스로 드래그하여 캡쳐 영역을 지정하세요. (ESC: 취소)",
            font=("맑은 고딕", 16)
        )

        self.canvas.bind("<ButtonPress-1>", self.on_down)
        self.canvas.bind("<B1-Motion>", self.on_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_up)
        self.root.bind("<Escape>", self.on_cancel)

    def on_down(self, event):
        self.start_x, self.start_y = event.x, event.y
        if self.rect_id:
            self.canvas.delete(self.rect_id)
            self.rect_id = None
        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline="red", width=3
        )

    def on_move(self, event):
        if self.rect_id and self.start_x is not None:
            self.canvas.coords(self.rect_id, self.start_x, self.start_y, event.x, event.y)

    def on_up(self, event):
        if self.start_x is None:
            return
        region = normalize_rect(self.start_x, self.start_y, event.x, event.y)
        
        # 오프셋 보정 (다중 모니터 좌표 반영)
        region["left"] += self.screen_x
        region["top"] += self.screen_y

        self.root.destroy()
        self.on_done(region)

    def on_cancel(self, _event=None):
        self.root.destroy()
        self.on_done(None)


class App:
    def __init__(self, root):
        self.root = root
        self.root.withdraw()  # 폴더 선택 전까지 숨김

        # 폴더 선택
        base_dir = filedialog.askdirectory(title="결과를 저장할 폴더를 선택하세요")
        if not base_dir:
            messagebox.showinfo("알림", "폴더가 선택되지 않아 프로그램을 종료합니다.")
            self.root.destroy()
            sys.exit(0)

        self.save_dir = Path(base_dir) / "screen-region-capture"
        try:
            self.save_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            messagebox.showerror("오류", f"폴더 생성 실패: {e}")
            self.root.destroy()
            sys.exit(1)

        self.root.deiconify()  # 메인 창 표시
        self.root.title(f"화면 영역 캡쳐 도구 - 저장위치: {self.save_dir.name}")
        self.root.geometry("520x220")
        self.root.resizable(False, False)

        # 실행 중 유지되는 영역(메모리)
        self.region = None


        # UI
        self.status_var = tk.StringVar(value="상태: 영역이 지정되지 않았습니다.")
        self.region_var = tk.StringVar(value="영역: (미지정)")
        self.nextfile_var = tk.StringVar(value="파일 이름: [날짜]_[시간]_[마이크로초].png")


        title = tk.Label(root, text="화면 영역 캡쳐 도구", font=("맑은 고딕", 16, "bold"))
        title.pack(pady=(14, 8))

        info_frame = tk.Frame(root)
        info_frame.pack(fill=tk.X, padx=14)

        tk.Label(info_frame, textvariable=self.status_var, font=("맑은 고딕", 11), anchor="w").pack(fill=tk.X)
        tk.Label(info_frame, textvariable=self.region_var, font=("Consolas", 11), anchor="w").pack(fill=tk.X, pady=(4, 0))
        tk.Label(info_frame, textvariable=self.nextfile_var, font=("Consolas", 11), anchor="w").pack(fill=tk.X, pady=(4, 0))

        btn_frame = tk.Frame(root)
        btn_frame.pack(fill=tk.X, padx=14, pady=(14, 0))

        self.btn_select = tk.Button(btn_frame, text="영역 지정", width=12, command=self.select_region)
        self.btn_capture = tk.Button(btn_frame, text="캡쳐", width=12, command=self.capture)
        self.btn_reset = tk.Button(btn_frame, text="영역 초기화", width=12, command=self.reset_region)
        self.btn_exit = tk.Button(btn_frame, text="종료", width=12, command=self.root.destroy)

        self.btn_select.pack(side=tk.LEFT)
        self.btn_capture.pack(side=tk.LEFT, padx=(10, 0))
        self.btn_reset.pack(side=tk.LEFT, padx=(10, 0))
        self.btn_exit.pack(side=tk.RIGHT)

        # 단축키 설정 (숫자 1을 누르면 캡쳐)
        self.root.bind("1", self.capture)


        hint = tk.Label(
            root,
            text="사용 방법: [영역 지정] → 드래그 → [캡쳐] 혹은 숫자 '1' 키",
            font=("맑은 고딕", 10)
        )
        hint.pack(pady=(16, 0))




    def select_region(self):
        self.status_var.set("상태: 영역 지정 중... (오버레이에서 드래그)")
        self.root.update_idletasks()

        def on_done(region):
            if region is None:
                self.status_var.set("상태: 영역 지정이 취소되었습니다.")
                return

            self.region = region
            r = self.region
            self.status_var.set("상태: 영역이 지정되었습니다. 이제 [캡쳐]를 누르세요.")
            self.region_var.set(f"영역: left={r['left']}, top={r['top']}, width={r['width']}, height={r['height']}")

        # 오버레이 생성 (메인 창 위)
        overlay = RegionSelectorOverlay(on_done=on_done)
        overlay.root.grab_set()  # 오버레이에 입력 포커스 고정

    def reset_region(self):
        self.region = None
        self.status_var.set("상태: 영역이 초기화되었습니다.")
        self.region_var.set("영역: (미지정)")

    def capture(self, event=None):

        if not self.region:
            messagebox.showwarning("경고", "먼저 [영역 지정]을 통해 캡쳐 영역을 지정하세요.")
            return

        # 날짜_시간_마이크로초 형식으로 파일명 생성 (중복 방지)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{timestamp}.png"

        out_path = self.save_dir / filename

        self.status_var.set(f"상태: 캡쳐 중... -> {filename}")
        self.root.update_idletasks()

        try:
            with mss.mss() as sct:
                shot = sct.grab(self.region)
                img = Image.frombytes("RGB", shot.size, shot.rgb)
                img.save(out_path, format="PNG")

            self.status_var.set(f"상태: 저장 완료 -> {filename}")
            # self.img_index 관련 로직 삭제


        except Exception as e:
            messagebox.showerror("오류", f"캡쳐 저장에 실패했습니다.\n\n{type(e).__name__}: {e}")
            self.status_var.set("상태: 캡쳐 실패")


if __name__ == "__main__":
    try:
        # High DPI 설정 (Windows)
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    root = tk.Tk()
    app = App(root)
    root.mainloop()
