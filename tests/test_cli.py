"""Submission routing and CLI contracts; these tests do not need installed EDA tools."""
import os
from pathlib import Path
import shlex
import sys
import tempfile
import unittest
from unittest.mock import patch

from typer.testing import CliRunner
from bandgap_cli import ROOT, app
import project
from tools import physical


class CLIContract(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.directory = (Path(self.scratch.name) / 'my entry').resolve()
        self.settings = patch('project.local_settings', return_value={})
        self.settings.start()
        self.addCleanup(self.settings.stop)

    def test_help_needs_no_tools(self):
        with patch('bandgap_cli.subprocess.call') as call:
            for args in [['--help'], ['help'], ['help', 'simulate'], ['extract', '--help'], ['pdk', '--help'], ['magic', '--help']]:
                result = self.runner.invoke(app, args)
                self.assertEqual(result.exit_code, 0, result.output)
                self.assertIn('Usage:', result.output)
            call.assert_not_called()

    def test_simulation_routing_and_exit_code(self):
        project.create_submission(self.directory, 'custom')
        with patch('bandgap_cli.subprocess.call', return_value=7) as call:
            result = self.runner.invoke(app, ['simulate', '-s', str(self.directory), '--out', 'my runs',
                '--mode', 'c', '--profile', 'corners', '--view', 'layout', '--pdk-root', '/alternate pdk',
                '--analysis', 'dc', '--analysis', 'tran'])
            self.assertEqual(result.exit_code, 7, result.output)
            self.assertIn(str(self.directory), result.output)
            self.assertEqual(call.call_args.args[0], [sys.executable, str(ROOT/'tools/check.py'),
                'simulate', '--layout', str(self.directory/'LELOTEMP_BIAS_IBP.mag'), '--out', 'my runs',
                '--track', 'custom', '--mode', 'c', '--profile', 'corners', '--view', 'layout',
                '--analysis', 'dc', '--analysis', 'tran'])
            self.assertEqual(call.call_args.kwargs['env']['PDK_ROOT'], '/alternate pdk')

    def test_invalid_requests_do_not_start_tools(self):
        with patch('bandgap_cli.subprocess.call') as call:
            for args in [['all', '--analysis', 'dc'], ['drc', '-s', '/missing', '--reference'],
                         ['drc', '-s', '/missing'], ['help', 'missing']]:
                result = self.runner.invoke(app, args)
                self.assertNotEqual(result.exit_code, 0, result.output)
            call.assert_not_called()

    def test_track_starters_and_no_overwrite(self):
        for track in ('provided', 'custom'):
            folder = self.directory/track
            result = self.runner.invoke(app, ['new', str(folder), '--track', track])
            self.assertEqual(result.exit_code, 0, result.output)
            layout = folder/'LELOTEMP_BIAS_IBP.mag'
            original = layout.read_bytes()
            self.assertEqual(layout.read_text().count('\nport '), 11)
            self.assertNotIn('\nrect ', layout.read_text())
            if track == 'custom':
                self.assertNotIn('\nuse ', layout.read_text())
                with self.assertRaisesRegex(RuntimeError, 'no physical geometry'):
                    physical.hierarchy(ROOT, layout, ROOT/'pdk', track)
            else:
                self.assertEqual(layout.read_text().count('\nuse '), 125)
                physical.hierarchy(ROOT, layout, ROOT/'pdk', track)
                self.assertEqual(original, (ROOT/'templates/provided'/layout.name).read_bytes())
                self.assertTrue((folder/'tap_palette.mag').is_file())
                self.assertTrue((folder/'inventory.csv').is_file())
            result = self.runner.invoke(app, ['new', str(folder), '--track', track])
            self.assertNotEqual(result.exit_code, 0)
            self.assertEqual(layout.read_bytes(), original)

    def test_default_submission_reference_override_and_separate_outputs(self):
        project.create_submission(self.directory, 'provided')
        with patch('project.local_settings', return_value={'default_submission': str(self.directory)}), \
                patch('bandgap_cli.subprocess.call', return_value=0) as call:
            for args, expected in [(['drc'], self.directory/'runs/rc/typical'),
                                   (['drc', '--mode', 'c'], self.directory/'runs/c/typical'),
                                   (['drc', '--reference'], ROOT/'runs/reference/rc/typical')]:
                result = self.runner.invoke(app, args)
                self.assertEqual(result.exit_code, 0, result.output)
                actual = call.call_args.args[0]
                self.assertEqual(actual[actual.index('--out')+1], str(expected))

    def test_pdk_defaults_and_shell_exports(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(project.pdk_root(), ROOT/'pdk')
        result = self.runner.invoke(app, ['env', '--pdk-root', "/pdk with ' quote"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(shlex.split(result.stdout.splitlines()[0]), ['export', "PDK_ROOT=/pdk with ' quote"])

    def test_magic_selection_and_launch(self):
        project.create_submission(self.directory, 'provided')
        layout = self.directory/'LELOTEMP_BIAS_IBP.mag'
        reference = ROOT/'reference/LELO_TEMP_SKY130A/LELOTEMP_BIAS_IBP.mag'
        with patch('project.local_settings', return_value={
            'default_submission': str(self.directory), 'tools': {'magic': 'eda tools/magic'},
        }), patch('bandgap_cli.subprocess.call', return_value=7) as call:
            for args, expected in [([], layout), (['-s', str(self.directory)], layout),
                                   ([str(self.directory)], layout), ([str(layout)], layout),
                                   (['--reference'], reference)]:
                result = self.runner.invoke(app, ['magic', *args, '--pdk-root', str(ROOT/'pdk')])
                self.assertEqual(result.exit_code, 7, result.output)
                self.assertEqual(call.call_args.args[0], [str(ROOT/'eda tools/magic'),
                    '-rcfile', str(ROOT/'magicrc'), str(ROOT/'tools/magic_open.tcl')])
                self.assertEqual(call.call_args.kwargs['cwd'], expected.parent)
                env = call.call_args.kwargs['env']
                self.assertEqual(env['PDK_ROOT'], str(ROOT/'pdk'))
                self.assertEqual(env['BANDGAP_PDK_ROOT'], str(ROOT/'pdk'))
                self.assertEqual(env['MAGTYPE'], 'mag')
                self.assertEqual(env['BANDGAP_LAYOUT'], expected.name)
            result = self.runner.invoke(app, ['magic', '--magic', '/alternate/magic'])
            self.assertEqual(result.exit_code, 7, result.output)
            self.assertEqual(call.call_args.args[0][0], '/alternate/magic')

    def test_magic_template_and_dry_run(self):
        # A raw template directory needs neither metadata nor physical geometry.
        folder = (Path(self.scratch.name)/"template's files").resolve()
        folder.mkdir()
        layout = folder/'LELOTEMP_BIAS_IBP.mag'
        layout.write_text('magic\ntech sky130A\n<< end >>\n')
        with patch('bandgap_cli.subprocess.call') as call:
            result = self.runner.invoke(app, ['magic', str(folder), '--dry-run',
                '--magic', '/tools with spaces/magic', '--pdk-root', str(ROOT/'pdk')])
            self.assertEqual(result.exit_code, 0, result.output)
            lines = result.stdout.splitlines()
            self.assertEqual(shlex.split(lines[0]), ['cd', str(folder)])
            command = shlex.split(lines[1])
            self.assertEqual(command[0], 'env')
            self.assertIn('PDK_ROOT=' + str(ROOT/'pdk'), command)
            self.assertIn('BANDGAP_LAYOUT=' + layout.name, command)
            self.assertEqual(command[-4:], ['/tools with spaces/magic', '-rcfile', str(ROOT/'magicrc'),
                                           str(ROOT/'tools/magic_open.tcl')])
            call.assert_not_called()

    def test_magic_rejects_invalid_targets_and_handles_missing_executable(self):
        project.create_submission(self.directory, 'custom')
        layout = self.directory/'LELOTEMP_BIAS_IBP.mag'
        with patch('bandgap_cli.subprocess.call') as call:
            for args in [[str(layout), '--reference'], [str(layout), '-s', str(self.directory)],
                         ['--reference', '-s', str(self.directory)], ['/missing.mag'],
                         ['--reference', '--pdk-root', '/missing-pdk']]:
                result = self.runner.invoke(app, ['magic', *args])
                self.assertNotEqual(result.exit_code, 0, result.output)
            layout.unlink()
            result = self.runner.invoke(app, ['magic', '-s', str(self.directory)])
            self.assertNotEqual(result.exit_code, 0, result.output)
            call.assert_not_called()
        with patch('bandgap_cli.subprocess.call', side_effect=FileNotFoundError('missing executable')):
            result = self.runner.invoke(app, ['magic', '--reference'])
            self.assertEqual(result.exit_code, 1, result.output)
            self.assertIn('Could not start Magic', result.output)

    def test_netlist_and_acceptance(self):
        with patch('bandgap_cli.subprocess.call', return_value=0) as call:
            result = self.runner.invoke(app, ['netlist', '--pdk-root', '/pdk', '--xschem', '/eda/xschem'])
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn(str(ROOT/'schematic/netlist.py'), call.call_args.args[0])
            with patch('project.local_settings', return_value={'tools': {'xschem': '/configured/xschem'}}):
                result = self.runner.invoke(app, ['netlist'])
                self.assertEqual(result.exit_code, 0, result.output)
                self.assertIn('/configured/xschem', call.call_args.args[0])
            result = self.runner.invoke(app, ['acceptance', '--keep'])
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertEqual(call.call_args.args[0], [sys.executable, str(ROOT/'tests/acceptance.py'), '--keep'])


if __name__ == '__main__':
    unittest.main()
