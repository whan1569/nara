from pynput import mouse, keyboard

# 전역 변수로 현재 마우스 위치 저장
current_position = (0, 0)

def on_move(x, y):
    global current_position
    current_position = (x, y)

def on_click(x, y, button, pressed):
    if pressed and button == mouse.Button.left:
        pass  # 클릭 이벤트는 무시함

def on_scroll(x, y, dx, dy):
    pass  # 스크롤 이벤트는 무시함

def on_press(key):
    # 'Q' 키가 눌렸을 때 현재 마우스 좌표 출력
    if key == keyboard.KeyCode.from_char('q'):
        print(f"Q pressed at {current_position}")

# Set up the listeners for mouse and keyboard events
with mouse.Listener(
        on_move=on_move,
        on_click=on_click,
        on_scroll=on_scroll) as mouse_listener, \
     keyboard.Listener(
         on_press=on_press) as keyboard_listener:
    
    # Join listeners to keep the program running
    mouse_listener.join()
    keyboard_listener.join()
