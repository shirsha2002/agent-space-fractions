"""Independent behavioural checks, never supplied by the generating model."""

GAME_CONTRACT = r'''
import unittest
from game_core import Question, Game

class IndependentFractionRules(unittest.TestCase):
    def questions(self):
        return [Question("a", "1/2 + 1/4?", ["3/4", "1/4", "1/2", "1"], "3/4", "Add quarters."),
                Question("b", "2/3 - 1/3?", ["1/3", "2/3", "1", "0"], "1/3", "Subtract thirds.")]

    def test_exact_fraction_and_validation(self):
        q = self.questions()[0]
        self.assertTrue(q.check("6/8"))
        self.assertFalse(q.check("1/4"))
        self.assertFalse(q.check("1/0"))
        self.assertFalse(q.check("__import__('os')"))

    def test_score_once_and_states(self):
        game = Game(self.questions())
        self.assertEqual(game.state, "playing")
        game.pause()
        self.assertEqual(game.state, "paused")
        with self.assertRaises(ValueError): game.submit("3/4")
        self.assertEqual(game.score, 0)
        game.resume()
        self.assertTrue(game.submit("3/4"))
        self.assertEqual(game.score, 1)
        with self.assertRaises(ValueError): game.submit("3/4")
        self.assertEqual(game.score, 1)
        game.next_question()
        self.assertEqual(game.index, 1)
        self.assertFalse(game.submit("2/3"))
        game.next_question()
        self.assertEqual(game.state, "game_over")
        self.assertEqual(game.score, 1)
        with self.assertRaises(ValueError): game.submit("1/3")
        game.restart()
        self.assertEqual((game.score, game.index, game.state), (0, 0, "playing"))

    def test_no_skip_unanswered(self):
        game = Game(self.questions())
        with self.assertRaises(ValueError): game.next_question()
        self.assertEqual(game.index, 0)

    def test_empty_bank_rejected(self):
        with self.assertRaises(ValueError): Game([])

if __name__ == "__main__": unittest.main()
'''
