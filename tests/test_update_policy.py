from datetime import datetime
import unittest
from scraper.update_policy import policy_at, should_run


class UpdatePolicyTests(unittest.TestCase):
    def test_launch_cutoff_uses_vienna_midnight(self):
        before = datetime.fromisoformat('2026-11-18T22:59:59+00:00')
        after = datetime.fromisoformat('2026-11-18T23:00:00+00:00')
        self.assertEqual(policy_at(before)['interval_hours'], 2)
        self.assertEqual(policy_at(after)['interval_hours'], 24)
        self.assertTrue(should_run('schedule', '17 */2 * * *', before))
        self.assertFalse(should_run('schedule', '50 11 * * *', before))
        self.assertFalse(should_run('schedule', '17 */2 * * *', after))
        self.assertTrue(should_run('schedule', '50 11 * * *', after))

    def test_a_delayed_daily_runner_does_not_skip_the_update(self):
        late = datetime.fromisoformat('2026-11-20T15:00:00+00:00')
        self.assertTrue(should_run('schedule', '50 11 * * *', late))
        self.assertFalse(should_run('schedule', 'unknown', late))
        for event in ['push', 'workflow_dispatch']:
            self.assertTrue(should_run(event, '', late))


if __name__ == '__main__': unittest.main()
