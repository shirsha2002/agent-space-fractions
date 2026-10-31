"""Operator-authored UI regressions after genuine DeepSeek generation.

Tests use only disposable local accounts and databases, not user credentials.
"""
import os
import tempfile
import tkinter as tk
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from storage import Storage
from game_gui import SpaceFractionsApp


class ReviewedUIBehavior(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.temp.name, 'ui.sqlite3')
        self.root = tk.Tk()
        self.root.withdraw()
        self.errors = patch('game_gui.messagebox.showerror').start()
        self.info = patch('game_gui.messagebox.showinfo').start()
        self.factory = patch('game_gui.Storage', lambda: Storage(self.db)).start()
        self.app = SpaceFractionsApp(self.root)

    def tearDown(self):
        for callback in self.root.tk.call('after', 'info'):
            self.root.after_cancel(callback)
        self.app.storage.close()
        self.root.destroy()
        patch.stopall()
        self.temp.cleanup()

    def login_player(self):
        password = 'Disposable-player-test-password'
        self.app.storage.set_user_password('test-player', password)
        self.app.username_entry.insert(0, 'test-player')
        self.app.password_entry.insert(0, password)
        self.app.login()
        self.assertEqual(self.app.current_role, 'user')
        self.assertTrue(self.app.animation_running)
        self.app.skip_intro()

    def test_answer_pause_resume_keyboard_and_binding_lifecycle(self):
        self.login_player()
        self.app.start_game()
        self.app.answer_question(self.app.game.current_question().answer)
        self.assertEqual(self.app.game.score, 1)
        self.app.pause_game(tk.Event())
        self.assertEqual(self.app.game.state, 'paused')
        self.assertTrue(all(str(button.cget('state')) == 'disabled' for button in self.app.question_buttons))
        self.app.on_key_press(SimpleNamespace(char='', keysym='Return'))
        self.assertEqual(self.app.game.index, 0)
        self.app.pause_game(tk.Event())
        self.assertEqual(self.app.game.state, 'playing')
        self.app.on_key_press(SimpleNamespace(char='', keysym='Return'))
        self.assertEqual(self.app.game.index, 1)
        self.assertTrue(self.root.bind('<Escape>'))
        self.app.show_menu()
        self.assertEqual(self.root.bind('<Escape>'), '')
        self.assertEqual(self.root.bind('<KeyPress>'), '')
        self.errors.assert_not_called()

    def test_completed_game_is_saved_once_and_restart_resets_state(self):
        self.login_player()
        self.app.start_game()
        while self.app.game.state != 'game_over':
            self.app.answer_question(self.app.game.current_question().answer)
            self.app.next_question()
        self.assertEqual(self.app.game.score, 10)
        self.app.show_game_over()
        self.assertEqual(len(self.app.storage.get_score_history('test-player')), 1)
        self.app.start_game()
        self.assertEqual((self.app.game.score, self.app.game.index), (0, 0))
        self.assertFalse(self.app.score_recorded_for_current_game)

    def test_player_cannot_open_admin_and_logout_invalidates_session(self):
        self.login_player()
        self.app.show_admin()
        self.app.edit_question('Q1')
        self.assertEqual(self.errors.call_count, 2)
        self.assertFalse(any(isinstance(widget, tk.Toplevel) for widget in self.root.winfo_children()))
        self.app.logout()
        self.assertIsNone(self.app.current_user)
        self.assertIsNone(self.app.current_role)
        self.assertIsNone(self.app.game)
        with self.assertRaises(PermissionError):
            self.app.storage.update_question('Q1', 'Valid prompt', ['1/2', '3/4'], '3/4')

    def test_authenticated_admin_edit_through_dialog_persists(self):
        password = 'Disposable-admin-test-password'
        self.app.storage.set_user_password('admin', password)
        self.app.username_entry.insert(0, 'admin')
        self.app.password_entry.insert(0, password)
        self.app.login()
        self.app.skip_intro()
        self.app.show_admin()
        self.app.edit_question('Q6')
        dialog = next(widget for widget in self.root.winfo_children() if isinstance(widget, tk.Toplevel))
        entries = [widget for widget in dialog.winfo_children() if isinstance(widget, tk.Entry)]
        entries[0].delete(0, tk.END)
        entries[0].insert(0, 'Compare 5/8 with 3/4: choose the larger fraction.')
        save = next(widget for widget in dialog.winfo_children() if isinstance(widget, tk.Button) and widget.cget('text') == 'Save')
        save.invoke()
        reopened = Storage(self.db)
        try:
            question = next(question for question in reopened.get_questions() if question.qid == 'Q6')
            self.assertEqual(question.prompt, 'Compare 5/8 with 3/4: choose the larger fraction.')
            self.assertIn('They are equal', question.options)
        finally:
            reopened.close()
        self.errors.assert_not_called()


if __name__ == '__main__':
    unittest.main()
