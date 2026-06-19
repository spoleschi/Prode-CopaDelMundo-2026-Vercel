import unittest
from datetime import datetime, timedelta, timezone

from api.services.policy_service import (
    can_access_group,
    can_admin_update_result,
    can_predict,
    validate_score,
)
from api.services.scoring_service import calculate_points, sort_ranking_rows
from utils import parse_supabase_datetime


class ScoringTests(unittest.TestCase):
    def test_exact_score_gets_three_points(self):
        self.assertEqual(calculate_points(2, 1, 2, 1), 3)

    def test_correct_result_gets_one_point(self):
        self.assertEqual(calculate_points(3, 1, 2, 0), 1)
        self.assertEqual(calculate_points(1, 1, 0, 0), 1)

    def test_wrong_result_gets_zero_points(self):
        self.assertEqual(calculate_points(1, 2, 2, 1), 0)

    def test_ranking_tiebreakers(self):
        ranking = [
            {"display_name": "B", "points": 5, "exact_count": 1, "result_count": 3, "miss_count": 2},
            {"display_name": "A", "points": 5, "exact_count": 2, "result_count": 0, "miss_count": 4},
            {"display_name": "C", "points": 5, "exact_count": 1, "result_count": 3, "miss_count": 1},
        ]

        sorted_rows = sort_ranking_rows(ranking)

        self.assertEqual([row["display_name"] for row in sorted_rows], ["A", "C", "B"])
        self.assertEqual([row["position"] for row in sorted_rows], [1, 2, 3])


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)

    def match_at(self, dt, is_finished=False):
        return {"match_date": dt.isoformat(), "is_finished": is_finished}

    def test_prediction_allowed_before_start(self):
        match = self.match_at(self.now + timedelta(minutes=1))
        self.assertEqual(can_predict(match, now=self.now), (True, None))

    def test_prediction_blocked_at_start(self):
        match = self.match_at(self.now)
        allowed, reason = can_predict(match, now=self.now)
        self.assertFalse(allowed)
        self.assertIn("comenzo", reason)

    def test_prediction_blocked_after_start(self):
        match = self.match_at(self.now - timedelta(seconds=1))
        allowed, reason = can_predict(match, now=self.now)
        self.assertFalse(allowed)
        self.assertIn("comenzo", reason)

    def test_prediction_blocked_when_finished(self):
        match = self.match_at(self.now + timedelta(hours=1), is_finished=True)
        allowed, reason = can_predict(match, now=self.now)
        self.assertFalse(allowed)
        self.assertIn("finalizado", reason)

    def test_score_validation(self):
        self.assertEqual(validate_score("2"), 2)
        with self.assertRaises(ValueError):
            validate_score("-1")
        with self.assertRaises(ValueError):
            validate_score("x")

    def test_admin_result_blocked_before_start_without_override(self):
        match = self.match_at(self.now + timedelta(minutes=1))
        allowed, reason = can_admin_update_result(match, now=self.now, allow_early=False)
        self.assertFalse(allowed)
        self.assertIn("antes del inicio", reason)

    def test_admin_result_allowed_before_start_with_override(self):
        match = self.match_at(self.now + timedelta(minutes=1))
        self.assertEqual(
            can_admin_update_result(match, now=self.now, allow_early=True),
            (True, None),
        )

    def test_admin_result_allowed_at_start(self):
        match = self.match_at(self.now)
        self.assertEqual(
            can_admin_update_result(match, now=self.now, allow_early=False),
            (True, None),
        )

    def test_group_access_requires_membership(self):
        group = {"id": 1, "name": "Amigos"}
        self.assertEqual(can_access_group(group, True), (True, None))

        allowed, reason = can_access_group(group, False)
        self.assertFalse(allowed)
        self.assertIn("No perteneces", reason)

    def test_supabase_datetime_accepts_variable_microseconds(self):
        dt = parse_supabase_datetime("2026-05-31T22:43:01.82288+00:00")

        self.assertEqual(dt.microsecond, 822880)
        self.assertEqual(dt.tzinfo, timezone.utc)


if __name__ == "__main__":
    unittest.main()
