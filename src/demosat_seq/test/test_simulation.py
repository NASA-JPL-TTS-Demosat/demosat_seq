import pytest
from unittest.mock import MagicMock, patch, call
import sys
import demosat_dict
from pathlib import Path
from datetime import datetime, timedelta

from tts_seq.cmd_modeling.commands import EmitEvr, RelWait, FcnCall, SetState, LinearToGoal

from demosat_seq.simulation import (
    DemoSatSeqModule,
    AdcsModule,
    SciModule,
    TelModule,
    DemoSatCmdModule,
    DemoSatSimulation
)

# Helper to instantiate a command without invoking its base __init__
def create_command_instance(cls, module=None, sim=None, seq_step_args=None):
    cmd = cls.__new__(cls)
    cmd.module = module if module else MagicMock()
    cmd.sim = sim if sim else MagicMock()
    cmd.add_command_step = MagicMock()
    
    # Mock seq_step
    cmd.seq_step = MagicMock()
    if seq_step_args:
        # Create args with .value attributes
        cmd.seq_step.args = [MagicMock(value=arg) for arg in seq_step_args]
        
    return cmd

class TestDemoSatSeqModule:
    def test_run_seq_impl_init(self):
        """Test RUN_SEQ command initialization."""
        sim = MagicMock()
        # Mocking the engine provenance lookup
        sim.seq_module.engines = {1: {'provenance': 'test_provenance'}}
        
        module = MagicMock()
        module.load_sequence = MagicMock()

        cmd = create_command_instance(DemoSatSeqModule.RUN_SEQ, module=module, sim=sim, seq_step_args=['my_sequence'])
        cmd.sequence_engine_id = 1 # Set the engine ID for the lookup

        # Execute
        cmd._impl_init()

        # Verify
        assert cmd.add_command_step.call_count == 2
        
        # Check first step: EmitEvr
        cmd.add_command_step.assert_any_call(
            EmitEvr, 
            ['SEQ_LOAD_ENGINE', 'ACTIVITY_LO', 'Loading sequence my_sequence']
        )
        
        # Check second step: FcnCall
        # Verify it calls module.load_sequence with the sequence name and provenance
        args, _ = cmd.add_command_step.call_args_list[1]
        assert args[0] == FcnCall
        assert args[1][0] == module.load_sequence # The function to call
        assert args[1][1] == ['my_sequence']      # The args for the function
        assert args[1][2] == {'uuid_lineage': 'test_provenance'} # kwargs

class TestAdcsModule:
    def test_init(self):
        """Test ADCS module initialization."""
        # Pass a mock simulator as required by the base Module class
        module = AdcsModule(MagicMock())
        assert module.yaw == 0
        assert module.goal_yaw == 0
        assert module.in_motion is False
        assert module.NAME == 'adcs'

    def test_adcs_yaw_impl_init(self):
        """Test ADCS_YAW command logic."""
        # Pass a mock simulator as required by the base Module class
        module = AdcsModule(MagicMock())
        module.goal_yaw = 10
        module.YAW_RATE_DEG_PER_S = 1.5
        
        # Command to add 5 degrees
        cmd = create_command_instance(AdcsModule.ADCS_YAW, module=module, seq_step_args=[5])
        
        # Execute
        cmd._impl_init()
        
        # Verify goal_yaw updated
        assert module.goal_yaw == 15 # 10 + 5
        
        # Verify steps
        assert cmd.add_command_step.call_count == 3
        
        # 1. Begin EVR
        cmd.add_command_step.assert_any_call(
            EmitEvr, 
            ['ADCS_BEGIN_YAW', 'ACTIVITY_LO', 'Beginning yaw of 5 degrees at 1.5 degrees per second.']
        )
        
        # 2. Linear Motion
        cmd.add_command_step.assert_any_call(
            LinearToGoal, 
            ['goal_yaw', 'YAW_ANGLE', 1.5]
        )
        
        # 3. Complete EVR
        cmd.add_command_step.assert_any_call(
            EmitEvr, 
            ['ADCS_YAW_COMPLETE', 'ACTIVITY_LO', 'Yaw complete.']
        )

class TestSciModule:
    def test_do_science_impl_init(self):
        """Test DO_SCIENCE command logic."""
        # args: [science_type, side]
        cmd = create_command_instance(SciModule.DO_SCIENCE, seq_step_args=['Optical', 'Nadir'])
        
        cmd._impl_init()
        
        assert cmd.add_command_step.call_count == 4
        
        cmd.add_command_step.assert_has_calls([
            call(EmitEvr, ['SCI_BEGIN_SCI', 'ACTIVITY_LO', 'Doing Optical science on the Nadir side.']),
            call(EmitEvr, ['SCI_TIMER_TEST_BEGIN', 'DIAGNOSTIC', 'This EVR happens 10 seconds before the other one.']),
            call(RelWait, [10]),
            call(EmitEvr, ['SCI_TIMER_TEST_END', 'DIAGNOSTIC', 'This happened 10 seonds later.'])
        ])

    def test_stop_science_impl_init(self):
        """Test STOP_SCIENCE command logic."""
        cmd = create_command_instance(SciModule.STOP_SCIENCE)
        
        cmd._impl_init()
        
        cmd.add_command_step.assert_called_once_with(
            EmitEvr, 
            ('SCI_STOP_SCI', 'ACTIVITY_LO', 'Stopping all science activities.')
        )

    def test_dark_side_calibration_impl_init(self):
        """Test DARK_SIDE_CALIBRATION command logic."""
        cmd = create_command_instance(SciModule.DARK_SIDE_CALIBRATION)
        
        cmd._impl_init()
        
        assert cmd.add_command_step.call_count == 3
        cmd.add_command_step.assert_any_call(RelWait, [120])
        cmd.add_command_step.assert_any_call(EmitEvr, ('SCI_START_DS_CAL', 'ACTIVITY_LO', 'Beginning dark side calibration activity.'))
        cmd.add_command_step.assert_any_call(EmitEvr, ('SCI_STOP_DS_CAL', 'ACTIVITY_LO', 'Dark side calibration activity complete.'))

class TestTelModule:
    def test_tx_power_impl_init(self):
        """Test TX_POWER command logic."""
        cmd = create_command_instance(TelModule.TX_POWER, seq_step_args=['ON'])
        
        cmd._impl_init()
        
        assert cmd.add_command_step.call_count == 2
        cmd.add_command_step.assert_any_call(SetState, ('TX_POWER_STATE', 'ON'))
        cmd.add_command_step.assert_any_call(EmitEvr, ('TEL_TX_PWR_TOGGLE', 'ACTIVITY_LO', 'Transmitter Power is now ON.'))

    def test_set_vcdu_impl_init(self):
        """Test SET_VCDU command logic."""
        cmd = create_command_instance(TelModule.SET_VCDU, seq_step_args=[42])
        
        cmd._impl_init()
        
        assert cmd.add_command_step.call_count == 2
        cmd.add_command_step.assert_any_call(SetState, ('VCDU_NO', 42))
        cmd.add_command_step.assert_any_call(EmitEvr, ('TEL_VCDU_CHANGE', 'ACTIVITY_LO', 'VCDU is now 42.'))

class TestDemoSatCmdModule:
    def test_mode_channel_name(self):
        assert DemoSatCmdModule.MODE_CHANNEL_NAME == 'SC_MODE'

class TestDemoSatSimulation:
    @patch('demosat_seq.simulation.etree.parse')
    @patch('demosat_seq.simulation.DemoSatSimulation.init_modules')
    def test_init(self, mock_init_modules, mock_etree_parse):
        """Test simulation initialization including module map and modeled values."""
        seq_collection = MagicMock()
        seq_collection.command_dict = "dummy_path.xml"
        
        # Instantiate
        dict_pkg_dir = Path(demosat_dict.__file__).parent
        dictionary_set_path = dict_pkg_dir.joinpath('dictionaries/v1/')

        sim = DemoSatSimulation(seq_collection, {}, dictionary_set_path)
        
        # Verify modeled values defaults
        assert sim.modeled_values['YAW_ANGLE'] == 0
        assert sim.modeled_values['TX_POWER_STATE'] == 'OFF'
        assert sim.modeled_values['VCDU_NO'] == 0
        assert sim.modeled_values['SC_MODE'] == 'NOMINAL'
        
        # Verify module map construction
        expected_modules = [
            DemoSatSeqModule, DemoSatCmdModule, 
            AdcsModule, SciModule, TelModule
        ]
        
        mapped_classes = [entry['cls'] for entry in sim.module_map]
        for module_cls in expected_modules:
            assert module_cls in mapped_classes
            
        mock_init_modules.assert_called_once()
        mock_etree_parse.assert_any_call("dummy_path.xml")

    @patch('demosat_seq.simulation.HtmlCompiler')
    @patch('demosat_seq.simulation.PaneContainer')
    def test_write_report(self, MockPaneContainer, MockHtmlCompiler):
        """Test report generation."""
        sim = MagicMock(spec=DemoSatSimulation)
        sim.plots = "mock_plots"
        sim.evr_table = "mock_evr_table"
        sim.cmd_history_table = "mock_cmd_table"
        
        file_path = "test_report.html"
        
        # Execute
        DemoSatSimulation.write_report(sim, file_path)
        
        # Verify PaneContainer interactions
        pane_instance = MockPaneContainer.return_value
        pane_instance.add_pane.assert_any_call("mock_plots", 'Simulated EHA')
        pane_instance.add_pane.assert_any_call("mock_evr_table", 'Simulated EVRs')
        
        # Verify HtmlCompiler interactions
        compiler_instance = MockHtmlCompiler.return_value
        compiler_instance.add_body_component.assert_called_with(pane_instance)
        compiler_instance.render_to_file.assert_called_with(file_path)