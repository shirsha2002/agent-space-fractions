"""Tkinter GUI for Space Fractions."""
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from game_core import Game, Question
from storage import Storage
import space_theme as theme
from space_theme import ACCENT, BAD, FONT, GOOD, MUTED, PANEL, TEXT


class SpaceFractionsApp:
    """Main application class."""
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Space Fractions")
        self.scale = max(1.0, self.root.winfo_fpixels('1i') / 96)
        self.root.geometry("%dx%d" % (1000 * self.scale, 720 * self.scale))
        self.root.minsize(int(880 * self.scale), int(660 * self.scale))
        self.root.configure(bg=PANEL)
        self.storage = Storage()
        self.current_user = None
        self.current_role = None
        self.game = None
        self.paused = False
        self.intro_canvas = None
        self.animation_running = False
        self.score_recorded_for_current_game = False  # guard for duplicate score recording
        self.menu_frame = None
        self.game_frame = None
        self.help_frame = None
        self.score_frame = None
        self.admin_frame = None
        self.question_buttons = []
        self.last_choice = None
        self._style_ttk()
        self.background = theme.SpaceBackground(self.root)
        self.background.bind('<Button-1>', lambda e: self.skip_intro() if self.animation_running else None)
        self.show_login()

    def _style_ttk(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use('clam')
        except tk.TclError:
            pass
        style.configure('Treeview', background='#0b1030', fieldbackground='#0b1030', foreground=TEXT,
                        rowheight=28, font=(FONT, 11), borderwidth=0)
        style.configure('Treeview.Heading', background='#1d2452', foreground=ACCENT, font=(FONT, 11, 'bold'),
                        relief='flat')
        style.map('Treeview', background=[('selected', '#2b3577')])

    def clear_widgets(self):
        self.animation_running = False
        self.root.unbind('<Escape>')
        self.root.unbind('<KeyPress>')
        self.root.unbind('<space>')
        self.background.delete('intro')
        for widget in self.root.winfo_children():
            if widget is not self.background:
                widget.destroy()

    def _screen(self, padx=40, pady=30):
        """Create a centred card over the animated backdrop; return (outer, inner)."""
        return theme.card(self.root, padx=padx, pady=pady)

    def show_login(self):
        self.storage.logout()
        self.clear_widgets()
        self.current_user = None
        self.current_role = None
        self.game = None
        self.score_recorded_for_current_game = False
        _, frame = self._screen()
        theme.label(frame, "SPACE FRACTIONS", size=28, bold=True).pack()
        theme.label(frame, "Fraction training for space cadets", size=11, color=MUTED).pack(pady=(2, 18))
        theme.label(frame, "Username", size=10, color=MUTED).pack(anchor='w')
        self.username_entry = theme.entry(frame)
        self.username_entry.pack(pady=(2, 10), ipady=5, fill='x')
        theme.label(frame, "Password", size=10, color=MUTED).pack(anchor='w')
        self.password_entry = theme.entry(frame, show='*')
        self.password_entry.pack(pady=(2, 16), ipady=5, fill='x')
        self.password_entry.bind('<Return>', lambda e: self.login())
        theme.button(frame, "Login", self.login, primary=True).pack(fill='x', pady=(0, 10))
        theme.button(frame, "Register New Player", self.show_register, size=11).pack(fill='x', pady=3)
        theme.button(frame, "First time? Set up admin password", self.first_time_setup, size=10).pack(fill='x', pady=3)
        self.username_entry.focus_set()

    def show_register(self):
        """Simple registration dialog for new player accounts."""
        self.clear_widgets()
        _, frame = self._screen()
        theme.label(frame, "New Cadet Registration", size=22, bold=True).pack(pady=(0, 16))
        theme.label(frame, "Username", size=10, color=MUTED).pack(anchor='w')
        self.reg_username_entry = theme.entry(frame)
        self.reg_username_entry.pack(pady=(2, 10), ipady=5, fill='x')
        theme.label(frame, "Password (min 8 characters)", size=10, color=MUTED).pack(anchor='w')
        self.reg_password_entry = theme.entry(frame, show='*')
        self.reg_password_entry.pack(pady=(2, 10), ipady=5, fill='x')
        theme.label(frame, "Confirm Password", size=10, color=MUTED).pack(anchor='w')
        self.reg_confirm_entry = theme.entry(frame, show='*')
        self.reg_confirm_entry.pack(pady=(2, 16), ipady=5, fill='x')
        theme.button(frame, "Register", self.register_player, primary=True).pack(fill='x', pady=(0, 8))
        theme.button(frame, "Back to Login", self.show_login, size=11).pack(fill='x')

    def register_player(self):
        username = self.reg_username_entry.get().strip()
        password = self.reg_password_entry.get()
        confirm = self.reg_confirm_entry.get()
        if not username or not password:
            messagebox.showerror("Error", "Please fill all fields")
            return
        if password != confirm:
            messagebox.showerror("Error", "Passwords do not match")
            return
        if self.storage.get_user_roles(username) is not None:
            messagebox.showerror("Error", "Username already exists")
            return
        try:
            self.storage.set_user_password(username, password)
            messagebox.showinfo("Success", "Registration successful. Please login.")
            self.show_login()
        except (ValueError, PermissionError) as e:
            messagebox.showerror("Error", str(e))

    def first_time_setup(self):
        # Prompt for new admin password if admin has empty hash
        username = 'admin'
        cur_role = self.storage.get_user_roles(username)
        if cur_role != 'admin':
            messagebox.showerror("Error", "Admin user not found")
            return
        if self.storage.is_admin_password_set(username):
            messagebox.showinfo("Info", "Admin password already set. Please login.")
            return
        password = simpledialog.askstring("Set Admin Password", "Enter new admin password (min 8 characters):", show='*')
        if password:
            try:
                self.storage.set_user_password(username, password)
                messagebox.showinfo("Success", "Admin password set. Please login.")
            except (ValueError, PermissionError) as e:
                messagebox.showerror("Error", str(e))

    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        if not username or not password:
            messagebox.showerror("Error", "Please enter username and password")
            return
        success, role = self.storage.verify_user(username, password)
        if success:
            self.current_user = username
            self.current_role = role
            self.show_intro()
        else:
            messagebox.showerror("Error", "Invalid credentials")

    def logout(self):
        """Logout and return to login screen."""
        self.current_user = None
        self.current_role = None
        self.game = None
        self.score_recorded_for_current_game = False
        self.show_login()

    def show_intro(self):
        self.clear_widgets()
        self.intro_canvas = self.background
        self.animation_running = True
        self.intro_step = 0
        self.root.after(5200, lambda: self.skip_intro() if self.animation_running else None)
        self.root.bind('<space>', lambda e: self.skip_intro())
        self.animate_stars()

    def animate_stars(self):
        """Intro scene: a rocket flies in while the mission briefing fades up."""
        if not self.animation_running:
            return
        c = self.background
        w, h = max(c.winfo_width(), 200), max(c.winfo_height(), 200)
        t = self.intro_step
        c.delete('intro')
        rx = -80 + min(t, 60) * (w * 0.5 + 80) / 60
        ry = h * 0.42 + 6 * ((t % 20) - 10) / 10
        c.create_polygon(rx - 40, ry - 14, rx + 30, ry, rx - 40, ry + 14, fill='#dfe6ff', outline='', tags='intro')
        c.create_polygon(rx - 40, ry - 14, rx - 52, ry - 26, rx - 30, ry - 10, fill=ACCENT, outline='', tags='intro')
        c.create_polygon(rx - 40, ry + 14, rx - 52, ry + 26, rx - 30, ry + 10, fill=ACCENT, outline='', tags='intro')
        c.create_oval(rx - 8, ry - 6, rx + 4, ry + 6, fill='#4057a8', outline='', tags='intro')
        flame = 18 + (t % 4) * 6
        c.create_polygon(rx - 42, ry - 8, rx - 42 - flame, ry, rx - 42, ry + 8, fill='#ffb347', outline='', tags='intro')
        if t > 25:
            shade = min(255, (t - 25) * 12)
            col = '#%02x%02x%02x' % (shade, shade, 255)
            c.create_text(w / 2, h * 0.58, text="Welcome aboard, %s!" % (self.current_user or 'cadet'),
                          fill=col, font=(FONT, 30, 'bold'), tags='intro')
            c.create_text(w / 2, h * 0.58 + 55 * self.scale, text="Your mission: master fractions to power the starship.",
                          fill=col, font=(FONT, 15), tags='intro')
        c.create_text(w / 2, h - 40, text="Press SPACE or click to skip", fill=ACCENT, font=(FONT, 12), tags='intro')
        self.intro_step += 1
        self.root.after(40, self.animate_stars)

    def skip_intro(self):
        self.animation_running = False
        self.root.unbind('<space>')
        self.show_menu()

    def show_menu(self):
        self.clear_widgets()
        self.menu_frame, inner = self._screen(padx=50)
        theme.label(inner, "MAIN MENU", size=28, bold=True).pack()
        theme.label(inner, "Logged in as %s" % (self.current_user or 'guest'), size=11, color=MUTED).pack(pady=(2, 20))
        theme.button(inner, "▶  Play Game", self.start_game, primary=True, size=15, width=20).pack(pady=6)
        theme.button(inner, "?  Help", self.show_help, size=13, width=24).pack(pady=5)
        theme.button(inner, "★  Score History", self.show_scores, size=13, width=24).pack(pady=5)
        if self.current_role == 'admin':
            theme.button(inner, "⚙  Admin Panel", self.show_admin, size=13, width=24).pack(pady=5)
        theme.button(inner, "Logout", self.logout, size=11, width=28).pack(pady=(16, 0))

    def start_game(self):
        questions = self.storage.get_questions()
        if not questions:
            messagebox.showerror("Error", "No questions available")
            return
        self.game = Game(questions)
        self.score_recorded_for_current_game = False
        self.last_choice = None
        self.show_game()

    def show_game(self):
        self.clear_widgets()
        self.game_frame, _ = self._screen(padx=0, pady=0)
        self.game_frame.place_configure(relwidth=0.86, relheight=0.86)
        self.draw_game_canvas()
        self.root.bind('<Escape>', self.pause_game)
        self.root.bind('<KeyPress>', self.on_key_press)

    def on_key_press(self, event):
        """Handle keyboard shortcuts for gameplay."""
        if self.game is None or self.game.state != 'playing':
            return
        if event.char and event.char in '1234567890':
            idx = int(event.char) - 1
            if 0 <= idx < len(self.question_buttons):
                self.question_buttons[idx].invoke()
        elif event.keysym == 'Return':
            if self.game.answered_current:
                self.next_question()

    def _game_body(self):
        body = self.game_frame.winfo_children()[0]
        for widget in body.winfo_children():
            widget.destroy()
        return body

    def draw_game_canvas(self):
        body = self._game_body()
        if self.game.state == 'game_over':
            self.show_game_over()
            return
        total = len(self.game.questions)
        top = tk.Frame(body, bg=PANEL)
        top.pack(fill='x', padx=24, pady=(18, 6))
        theme.label(top, "Score: %d" % self.game.score, size=14, bold=True, color=ACCENT).pack(side='left')
        theme.label(top, "Question %d of %d" % (self.game.index + 1, total), size=13, color=MUTED).pack(side='right')
        bar = tk.Canvas(body, height=8, bg='#0b1030', highlightthickness=0)
        bar.pack(fill='x', padx=24)
        done = self.game.index + (1 if self.game.answered_current else 0)
        bar.bind('<Configure>', lambda e: (bar.delete('all'), bar.create_rectangle(
            0, 0, e.width * done / total, 8, fill=ACCENT, outline='')))
        question = self.game.current_question()
        theme.label(body, question.prompt, size=20, bold=True, wraplength=720, justify='center').pack(pady=(28, 22), padx=24)
        options_frame = tk.Frame(body, bg=PANEL)
        options_frame.pack(pady=4)
        self.question_buttons = []
        for i, opt in enumerate(question.options):
            btn = theme.button(options_frame, "%d.  %s" % (i + 1, opt), lambda o=opt: self.answer_question(o),
                               size=14, width=18)
            btn.grid(row=i // 2, column=i % 2, padx=10, pady=8)
            if self.game.answered_current:
                if question.check(opt):
                    btn.config(bg='#14532d', disabledforeground=GOOD)
                elif opt == self.last_choice:
                    btn.config(bg='#5b1a1a', disabledforeground=BAD)
            self.question_buttons.append(btn)
        if self.game.state == 'paused' or self.game.answered_current:
            for button in self.question_buttons:
                button.config(state='disabled')
        footer = tk.Frame(body, bg=PANEL)
        footer.pack(fill='x', pady=(14, 0), padx=24)
        if self.game.answered_current:
            right = self.last_choice is not None and question.check(self.last_choice)
            verdict = "Correct! +1 point" if right else "Not quite - the answer is %s" % question.answer
            theme.label(footer, verdict, size=14, bold=True, color=GOOD if right else BAD).pack()
            theme.label(footer, question.explanation, size=12, color=MUTED, wraplength=720).pack(pady=(4, 10))
            if self.game.state != 'paused':
                theme.button(footer, "Next Question  (Enter)", self.next_question, primary=True).pack()
        if self.game.state == 'paused':
            theme.label(footer, "PAUSED", size=18, bold=True, color=ACCENT).pack(pady=(6, 4))
            theme.button(footer, "Resume (Esc)", self.resume_game, primary=True).pack(pady=4)
        else:
            theme.button(footer, "Pause (Esc)", self.pause_game, size=11).pack(pady=(10, 0))

    def answer_question(self, option):
        if self.game.state != 'playing':
            return
        try:
            correct = self.game.submit(option)
            self.last_choice = option
            self.show_feedback(correct)
            self.draw_game_canvas()
        except (ValueError, PermissionError) as e:
            messagebox.showerror("Error", str(e))

    def show_feedback(self, correct):
        """Feedback is shown inline by draw_game_canvas; flash the window edge as a cue."""
        self.root.configure(bg='#14532d' if correct else '#5b1a1a')
        self.root.after(250, lambda: self.root.configure(bg=PANEL))

    def next_question(self):
        try:
            self.game.next_question()
            self.last_choice = None
            self.draw_game_canvas()
        except (ValueError, PermissionError) as e:
            messagebox.showerror("Error", str(e))

    def pause_game(self, event=None):
        if self.game is None:
            return
        if self.game.state == 'playing':
            self.game.pause()
            self.draw_game_canvas()
        elif self.game.state == 'paused':
            self.resume_game()

    def resume_game(self):
        if self.game is None or self.game.state != 'paused':
            return
        self.game.resume()
        self.draw_game_canvas()

    def show_game_over(self):
        body = self._game_body()
        final_score = self.game.score
        total = len(self.game.questions)
        frame = tk.Frame(body, bg=PANEL)
        frame.place(relx=0.5, rely=0.5, anchor='center')
        theme.label(frame, "MISSION COMPLETE", size=26, bold=True).pack()
        theme.label(frame, "%d / %d" % (final_score, total), size=48, bold=True, color=ACCENT).pack(pady=(10, 0))
        stars = round(3 * final_score / total) if total else 0
        theme.label(frame, "★" * stars + "☆" * (3 - stars), size=30, color='#facc15').pack()
        # Record score once per game
        if self.current_user and not self.score_recorded_for_current_game:
            self.storage.add_score(self.current_user, final_score, total)
            self.score_recorded_for_current_game = True
        # Feedback message
        if final_score == total:
            feedback = "Perfect! You are a fraction master!"
        elif final_score >= total * 0.7:
            feedback = "Great job! Keep practicing to improve."
        else:
            feedback = "Good effort. Review the explanations and try again!"
        theme.label(frame, feedback, size=14, color=MUTED).pack(pady=(6, 20))
        theme.button(frame, "Play Again", self.start_game, primary=True, width=18).pack(pady=4)
        theme.button(frame, "Back to Menu", self.show_menu, width=22).pack(pady=4)

    def show_help(self):
        self.clear_widgets()
        self.help_frame, inner = self._screen()
        theme.label(inner, "How to Play", size=24, bold=True).pack(anchor='w', pady=(0, 12))
        rules = [
            "You will be asked 10 fraction questions.",
            "Choose the correct answer from the options.",
            "You earn 1 point for each correct answer.",
            "After answering, you will see an explanation.",
            "Pause at any time with Esc.",
            "Your scores are saved automatically.",
            "Admin users can edit questions in the Admin Panel.",
        ]
        for rule in rules:
            theme.label(inner, "•  " + rule, size=13).pack(anchor='w', pady=1)
        theme.label(inner, "Keyboard shortcuts", size=15, bold=True, color=ACCENT).pack(anchor='w', pady=(16, 6))
        for key, action in (("Esc", "Pause / Resume"), ("Space", "Skip intro"),
                            ("1-9", "Select answer"), ("Enter", "Next question (after answering)")):
            row = tk.Frame(inner, bg=PANEL)
            row.pack(anchor='w', pady=2)
            theme.label(row, key, size=11, bold=True, color=TEXT, bg='#1d2452', width=7).pack(side='left')
            theme.label(row, action, size=12, color=MUTED).pack(side='left', padx=10)
        theme.button(inner, "Back", self.show_menu, primary=True, width=14).pack(pady=(20, 0))

    def show_scores(self):
        self.clear_widgets()
        self.score_frame, inner = self._screen()
        theme.label(inner, "Score History", size=24, bold=True).pack(pady=(0, 14))
        if self.current_user:
            rows = self.storage.get_score_history(self.current_user)
        else:
            rows = self.storage.get_score_history()
        if not rows:
            theme.label(inner, "No scores yet - play a mission first!", size=14, color=MUTED).pack(pady=20)
        else:
            tree = ttk.Treeview(inner, columns=('Date', 'Score', 'Total'), show='headings', height=10)
            for col, width in (('Date', 260), ('Score', 100), ('Total', 100)):
                tree.heading(col, text=col)
                tree.column(col, width=width, anchor='center')
            tree.pack(fill='both', expand=True)
            for row in rows[:20]:  # most recent 20
                tree.insert('', 'end', values=(row['date'], row['score'], row['total_questions']))
        theme.button(inner, "Back", self.show_menu, primary=True, width=14).pack(pady=(18, 0))

    def show_admin(self):
        if self.current_role != 'admin':
            messagebox.showerror("Access denied", "Admin only")
            return
        self.clear_widgets()
        self.admin_frame, inner = self._screen(padx=24, pady=20)
        self.admin_frame.place_configure(relwidth=0.86, relheight=0.86)
        theme.label(inner, "Admin Panel - Edit Questions", size=20, bold=True).pack(pady=(0, 12))
        theme.button(inner, "Back", self.show_menu, primary=True, width=14).pack(pady=(12, 0), side='bottom')
        # List questions with edit buttons
        questions = self.storage.get_questions()
        canvas = tk.Canvas(inner, bg=PANEL, highlightthickness=0)
        scrollbar = ttk.Scrollbar(inner, orient='vertical', command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=PANEL)
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        for q in questions:
            row = tk.Frame(scrollable_frame, bg='#161c40', padx=10, pady=6)
            row.pack(fill='x', pady=4)
            theme.label(row, q.qid, size=11, bold=True, color=ACCENT, bg='#161c40', width=6).pack(side='left')
            theme.label(row, q.prompt, size=11, bg='#161c40', width=60, anchor='w').pack(side='left', padx=10)
            theme.button(row, "Edit", lambda qid=q.qid: self.edit_question(qid), size=10).pack(side='right')

    def edit_question(self, qid):
        if self.current_role != 'admin':
            messagebox.showerror("Access denied", "Admin only")
            return
        # Find question
        for q in self.storage.get_questions():
            if q.qid == qid:
                break
        else:
            messagebox.showerror("Error", "Question not found")
            return
        # Create dialog to edit
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Edit {qid}")
        dialog.configure(bg=PANEL, padx=24, pady=16)
        dialog.geometry('560x430')
        fields = []
        for caption, value in (("Prompt", q.prompt), ("Options (comma-separated)", ', '.join(q.options)),
                               ("Correct Answer", q.answer), ("Explanation", q.explanation)):
            theme.label(dialog, caption, size=10, color=MUTED).pack(anchor='w')
            field = theme.entry(dialog, width=56)
            field.pack(pady=(2, 10), ipady=4, fill='x')
            field.insert(0, value)
            fields.append(field)
        prompt_entry, options_entry, answer_entry, explanation_entry = fields
        def save():
            if self.current_role != 'admin':
                messagebox.showerror("Access denied", "Admin only")
                return
            prompt = prompt_entry.get().strip()
            options = [o.strip() for o in options_entry.get().split(',') if o.strip()]
            answer = answer_entry.get().strip()
            explanation = explanation_entry.get().strip()
            if not prompt or len(options) < 2 or not answer:
                messagebox.showerror("Error", "Invalid input")
                return
            try:
                self.storage.update_question(qid, prompt, options, answer, explanation)
                dialog.destroy()
                self.show_admin()  # refresh
            except (ValueError, PermissionError) as e:
                messagebox.showerror("Error", str(e))
        save_btn = theme.button(dialog, "Save", save, primary=True, width=12)
        save_btn.pack(pady=10)
