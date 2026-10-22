"""
Flowey talker for Roblox (Undertale style).
Monitors the Roblox process, provides tips / roasts in an overlay window above the game,
and answers your messages (taking game screenshots into account).

Hotkey for a tip right now: f + y (5 second cooldown)
Hide / show window: z - hide, x - show
Chat: click the input field at the bottom of the window, type a message and press Enter.

Installation:  pip install psutil google-genai mss pillow keyboard
Run:           python flowey.py
Next to the script (or in a faces subfolder) you should have:
    flowey-normal-voice.wav  - letter sound
    Flowey 1 <emotion>.png   - Flowey when a letter is NOT playing
    Flowey 2 <emotion>.png   - Flowey when a letter is playing
Controls: drag the window with the mouse, right mouse button = exit.
"""
import ctypes
import io
import os
import queue
import random
import re
import textwrap
import threading
import time
import tkinter as tk
from tkinter import font as tkfont
from ctypes import wintypes

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import psutil

try:
    import keyboard
except ImportError:
    keyboard = None

try:
    from google import genai
    from google.genai import types
    import mss
    from PIL import Image
except ImportError:
    genai = types = mss = Image = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Primary and backup Gemini keys:
API_KEYS = [
    "",  # Primary key
    "",  # Backup key
]
QUOTA_COOLDOWN = 15 * 60        # seconds to leave the key alone after hitting quota limit
BADKEY_COOLDOWN = 6 * 3600      # seconds to leave an invalid / blocked key alone
OTHER_COOLDOWN = 60             # seconds to leave the key alone after another error

PROCESS_NAMES = {"robloxplayerbeta.exe", "robloxplayer.exe", "windows10universal.exe"}
BUBBLE_SECONDS = 8              # how long the replica stays on screen (if window isn't permanent)
ALWAYS_VISIBLE = True           # keep the window with the input field on screen while Roblox is running
MIN_PAUSE, MAX_PAUSE = 45, 150  # pause between random lines (sec)
HOTKEY_COOLDOWN = 5.0           # hotkey cooldown (sec)
HIDE_KEY = "z"                  # hide textbox
SHOW_KEY = "x"                  # show textbox
KEY_LOCK_SECONDS = 4.0          # seconds after phrase end when z and x still don't work

AI_MODEL = "gemini-3.5-flash-lite"  # fast and smart model
AI_INTERVAL = (40, 90)          # pause between AI lines (sec)

PERSONA = (
    "You are Flowey (from Undertale), sitting on the player's shoulder in Roblox. "
    "You speak like a sarcastic, falsely friendly flower: sarcasm, playful mocking, "
    "no real hate speech based on personal traits, no profanity. "
    "Answer in English, without emojis, quotation marks, or asterisks at the beginning. "
)
SYSTEM_PROMPT = (
    PERSONA
    + "You are sent a screenshot of the game. Comment on what is happening: give advice or "
    "a roast. 1-2 short sentences, no more than 140 characters. "
    "Do not repeat what you already said."
)
CHAT_PROMPT = (
    PERSONA
    + "The player is messaging you, with a fresh game screenshot attached (if available). "
    "Reply specifically to the player's question or statement while staying in character as Flowey. "
    "If asked about the game, use the screenshot and actually help, "
    "but with a sarcastic delivery. 1-3 short sentences, no more than 220 characters."
)

# ---------- appearance (Undertale style) ----------
WIN_W, WIN_H = 560, 190         # window size
BOX_COLOR = "#000000"           # textbox background
BORDER_COLOR = "#ffffff"        # textbox border (Undertale: white)
BORDER_WIDTH = 4
CORNER_RADIUS = 14              # corner rounding
TEXT_COLOR = "#ffffff"          # text color
TRANSPARENT_KEY = "#010101"     # transparent color for window corners
FACE_ZOOM = 2                   # how much to upscale Flowey's image
FACE_DIRS = (BASE_DIR, os.path.join(BASE_DIR, "faces"))        # where to look for images
FACE_RE = re.compile(r"^flowey\s*([12])[\s_\-]+(.+)\.png$", re.IGNORECASE)
DEFAULT_EMOTION = "nice"        # default emotion (if AI didn't choose another)

# Exact Undertale font names from your system:
FONT_CANDIDATES = (
    "Determination Mono(RUS BY LYAJK",
    "Determination Mono",
    "DeterminationMono",
    "Consolas",
    "Courier New"
)
FONT_SIZE = 12
CHARS_PER_LINE = 40             # text line width in characters
LINE_PREFIX = "* "              # asterisk before text, like in Undertale

TYPE_DELAY = 45                 # ms between letters
PUNCT_DELAY = {",": 160, ";": 160, ":": 160, "-": 120, "—": 160,
                ".": 320, "!": 320, "?": 320, "…": 320}
NO_SOUND = set(" \n*.,;:!?—-…")   # no sound for these characters

VOICE_FILE = os.path.join(BASE_DIR, "flowey-normal-voice.wav")    # main WAV voice
EMOTION_VOICES = {
    "grin": os.path.join(BASE_DIR, "flowey-grin-voice.wav"),
}

GREET = [
    "Oh, you started Roblox. Finally, I was getting bored on your shoulder.",
    "Hello-hello! Ready to suffer in this game again?",
    "Roblox is open. I can already foresee your fails.",
]
ADVICE = [
    "Advice: don't jump into lava. Although... jump, it's interesting.",
    "Drink some water. Even virtual heroes need hydration.",
    "If it doesn't work out, try pressing buttons with feeling.",
    "Save often. Or don't save, what do I care.",
    "Give your eyes a rest. Look out the window. There's graphics there too.",
    "Don't trust players with a 15-digit name. Just advice.",
    "Don't spend all your Robux at once. Though I would.",
]
ROAST = [
    "Are you even looking where you're going?",
    "Was that your best move? Pathetic.",
    "I'm a flower, and even I would play better.",
    "Woah, you're still here? Determination or stubbornness?",
    "My pot moves more gracefully than that.",
    "Don't worry. Everyone was a noob once. You — still are.",
    "Nice walking style. Just like a lagging NPC.",
]
CHATTER = [
    "You know what we have in common? We're both stuck on your character.",
    "Boring... Show me something interesting.",
    "I was thinking: what if I could speak louder?",
    "Are you still alive? Fine, keep going.",
]
HOUR = [
    "You've been playing for an hour. Maybe stand up, stretch?",
]
TWO_HOURS = [
    "Two hours! I'm starting to worry about you. Well, a little bit.",
]
BYE = [
    "Roblox is closed. I won't miss you. Not at all. Come back.",
    "Leaving already? Fine, I'll watch your avatar.",
    "Bye! It's quiet without you. Too quiet.",
]
ERRORS = [
    "Something broke. And no, I'm not to blame.",
    "Connection with the cosmos lost. Try again.",
]


def find_roblox_window():
    if not hasattr(ctypes, "windll"):
        return 0
    return ctypes.windll.user32.FindWindowW(None, "Roblox")


def grab_roblox_jpeg(require_active=True):
    if not (mss and Image and hasattr(ctypes, "windll")):
        return None
    user32 = ctypes.windll.user32
    hwnd = find_roblox_window()
    if not hwnd:
        return None
    if require_active and user32.GetForegroundWindow() != hwnd:
        return None
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    box = {"left": r.left, "top": r.top,
           "width": r.right - r.left, "height": r.bottom - r.top}
    if box["width"] < 100 or box["height"] < 100:
        return None
    with mss.mss() as sct:
        shot = sct.grab(box)
    img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
    img.thumbnail((1024, 1024))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=70)
    return buf.getvalue()


def roblox_running() -> bool:
    for p in psutil.process_iter(["name"]):
        name = (p.info.get("name") or "").lower()
        if name in PROCESS_NAMES:
            return True
    return False


def classify_error(ex):
    code = getattr(ex, "code", None) or getattr(ex, "status_code", None)
    msg = str(ex).lower()
    if code == 429 or "resource_exhausted" in msg or "quota" in msg or "rate limit" in msg:
        return "quota"
    if (code in (401, 403) or "api key" in msg or "api_key" in msg
            or "permission_denied" in msg or "unauthenticated" in msg
            or "access_token_type_unsupported" in msg):
        return "badkey"
    return "other"


class KeyPool:
    def __init__(self, keys):
        self.lock = threading.Lock()
        self.slots = [{"client": genai.Client(api_key=k), "until": 0.0}
                      for k in keys]
        self.active = None

    def __len__(self):
        return len(self.slots)

    def generate_content(self, **kwargs):
        now = time.time()
        with self.lock:
            order = [i for i, s in enumerate(self.slots) if s["until"] <= now]
            if not order:
                order = list(range(len(self.slots)))
        last_error = None
        for i in order:
            try:
                resp = self.slots[i]["client"].models.generate_content(**kwargs)
            except Exception as ex:
                last_error = ex
                kind = classify_error(ex)
                pause = {"quota": QUOTA_COOLDOWN, "badkey": BADKEY_COOLDOWN}.get(kind, OTHER_COOLDOWN)
                with self.lock:
                    self.slots[i]["until"] = time.time() + pause
                reason = {"quota": "quota exceeded", "badkey": "key not accepted",
                          "other": "error"}[kind]
                print(f"Key #{i + 1}: {reason} ({str(ex)[:120]}). "
                      + ("Trying next..." if i != order[-1] else "No more backups available."))
                continue
            with self.lock:
                self.slots[i]["until"] = 0.0
                if self.active != i:
                    if self.active is not None or i != 0:
                        print(f"Now using key #{i + 1}"
                              + (" (primary)" if i == 0 else " (backup)"))
                    self.active = i
            return resp
        raise last_error


def rounded_rect_points(x1, y1, x2, y2, r):
    return [
        x1 + r, y1, x1 + r, y1, x2 - r, y1, x2 - r, y1,
        x2, y1, x2, y1 + r, x2, y1 + r, x2, y2 - r, x2, y2 - r,
        x2, y2, x2 - r, y2, x2 - r, y2, x1 + r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y2 - r, x1, y1 + r, x1, y1 + r,
        x1, y1,
    ]


def find_faces():
    found = {}
    for folder in FACE_DIRS:
        if not os.path.isdir(folder):
            continue
        for name in sorted(os.listdir(folder)):
            m = FACE_RE.match(name)
            if m:
                emotion = m.group(2).strip().lower()
                found.setdefault(emotion, {})[int(m.group(1))] = os.path.join(folder, name)
    return found


def build_prompt(base, emotions):
    if len(emotions) < 2:
        return base
    example = DEFAULT_EMOTION if DEFAULT_EMOTION in emotions else emotions[0]
    return (
        base
        + "Expression: at the very beginning of the response in square brackets indicate Flowey's "
        "emotion that best fits the replica, for example [" + example + "]. "
        "Available emotions: " + ", ".join(emotions) + ". Choose only from this list, "
        "based on the name's meaning, and change emotion depending on the situation. "
        "If nothing fits, write [" + DEFAULT_EMOTION + "]. "
        "Right after the brackets, write the replica itself. "
    )


def parse_emotion(text, emotions):
    m = re.match(r"^\s*\[\s*([^\]]{1,30}?)\s*\]\s*", text)
    if not m:
        return None, text
    tag = m.group(1).strip().lower()
    rest = text[m.end():].strip()
    if tag in emotions:
        return tag, rest
    return None, rest


def format_line(line):
    wrapped = textwrap.fill(line, width=CHARS_PER_LINE - len(LINE_PREFIX),
                            initial_indent=LINE_PREFIX,
                            subsequent_indent=" " * len(LINE_PREFIX))
    return wrapped


class Flowey:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=TRANSPARENT_KEY)
        try:
            self.root.attributes("-transparentcolor", TRANSPARENT_KEY)
        except tk.TclError:
            pass

        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"{WIN_W}x{WIN_H}+{sw - WIN_W - 20}+{sh - WIN_H - 60}")

        self.canvas = tk.Canvas(self.root, width=WIN_W, height=WIN_H,
                                bg=TRANSPARENT_KEY, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        half = BORDER_WIDTH // 2 + 1
        self.canvas.create_polygon(
            rounded_rect_points(half, half, WIN_W - half, WIN_H - half, CORNER_RADIUS),
            smooth=True, fill=BOX_COLOR, outline=BORDER_COLOR, width=BORDER_WIDTH)

        self.faces = self.load_faces()
        self.emotions = sorted(self.faces)
        self.emotion = DEFAULT_EMOTION if DEFAULT_EMOTION in self.faces else (
            self.emotions[0] if self.emotions else None)
        all_imgs = [img for pair in self.faces.values() for img in pair.values()]
        face_w = max((i.width() for i in all_imgs), default=84)
        face_h = max((i.height() for i in all_imgs), default=88)
        print("Flowey's emotions:", ", ".join(self.emotions) or "no images")

        self.system_prompt = build_prompt(SYSTEM_PROMPT, self.emotions)
        self.chat_prompt = build_prompt(CHAT_PROMPT, self.emotions)

        self.face = tk.Label(self.root, bg=BOX_COLOR, bd=0, highlightthickness=0)
        if self.emotion:
            self.face.config(image=self.faces[self.emotion][1])
        else:
            self.face.config(text="🌼", font=("Segoe UI Emoji", 28), fg="#ffd800")
        self.face.place(x=22, y=20, width=face_w, height=face_h)

        families = set(tkfont.families())
        family = next((f for f in FONT_CANDIDATES if f in families), "Courier New")
        self.font = tkfont.Font(family=family, size=FONT_SIZE)

        text_x = 22 + face_w + 20
        self.text = tk.Label(self.root, text="", font=self.font, bg=BOX_COLOR,
                             fg=TEXT_COLOR, justify="left", anchor="nw",
                             bd=0, highlightthickness=0)
        self.text.place(x=text_x, y=18, width=WIN_W - text_x - 22, height=WIN_H - 18 - 60)

        self.entry = tk.Entry(self.root, font=self.font, bg=BOX_COLOR,
                              fg=TEXT_COLOR, insertbackground=TEXT_COLOR,
                              relief="flat", highlightthickness=1,
                              highlightbackground="#555555",
                              highlightcolor=BORDER_COLOR)
        self.entry.place(x=22, y=WIN_H - 46, width=WIN_W - 44, height=28)
        self.typing = False
        self.entry.bind("<Button-1>", self.focus_entry)
        self.entry.bind("<FocusIn>", lambda e: setattr(self, "typing", True))
        self.entry.bind("<FocusOut>", lambda e: setattr(self, "typing", False))
        self.entry.bind("<Return>", self.on_send)

        self.init_sound()

        self.ai = None
        self.ai_busy = False
        self.chat_busy = False
        self.ai_queue = queue.Queue()
        self.history = []
        self.chat_log = []
        self.last_hotkey_time = 0.0

        keys = []
        for k in list(API_KEYS) + [os.environ.get("GEMINI_API_KEY"),
                                   os.environ.get("GEMINI_API_KEY_2")]:
            k = (k or "").strip()
            if k and k not in keys:
                keys.append(k)
        if not keys:
            print("AI mode disabled: no keys specified in API_KEYS")
        elif genai is None:
            print("AI mode disabled: libraries not installed")
        else:
            try:
                self.ai = KeyPool(keys)
                print(f"AI mode enabled, model: {AI_MODEL}, keys: {len(keys)}"
                      + (" (primary + backup)" if len(keys) > 1 else " (no backup)"))
            except Exception as e:
                print("AI mode disabled, error:", e)

        for w in (self.root, self.canvas, self.face, self.text):
            w.bind("<ButtonPress-1>", self.start_drag)
            w.bind("<B1-Motion>", self.drag)
            w.bind("<Button-3>", lambda e: self.root.destroy())

        self.speaking = False
        self.finished_at = 0.0
        self.key_queue = queue.Queue()

        if keyboard:
            try:
                keyboard.add_hotkey("f+y", self.on_hotkey_pressed)
                print(f"Hotkey F + Y activated (cooldown {HOTKEY_COOLDOWN:.0f} sec)!")
            except Exception as e:
                print("Hotkey F + Y failed to enable:", e)
            try:
                keyboard.on_press_key(HIDE_KEY, lambda _e: self.key_queue.put("hide"))
                keyboard.on_press_key(SHOW_KEY, lambda _e: self.key_queue.put("show"))
                print(f"Keys: {HIDE_KEY.upper()} - hide textbox, {SHOW_KEY.upper()} - show")
            except Exception as e:
                print("Keys z / x failed to enable:", e)

        self.root.withdraw()
        self.running = False
        self.started_at = 0.0
        self.next_talk = 0.0
        self.said_hour = False
        self.said_two = False
        self.hide_job = None
        self.type_job = None
        print("Flowey is running, waiting for Roblox...")
        self.say("Flowey is running. Waiting for you to open Roblox...", hide=True)
        self.tick()
        self.poll_queue()

    def load_faces(self):
        faces = {}
        for emotion, files in find_faces().items():
            pair = {}
            for num, path in files.items():
                try:
                    img = tk.PhotoImage(file=path)
                    pair[num] = img.zoom(FACE_ZOOM, FACE_ZOOM) if FACE_ZOOM > 1 else img
                except tk.TclError as e:
                    print("Failed to load", os.path.basename(path), "-", e)
            if pair:
                pair.setdefault(1, pair.get(2))
                pair.setdefault(2, pair.get(1))
                faces[emotion] = pair
        return faces

    def set_face(self, talking):
        if self.emotion in self.faces:
            self.face.config(image=self.faces[self.emotion][2 if talking else 1])

    def start_drag(self, e):
        self._dx, self._dy = e.x, e.y

    def drag(self, e):
        x = self.root.winfo_x() + e.x - self._dx
        y = self.root.winfo_y() + e.y - self._dy
        self.root.geometry(f"+{x}+{y}")

    def focus_entry(self, _event=None):
        self.root.focus_force()
        self.entry.focus_set()

    def init_sound(self):
        if not os.path.exists(VOICE_FILE):
            print("Warning: file flowey-normal-voice.wav not found!")
        else:
            print("WAV voice successfully connected!")

    def current_voice(self):
        path = EMOTION_VOICES.get(self.emotion)
        return path if path and os.path.exists(path) else VOICE_FILE

    def blip(self):
        path = self.current_voice()
        kind = "waveaudio" if path.lower().endswith(".wav") else "mpegvideo"
        try:
            ctypes.windll.winmm.mciSendStringW("close flowey_voice", None, 0, None)
            ctypes.windll.winmm.mciSendStringW(
                f'open "{path}" type {kind} alias flowey_voice', None, 0, None)
            ctypes.windll.winmm.mciSendStringW("play flowey_voice from 0", None, 0, None)
        except Exception:
            pass

    def say(self, line, hide=None, emotion=None):
        if hide is None:
            hide = not ALWAYS_VISIBLE
        if emotion in self.faces:
            self.emotion = emotion
        elif DEFAULT_EMOTION in self.faces:
            self.emotion = DEFAULT_EMOTION
        if self.hide_job:
            self.root.after_cancel(self.hide_job)
            self.hide_job = None
        if self.type_job:
            self.root.after_cancel(self.type_job)
            self.type_job = None

        self.text.config(text="")
        self.set_face(False)
        self.speaking = True
        self.root.deiconify()
        self.root.attributes("-topmost", True)
        self.type_step(format_line(line), 0, hide)

    def handle_visibility_key(self, action):
        if self.speaking or self.typing:
            return
        if time.time() - self.finished_at < KEY_LOCK_SECONDS:
            return
        if action == "hide":
            if self.hide_job:
                self.root.after_cancel(self.hide_job)
                self.hide_job = None
            self.root.withdraw()
        elif action == "show":
            self.root.deiconify()
            self.root.attributes("-topmost", True)
            if not ALWAYS_VISIBLE and not self.hide_job:
                self.hide_job = self.root.after(BUBBLE_SECONDS * 1000, self.root.withdraw)

    def type_step(self, line, i, hide):
        if i >= len(line):
            self.type_job = None
            self.speaking = False
            self.finished_at = time.time()
            self.set_face(False)
            if hide:
                self.hide_job = self.root.after(BUBBLE_SECONDS * 1000, self.root.withdraw)
            return
        ch = line[i]
        self.text.config(text=line[:i + 1])
        if ch not in NO_SOUND:
            self.blip()
            self.set_face(True)
        else:
            self.set_face(False)
        delay = PUNCT_DELAY.get(ch, TYPE_DELAY)
        self.type_job = self.root.after(delay, self.type_step, line, i + 1, hide)

    def ask_ai(self):
        if self.ai_busy or self.chat_busy:
            return
        self.ai_busy = True
        threading.Thread(target=self._ai_worker, daemon=True).start()

    def _ai_worker(self):
        try:
            jpeg = grab_roblox_jpeg(require_active=True)
            if jpeg is None:
                self.ai_queue.put((None, random.choice(ADVICE + ROAST)))
                return
            said = " | ".join(self.history[-5:]) or "nothing"
            resp = self.ai.generate_content(
                model=AI_MODEL,
                contents=[
                    types.Part.from_bytes(data=jpeg, mime_type="image/jpeg"),
                    f"What is happening right now? Already said: {said}",
                ],
                config=types.GenerateContentConfig(
                    system_instruction=self.system_prompt,
                    max_output_tokens=400,
                ),
            )
            emotion, text = parse_emotion((resp.text or "").strip(), self.faces)
            if text:
                self.ai_queue.put((emotion, text))
        except Exception as ex:
            print("AI error:", ex)
        finally:
            self.ai_busy = False

    def on_send(self, _event=None):
        msg = self.entry.get().strip()
        if not msg:
            return "break"
        if self.chat_busy:
            return "break"
        self.entry.delete(0, "end")
        self.chat_busy = True
        self.say("...", hide=False)
        threading.Thread(target=self._chat_worker, args=(msg,), daemon=True).start()
        self.give_focus_back()
        return "break"

    def give_focus_back(self):
        try:
            hwnd = find_roblox_window()
            if hwnd:
                ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception:
            pass

    def _chat_worker(self, msg):
        try:
            if not self.ai:
                self.ai_queue.put((None, random.choice(ADVICE + ROAST + CHATTER)))
                return
            jpeg = grab_roblox_jpeg(require_active=False)
            dialog = "\n".join(self.chat_log[-6:]) or "nothing yet"
            prompt = f"Previous dialogue:\n{dialog}\n\nPlayer writes: {msg}"
            contents = []
            if jpeg:
                contents.append(types.Part.from_bytes(data=jpeg, mime_type="image/jpeg"))
            else:
                prompt += "\n(No screenshot: Roblox window not found.)"
            contents.append(prompt)

            resp = self.ai.generate_content(
                model=AI_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=self.chat_prompt,
                    max_output_tokens=500,
                ),
            )
            emotion, text = parse_emotion((resp.text or "").strip(), self.faces)
            text = text.lstrip("* ").strip()
            if not text:
                emotion, text = None, random.choice(ERRORS)
            self.chat_log += [f"Player: {msg}", f"Flowey: {text}"]
            self.ai_queue.put((emotion, text))
        except Exception as ex:
            print("Chat error:", ex)
            self.ai_queue.put((None, random.choice(ERRORS)))
        finally:
            self.chat_busy = False

    def on_hotkey_pressed(self):
        if self.typing:
            return
        now = time.time()
        if now - self.last_hotkey_time < HOTKEY_COOLDOWN:
            return
        self.last_hotkey_time = now

        if self.ai:
            self.ask_ai()
        else:
            self.ai_queue.put((None, random.choice(ADVICE + ROAST)))

    def random_line(self):
        return random.choice(ADVICE + ROAST + CHATTER)

    def poll_queue(self):
        while not self.ai_queue.empty():
            emotion, line = self.ai_queue.get()
            self.history.append(line)
            self.say(line, emotion=emotion)
        while not self.key_queue.empty():
            self.handle_visibility_key(self.key_queue.get())
        self.root.after(200, self.poll_queue)

    def tick(self):
        now = time.time()
        alive = roblox_running()

        if alive and not self.running:
            self.running = True
            self.started_at = now
            self.said_hour = self.said_two = False
            self.next_talk = now + random.randint(MIN_PAUSE, MAX_PAUSE)
            self.say(random.choice(GREET))
        elif not alive and self.running:
            self.running = False
            self.say(random.choice(BYE), hide=True)
        elif alive:
            played = now - self.started_at
            if played > 3600 and not self.said_hour:
                self.said_hour = True
                self.say(random.choice(HOUR))
            elif played > 7200 and not self.said_two:
                self.said_two = True
                self.say(random.choice(TWO_HOURS))
            elif now >= self.next_talk and not self.typing:
                if self.ai:
                    self.ask_ai()
                    self.next_talk = now + random.randint(*AI_INTERVAL)
                else:
                    self.say(self.random_line())
                    self.next_talk = now + random.randint(MIN_PAUSE, MAX_PAUSE)

        self.root.after(2000, self.tick)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    try:
        Flowey().run()
    except Exception:
        import traceback
        traceback.print_exc()
        input("\nStartup error (text above). Press Enter to close...")