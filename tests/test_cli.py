"""Contract tests for the adapter; no PDK or installed EDA tools required."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from typer.testing import CliRunner
from bandgap_cli import ROOT, app


class CLIContract(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()

    def test_help_needs_no_tools(self):
        with patch('bandgap_cli.subprocess.call') as call:
            for args in [['--help'], ['help'], ['help', 'simulate'], ['extract', '--help']]:
                result = self.runner.invoke(app, args)
                self.assertEqual(result.exit_code, 0, result.output)
                self.assertIn('Usage:', result.output)
            call.assert_not_called()

    def test_simulation_arguments_and_exit_code(self):
        with patch('bandgap_cli.subprocess.call', return_value=7) as call:
            result = self.runner.invoke(app, ['simulate', '--layout', 'my entry/top.mag', '--out', 'my runs',
                '--track', 'custom', '--mode', 'c', '--profile', 'corners', '--view', 'layout',
                '--analysis', 'dc', '--analysis', 'tran'])
            self.assertEqual(result.exit_code, 7, result.output)
            self.assertEqual(call.call_args.args[0], [sys.executable, str(ROOT/'tools/check.py'),
                'simulate', '--out', 'my runs', '--track', 'custom', '--mode', 'c',
                '--profile', 'corners', '--view', 'layout', '--layout', 'my entry/top.mag',
                '--analysis', 'dc', '--analysis', 'tran'])

    def test_invalid_requests_do_not_start_tools(self):
        with patch('bandgap_cli.subprocess.call') as call:
            for args in [['all', '--analysis', 'dc'], ['drc', '--track', 'unknown'], ['help', 'missing']]:
                result = self.runner.invoke(app, args)
                self.assertNotEqual(result.exit_code, 0, result.output)
            call.assert_not_called()

    def test_netlist_and_acceptance(self):
        with patch('bandgap_cli.subprocess.call', return_value=0) as call:
            result = self.runner.invoke(app, ['netlist', '--pdk-root', '/pdk', '--xschem', '/eda/xschem'])
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn('--pdk-root', call.call_args.args[0])
            self.assertIn(str(ROOT/'schematic/netlist.py'), call.call_args.args[0])
            result = self.runner.invoke(app, ['acceptance', '--keep'])
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertEqual(call.call_args.args[0], [sys.executable, str(ROOT/'tests/acceptance.py'), '--keep'])


if __name__ == '__main__':
    unittest.main()
