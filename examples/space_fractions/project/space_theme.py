"""Animated space backdrop and widget styling for Space Fractions (operator UI patch).

Pure Tkinter: no images or extra dependencies, so the packaged game stays small.
"""
import math
import random
import tkinter as tk

BG_TOP = (6, 8, 26)
BG_BOTTOM = (28, 12, 48)
PANEL = '#111633'
PANEL_EDGE = '#3b4fd8'
TEXT = '#eef1ff'
MUTED = '#9aa6d9'
ACCENT = '#38e8c6'
ACCENT_DARK = '#1fb89b'
BUTTON = '#1d2452'
BUTTON_HOVER = '#2b3577'
GOOD = '#4ade80'
BAD = '#f87171'
FONT = 'Segoe UI'

FRAME_MS = 33


def _hex(rgb):
    return '#%02x%02x%02x' % tuple(max(0, min(255, int(c))) for c in rgb)


def _mix(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


class SpaceBackground(tk.Canvas):
    """Full-window canvas with gradient sky, nebulae, parallax stars and meteors."""

    LAYERS = ((70, 0.15, 1), (45, 0.35, 2), (20, 0.8, 3))  # count, speed px/frame, size

    def __init__(self, master):
        super().__init__(master, highlightthickness=0, bd=0, bg=_hex(BG_TOP))
        self.place(x=0, y=0, relwidth=1, relheight=1)
        self.size = (0, 0)
        self.stars = []
        self.meteor = None
        self.tick = 0
        self.running = True
        self._job = None
        self.bind('<Configure>', self._on_resize)
        self._job = self.master.after(FRAME_MS, self._animate)

    def _on_resize(self, event):
        if (event.width, event.height) != self.size and event.width > 1:
            self.size = (event.width, event.height)
            self._build()

    def _build(self):
        w, h = self.size
        self.delete('scene')
        bands = 48
        for i in range(bands):
            color = _hex(_mix(BG_TOP, BG_BOTTOM, i / (bands - 1)))
            y0 = h * i / bands
            self.create_rectangle(0, y0, w, y0 + h / bands + 1, fill=color, outline='', tags='scene')
        # Soft nebula glows: concentric ovals fading into the sky colour.
        for cx, cy, r, tint in ((0.78, 0.25, 0.32, (90, 40, 160)), (0.18, 0.75, 0.28, (20, 90, 140)),
                                (0.55, 0.9, 0.22, (140, 40, 110))):
            base = _mix(BG_TOP, BG_BOTTOM, cy)
            for step in range(14, 0, -1):
                t = step / 14
                rr = r * min(w, h) * (0.4 + t)
                color = _hex(_mix(base, tint, (1 - t) * 0.55))
                self.create_oval(cx * w - rr * 1.4, cy * h - rr, cx * w + rr * 1.4, cy * h + rr,
                                 fill=color, outline='', tags='scene')
        self._planet(w * 0.12, h * 0.2, min(w, h) * 0.07)
        self.stars = []
        for count, speed, size in self.LAYERS:
            for _ in range(count):
                x, y = random.uniform(0, w), random.uniform(0, h)
                shade = 150 + 35 * size + random.randint(-20, 20)
                item = self.create_oval(x, y, x + size, y + size, fill=_hex((shade, shade, 255)),
                                        outline='', tags=('scene', 'star'))
                self.stars.append([item, speed, size, shade, random.uniform(0, math.tau)])
        self.tag_lower('scene')

    def _planet(self, x, y, r):
        for step in range(10, 0, -1):
            t = step / 10
            self.create_oval(x - r * (1 + t * 0.6), y - r * (1 + t * 0.6), x + r * (1 + t * 0.6), y + r * (1 + t * 0.6),
                             fill=_hex(_mix(BG_TOP, (60, 80, 200), (1 - t) * 0.35)), outline='', tags='scene')
        self.create_oval(x - r, y - r, x + r, y + r, fill='#4057a8', outline='#7891e8', width=2, tags='scene')
        self.create_oval(x - r * 0.6, y - r * 0.7, x + r * 0.1, y - r * 0.1, fill='#5b74c9', outline='', tags='scene')
        self.create_oval(x - r * 1.8, y - r * 0.35, x + r * 1.8, y + r * 0.35, outline='#70e0c4', width=3, tags='scene')

    def _animate(self):
        if not self.running:
            return
        self.tick += 1
        w, h = self.size
        if w > 1:
            for star in self.stars:
                item, speed, size, shade, phase = star
                self.move(item, -speed, 0)
                x0, y0, _, _ = self.coords(item)
                if x0 < -size:
                    self.move(item, w + size, 0)
                if size > 1:
                    glow = shade + 50 * math.sin(self.tick * 0.08 + phase)
                    self.itemconfigure(item, fill=_hex((glow, glow, 255)))
            self._meteor_step(w, h)
        self._job = self.master.after(FRAME_MS, self._animate)

    def _meteor_step(self, w, h):
        if self.meteor is None and random.random() < 0.012:
            x, y = random.uniform(w * 0.3, w * 1.1), random.uniform(-20, h * 0.4)
            self.meteor = [self.create_line(x, y, x + 60, y - 25, fill='#ffffff', width=2,
                                            capstyle='round', tags=('scene', 'meteor')), 0]
            self.tag_raise('meteor', 'star')
        elif self.meteor is not None:
            item, age = self.meteor
            self.move(item, -14, 6)
            fade = max(0, 255 - age * 12)
            self.itemconfigure(item, fill=_hex((fade, fade, min(255, fade + 40))))
            self.meteor[1] += 1
            if age > 20:
                self.delete(item)
                self.meteor = None

    def stop(self):
        self.running = False
        if self._job:
            self.master.after_cancel(self._job)


def card(parent, padx=36, pady=28):
    """A raised panel floating over the backdrop."""
    outer = tk.Frame(parent, bg=PANEL_EDGE, padx=1, pady=1)
    inner = tk.Frame(outer, bg=PANEL, padx=padx, pady=pady)
    inner.pack(fill='both', expand=True)
    outer.place(relx=0.5, rely=0.5, anchor='center')
    return outer, inner


def label(parent, text, size=12, color=TEXT, bold=False, **kw):
    return tk.Label(parent, text=text, fg=color, bg=kw.pop('bg', PANEL),
                    font=(FONT, size, 'bold' if bold else 'normal'), **kw)


def entry(parent, show=None, width=30):
    return tk.Entry(parent, show=show, width=width, font=(FONT, 12), bg='#0b1030', fg=TEXT,
                    insertbackground=ACCENT, relief='flat', highlightthickness=1,
                    highlightbackground='#2a3366', highlightcolor=ACCENT)


def button(parent, text, command, primary=False, size=13, width=None, **kw):
    base, hover = (ACCENT_DARK, ACCENT) if primary else (BUTTON, BUTTON_HOVER)
    fg = '#06121a' if primary else TEXT
    btn = tk.Button(parent, text=text, command=command, font=(FONT, size, 'bold' if primary else 'normal'),
                    bg=base, fg=fg, activebackground=hover, activeforeground=fg, relief='flat', bd=0,
                    cursor='hand2', padx=18, pady=8, disabledforeground='#5d6796', **kw)
    if width:
        btn.config(width=width)
    btn.bind('<Enter>', lambda e: btn.config(bg=hover) if str(btn.cget('state')) != 'disabled' else None)
    btn.bind('<Leave>', lambda e: btn.config(bg=base))
    return btn
