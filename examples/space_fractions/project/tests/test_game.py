# DeepSeek-generated tests with disclosed operator regression fixes; see provenance.
import unittest
import tempfile
import os
import sqlite3
from fractions import Fraction
from game_core import Question, Game
from storage import Storage

class TestQuestion(unittest.TestCase):
    def test_question_creation_valid(self):
        q = Question('q1', 'What is 1/2 + 1/4?', ['1/2', '3/4', '1/4', '2/6'], '3/4')
        self.assertEqual(q.qid, 'q1')
        self.assertEqual(q.prompt, 'What is 1/2 + 1/4?')
        self.assertEqual(q.options, ['1/2', '3/4', '1/4', '2/6'])
        self.assertEqual(q.answer, '3/4')

    def test_question_creation_invalid(self):
        with self.assertRaises(ValueError):
            Question('', 'prompt', ['a', 'b'], 'a')
        with self.assertRaises(ValueError):
            Question('q', '', ['a', 'b'], 'a')
        with self.assertRaises(ValueError):
            Question('q', 'prompt', ['a'], 'a')
        with self.assertRaises(ValueError):
            Question('q', 'prompt', ['a', 'b'], 'c')

    def test_check_exact_match(self):
        q = Question('q', 'p', ['1/2', '3/4'], '1/2')
        self.assertTrue(q.check('1/2'))
        self.assertFalse(q.check('3/4'))

    def test_check_equivalent_fractions(self):
        q = Question('q', 'p', ['1/2', '2/4', '3/5'], '1/2')
        self.assertTrue(q.check('2/4'))
        self.assertFalse(q.check('3/5'))

    def test_check_invalid_input(self):
        q = Question('q', 'p', ['1/2', '2/3'], '1/2')
        self.assertTrue(q.check('1/2'))
        self.assertFalse(q.check('invalid'))
        self.assertFalse(q.check('1/0'))
        self.assertFalse(q.check(None))

class TestGame(unittest.TestCase):
    def setUp(self):
        self.q1 = Question('q1', 'q1', ['1/2', '3/4'], '3/4', 'explain1')
        self.q2 = Question('q2', 'q2', ['1/3', '2/3'], '2/3', 'explain2')
        self.game = Game([self.q1, self.q2])

    def test_game_initialization(self):
        self.assertEqual(self.game.state, 'playing')
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.index, 0)
        self.assertIsNotNone(self.game.current_question())
        self.assertFalse(self.game.answered_current)

    def test_game_rejects_empty_questions(self):
        with self.assertRaises(ValueError):
            Game([])

    def test_submit_correct(self):
        result = self.game.submit('3/4')
        self.assertTrue(result)
        self.assertEqual(self.game.score, 1)
        self.assertTrue(self.game.answered_current)

    def test_submit_incorrect(self):
        result = self.game.submit('1/2')
        self.assertFalse(result)
        self.assertEqual(self.game.score, 0)
        self.assertTrue(self.game.answered_current)

    def test_submit_equivalent_fraction(self):
        result = self.game.submit('6/8')
        self.assertTrue(result)

    def test_submit_duplicate_raises(self):
        self.game.submit('3/4')
        with self.assertRaises(ValueError):
            self.game.submit('3/4')

    def test_submit_paused_raises(self):
        self.game.pause()
        with self.assertRaises(ValueError):
            self.game.submit('3/4')

    def test_submit_game_over_raises(self):
        self.game.submit('3/4')
        self.game.next_question()
        self.game.submit('2/3')
        self.game.next_question()
        with self.assertRaises(ValueError):
            self.game.submit('1/2')

    def test_next_question_normal(self):
        self.game.submit('3/4')
        self.game.next_question()
        self.assertEqual(self.game.index, 1)
        self.assertFalse(self.game.answered_current)
        self.assertEqual(self.game.state, 'playing')

    def test_next_question_last_sets_game_over(self):
        self.game.submit('3/4')
        self.game.next_question()
        self.game.submit('2/3')
        self.game.next_question()
        self.assertEqual(self.game.state, 'game_over')
        self.assertIsNone(self.game.current_question())

    def test_next_question_unanswered_raises(self):
        with self.assertRaises(ValueError):
            self.game.next_question()

    def test_next_question_paused_raises(self):
        self.game.submit('3/4')
        self.game.pause()
        with self.assertRaises(ValueError):
            self.game.next_question()

    def test_pause_resume(self):
        self.game.pause()
        self.assertEqual(self.game.state, 'paused')
        self.game.resume()
        self.assertEqual(self.game.state, 'playing')

    def test_pause_when_not_playing_raises(self):
        self.game.pause()
        with self.assertRaises(ValueError):
            self.game.pause()

    def test_resume_when_not_paused_raises(self):
        with self.assertRaises(ValueError):
            self.game.resume()

    def test_restart(self):
        self.game.submit('3/4')
        self.game.next_question()
        self.game.pause()
        self.game.restart()
        self.assertEqual(self.game.state, 'playing')
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.index, 0)
        self.assertFalse(self.game.answered_current)

class TestStorage(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db_path = os.path.join(self.temp_dir.name, 'test.db')
        self.storage = Storage(self.db_path)

    def tearDown(self):
        self.storage.close()

    def _login_admin(self):
        self.storage.set_user_password('admin', 'Unit-test-admin-password')
        self.assertTrue(self.storage.verify_user('admin', 'Unit-test-admin-password')[0])

    def test_session_authorization_for_question_updates(self):
        args = ('Q1', 'A valid prompt', ['1/2', '3/4'], '3/4')
        with self.assertRaises(PermissionError): self.storage.update_question(*args)
        self.storage.set_user_password('player', 'Unit-test-player-password')
        self.assertTrue(self.storage.verify_user('player', 'Unit-test-player-password')[0])
        with self.assertRaises(PermissionError): self.storage.update_question(*args)
        self._login_admin()
        self.storage.update_question(*args)
        self.storage.logout()
        with self.assertRaises(PermissionError): self.storage.update_question(*args)

    def test_configured_admin_password_cannot_be_reset_without_login(self):
        self._login_admin()
        self.storage.logout()
        with self.assertRaises(PermissionError): self.storage.set_user_password('admin', 'Unauthorized-new-password')
        self.assertTrue(self.storage.verify_user('admin', 'Unit-test-admin-password')[0])

    def test_text_distractor_question_edit_persists(self):
        self._login_admin()
        question = next(q for q in self.storage.get_questions() if q.qid == 'Q6')
        self.storage.update_question(question.qid, question.prompt, question.options, question.answer, 'Reviewed explanation')
        reopened = Storage(self.db_path)
        try:
            self.assertEqual(next(q for q in reopened.get_questions() if q.qid == 'Q6').explanation, 'Reviewed explanation')
        finally:
            reopened.close()

    def test_default_questions_seeded(self):
        questions = self.storage.get_questions()
        self.assertEqual(len(questions), 10)
        self.assertTrue(any(q.qid == 'Q1' for q in questions))

    def test_default_question_bank_is_valid(self):
        """Ensure every default question has exactly one mathematically correct option."""
        for q in self.storage.get_questions():
            correct_count = 0
            for opt in q.options:
                if q.check(opt):
                    correct_count += 1
            self.assertEqual(correct_count, 1, f"Question {q.qid} should have exactly one correct option")

    def test_update_question(self):
        self._login_admin()
        self.storage.update_question('TEST', 'Test prompt', ['1/2', '3/4'], '3/4', 'explanation')
        questions = self.storage.get_questions()
        test_q = next(q for q in questions if q.qid == 'TEST')
        self.assertEqual(test_q.prompt, 'Test prompt')
        self.assertEqual(test_q.answer, '3/4')

    def test_update_question_invalid_answer(self):
        self._login_admin()
        with self.assertRaises(ValueError):
            self.storage.update_question('TEST', 'Test', ['1/2', '3/4'], '1/3', '')

    def test_update_question_blank_qid(self):
        self._login_admin()
        with self.assertRaises(ValueError):
            self.storage.update_question('', 'Test', ['1/2', '3/4'], '3/4', '')

    def test_update_question_blank_prompt(self):
        self._login_admin()
        with self.assertRaises(ValueError):
            self.storage.update_question('TEST', '', ['1/2', '3/4'], '3/4', '')

    def test_update_question_malformed_options(self):
        self._login_admin()
        with self.assertRaises(ValueError):
            self.storage.update_question('TEST', 'Test', ['1/2'], '1/2', '')
        with self.assertRaises(ValueError):
            self.storage.update_question('TEST', 'Test', ['1/2', ''], '1/2', '')
        with self.assertRaises(ValueError):
            self.storage.update_question('TEST', 'Test', ['1/2', '1/2'], '1/2', '')

    def test_update_question_ambiguous_equivalent_options(self):
        self._login_admin()
        with self.assertRaises(ValueError):
            self.storage.update_question('TEST', 'Test', ['1/2', '2/4', '3/5'], '1/2', '')

    def test_update_question_invalid_fraction(self):
        self._login_admin()
        with self.assertRaises(ValueError):
            self.storage.update_question('TEST', 'Test', ['1/0', '3/4'], '3/4', '')

    def test_update_question_preserves_on_failure(self):
        self._login_admin()
        qid = 'Q1'
        original = self.storage.get_questions()[0]
        with self.assertRaises(ValueError):
            self.storage.update_question(qid, 'Bad', ['1/2', '2/4'], '1/2', '')
        questions = self.storage.get_questions()
        restored = next(q for q in questions if q.qid == qid)
        self.assertEqual(restored.prompt, original.prompt)
        self.assertEqual(restored.answer, original.answer)

    def test_add_and_get_score(self):
        self.storage.add_score('alice', 8, 10)
        scores = self.storage.get_score_history('alice')
        self.assertEqual(len(scores), 1)
        self.assertEqual(scores[0]['score'], 8)

    def test_user_password_set_and_verify(self):
        self.storage.set_user_password('bob', 'secret123')
        success, role = self.storage.verify_user('bob', 'secret123')
        self.assertTrue(success)
        self.assertEqual(role, 'user')
        success, _ = self.storage.verify_user('bob', 'wrong')
        self.assertFalse(success)

    def test_short_password_rejected(self):
        with self.assertRaises(ValueError):
            self.storage.set_user_password('eve', 'short')

    def test_admin_unconfigured_cannot_login(self):
        role = self.storage.get_user_roles('admin')
        self.assertEqual(role, 'admin')
        success, role = self.storage.verify_user('admin', '')
        self.assertFalse(success)
        success, role = self.storage.verify_user('admin', 'any')
        self.assertFalse(success)

    def test_admin_password_setup_enables_login(self):
        self.storage.set_user_password('admin', 'newpass123')
        success, role = self.storage.verify_user('admin', 'newpass123')
        self.assertTrue(success)
        self.assertEqual(role, 'admin')
        success, _ = self.storage.verify_user('admin', '')
        self.assertFalse(success)
        success, _ = self.storage.verify_user('admin', 'wrong')
        self.assertFalse(success)

if __name__ == '__main__':
    unittest.main()
