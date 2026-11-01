"""A city may retain a return pass after a separate seasonal offer ends."""
import copy
import json
from pathlib import Path
import unittest
from bus_pages import validate_bus
from outing_supports import program
from prefecture_comparison import comparison_rows

ROOT = Path(__file__).resolve().parents[1]

class EndedBusProgramTests(unittest.TestCase):
    def test_ended_offer_does_not_disable_the_separate_return_pass(self):
        pref = json.loads((ROOT/'data/ibaraki-menkyo-henno.json').read_text())
        bus = json.loads((ROOT/'data/ibaraki-bus.json').read_text())
        taxi = json.loads((ROOT/'data/ibaraki-taxi.json').read_text())
        validate_bus(bus, pref)
        city = next(c for c in bus['cities'] if c['slug'] == 'hitachinaka')
        current, ended = city['programs']
        self.assertTrue(program('ibaraki', 'hitachinaka', 'bus', current, bus['checked'], city)['selectable'])
        historic = program('ibaraki', 'hitachinaka', 'bus', ended, bus['checked'], city)
        self.assertFalse(historic['selectable'])
        self.assertIn('終了', historic['status'])
        rows = [r for r in comparison_rows(pref, bus, taxi) if r['slug'] == 'hitachinaka' and r['kind'] == 'bus']
        self.assertEqual([r['state'] for r in rows], ['document_checked', 'ended'])
        broken = copy.deepcopy(bus)
        next(c for c in broken['cities'] if c['slug'] == 'hitachinaka')['programs'][1]['current'] = 'unsupported'
        with self.assertRaises(AssertionError):
            validate_bus(broken, pref)

if __name__ == '__main__':
    unittest.main()
