"""Fullscreen drag-to-select rectangle overlay for in-game regions."""
import tkinter as tk
import win32gui


def pick_region(root, hwnd, instruction, on_complete, on_cancel=None):
  """
  Hide root, show overlay. on_complete(rel_x, rel_y, width, height) on success.
  """
  root.withdraw()
  picker = tk.Toplevel()
  picker.attributes('-fullscreen', True)
  picker.attributes('-alpha', 0.5)
  picker.configure(bg='black')
  picker.attributes('-topmost', True)

  canvas = tk.Canvas(picker, bg='black', highlightthickness=0, bd=0)
  canvas.pack(fill='both', expand=True)

  label = tk.Label(
    picker, text=instruction, font=('Arial', 16), fg='white', bg='black',
  )
  label.place(relx=0.5, rely=0.1, anchor='center')

  info = tk.Label(picker, text='', font=('Arial', 12), fg='yellow', bg='black')
  info.place(relx=0.5, rely=0.15, anchor='center')

  rect_id = None
  start_x = None
  start_y = None
  dragging = False

  def finish(restore=True):
    picker.destroy()
    if restore:
      root.deiconify()

  def on_press(event):
    nonlocal start_x, start_y, dragging, rect_id
    start_x = event.x_root
    start_y = event.y_root
    dragging = True
    if rect_id:
      canvas.delete(rect_id)
      rect_id = None

  def on_motion(event):
    nonlocal rect_id, start_x, start_y, dragging
    if not dragging or start_x is None:
      return
    try:
      wx, wy, _, _ = win32gui.GetWindowRect(hwnd)
      min_x = min(start_x, event.x_root)
      max_x = max(start_x, event.x_root)
      min_y = min(start_y, event.y_root)
      max_y = max(start_y, event.y_root)
      rel_x = min_x - wx
      rel_y = min_y - wy
      w = max_x - min_x
      h = max_y - min_y
      info.configure(text=f'Position: ({rel_x}, {rel_y}) | Size: {w}x{h} px')
      if rect_id:
        canvas.delete(rect_id)
      rect_id = canvas.create_rectangle(min_x, min_y, max_x, max_y, outline='red', width=2)
    except Exception:
      pass

  def on_release(event):
    nonlocal dragging, start_x, start_y
    if not dragging or start_x is None:
      return
    try:
      wx, wy, _, _ = win32gui.GetWindowRect(hwnd)
      min_x = min(start_x, event.x_root)
      max_x = max(start_x, event.x_root)
      min_y = min(start_y, event.y_root)
      max_y = max(start_y, event.y_root)
      rel_x = min_x - wx
      rel_y = min_y - wy
      width = max(max_x - min_x, 10)
      height = max(max_y - min_y, 5)
      finish()
      on_complete(rel_x, rel_y, width, height)
    except Exception as exc:
      print(f'[region_picker] error: {exc}')
      finish()
      if on_cancel:
        on_cancel()
    dragging = False
    start_x = None
    start_y = None

  def on_escape(_event=None):
    finish()
    if on_cancel:
      on_cancel()

  picker.bind('<Button-1>', on_press)
  picker.bind('<B1-Motion>', on_motion)
  picker.bind('<ButtonRelease-1>', on_release)
  picker.bind('<Escape>', on_escape)
  picker.focus_set()
