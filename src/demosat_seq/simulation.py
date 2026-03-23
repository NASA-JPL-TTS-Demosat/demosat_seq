import pdb
from pathlib import Path
from lxml import etree
import pandas as pd
import plotly.io as pio

from tts_seq.core.simulation import SeqSimulation
from tts_seq.sim_modules.base import Module
from tts_seq.cmd_modeling.commands import EmitEvr, RelWait, FcnCall, SetState, LinearToGoal, Command
from demosat_seq.seqcollection import DemoSatSeqCollection
from demosat_seq.seqdict import DemoSatSeqDict
from demosat_data_utils.evr import EvrContainer
from demosat_dictionary_interface.command import CommandDictionary
from demosat_dictionary_interface.channel import ChannelDictionary
from tts_data_utils.multimission.eha import EhaContainer
from tts_seq.sim_modules.evr import EvrModule
from tts_seq.sim_modules.eha import EhaModule
from tts_seq.sim_modules.seq_no_logic import SeqModule
from tts_seq.sim_modules.cmd import CmdModule
import tts_dtat.plot as dtatplot
from tts_html_utils.core.compiler import HtmlCompiler
from tts_html_utils.core.components.structure import PaneContainer

class DemoSatSeqModule(SeqModule):
	"""
	Specialized sequence engine module for the DemoSat simulation.
	Handles the loading and execution of satellite sequences.
	"""
	class RUN_SEQ(Command):
		"""
		Command implementation to load and trigger a sub-sequence within the engine.
		"""
		def _impl_init(self):
			"""
			Initializes the RUN_SEQ command steps: emitting a load EVR and calling the engine load function.
			"""
			self.add_command_step(EmitEvr, ['SEQ_LOAD_ENGINE', 'ACTIVITY_LO', f'Loading sequence {self.seq_step.args[0].value}'])
			self.add_command_step(FcnCall, [self.module.load_sequence, [self.seq_step.args[0].value], {'uuid_lineage': self.sim.seq_module.engines[self.sequence_engine_id]['provenance']}])

class AdcsModule(Module):
	"""
	Very simple Attitude Determination and Control Subsystem (ADCS) module.
	Manages spacecraft maneuvers.
	"""
	NAME = 'adcs'
	YAW_RATE_DEG_PER_S = 0.75
	def __init__(self, *args, **kwargs):
		"""
		Initializes the ADCS module with default yaw angles and motion state.
		"""
		super().__init__(*args, **kwargs)
		self.yaw = 0 #TO DO: Make this a real incon
		self.goal_yaw = 0
		self.in_motion = False

	class ADCS_YAW(Command):
		"""
		Command to execute a yaw maneuver to a specific relative angle.
		"""
		def _impl_init(self):
			"""
			Defines the maneuver steps: updating the goal, emitting start/stop EVRs, 
			and simulating the linear motion.
			"""
			self.module.goal_yaw += int(self.seq_step.args[0].value)
			self.add_command_step(EmitEvr, ['ADCS_BEGIN_YAW', 'ACTIVITY_LO', f'Beginning yaw of {self.seq_step.args[0].value} degrees at {self.module.YAW_RATE_DEG_PER_S} degrees per second.'])			
			self.add_command_step(LinearToGoal, ['goal_yaw', 'YAW_ANGLE', self.module.YAW_RATE_DEG_PER_S])
			self.add_command_step(EmitEvr, ['ADCS_YAW_COMPLETE', 'ACTIVITY_LO', f'Yaw complete.'])

class SciModule(Module):
	"""
	Science Instrument module.
	Handles science data collection activities and calibrations.
	"""
	NAME = 'sci'

	class DO_SCIENCE(Command):
		"""
		Command to initiate a science activity with a built-in diagnostic delay.
		"""
		def _impl_init(self):
			"""
			Initializes science collection EVRs and a 10-second relative wait for timing verification.
			"""
			self.add_command_step(EmitEvr, ['SCI_BEGIN_SCI', 'ACTIVITY_LO', f'Doing {self.seq_step.args[0].value} science on the {self.seq_step.args[1].value} side.'])
			self.add_command_step(EmitEvr, ['SCI_TIMER_TEST_BEGIN', 'DIAGNOSTIC', f'This EVR happens 10 seconds before the other one.'])
			self.add_command_step(RelWait, [10])
			self.add_command_step(EmitEvr, ['SCI_TIMER_TEST_END', 'DIAGNOSTIC', f'This happened 10 seonds later.'])


	class STOP_SCIENCE(Command):
		"""
		Command to terminate all ongoing science activities.
		"""
		def _impl_init(self):
			"""
			Emits an EVR signaling the cessation of science activities.
			"""
			self.add_command_step(EmitEvr, ('SCI_STOP_SCI', 'ACTIVITY_LO', f'Stopping all science activities.'))

	class DARK_SIDE_CALIBRATION(Command):
		"""
		Command for performing a dark-side instrument calibration.
		"""
		def _impl_init(self):
			"""
			Defines a calibration sequence lasting 120 seconds.
			"""
			self.add_command_step(EmitEvr, ('SCI_START_DS_CAL', 'ACTIVITY_LO', f'Beginning dark side calibration activity.'))
			self.add_command_step(RelWait, [120])
			self.add_command_step(EmitEvr, ('SCI_STOP_DS_CAL', 'ACTIVITY_LO', f'Dark side calibration activity complete.'))

class TelModule(Module):
	"""
	Telemetry and Telecommunications module.
	Manages radio transmission states and Virtual Channel Data Unit (VCDU) settings.
	"""
	NAME = 'tel'

	class TX_POWER(Command):
		"""
		Command to toggle the transmitter power state.
		"""
		def _impl_init(self):
			"""
			Updates the transmitter power state and emits a status EVR.
			"""
			self.add_command_step(SetState, ('TX_POWER_STATE', self.seq_step.args[0].value))
			self.add_command_step(EmitEvr,  ('TEL_TX_PWR_TOGGLE', 'ACTIVITY_LO', f'Transmitter Power is now {self.seq_step.args[0].value}.'))

	class SET_VCDU(Command):
		"""
		Command to update the current Virtual Channel Data Unit (VCDU) ID.
		"""
		def _impl_init(self):
			"""
			Updates the VCDU state and emits a status EVR.
			"""
			self.add_command_step(SetState, ('VCDU_NO', self.seq_step.args[0].value))
			self.add_command_step(EmitEvr,  ('TEL_VCDU_CHANGE', 'ACTIVITY_LO', f'VCDU is now {self.seq_step.args[0].value}.'))

class DemoSatCmdModule(CmdModule):
	"""
	Command routing module for the DemoSat simulation, identifying the main mode channel.
	"""
	MODE_CHANNEL_NAME = 'SC_MODE'

class DemoSatSimulation(SeqSimulation):
	"""
	Top-level simulation class for the DemoSat mission.
	Integrates various modules, dictionaries, and state management.
	"""
	NO_SEQ_ENGINES = 16
	TIME_STEP_S = 1
	EXPECTED_SIM_DICTIONARIES = {}
	DICTIONARY_INTERFACE_CLASSES = {
		'command': CommandDictionary,
		'channel': ChannelDictionary
	}

	def __init__(self, *args, **kwargs):
		"""
		Initializes the simulation environment, defines the initial state (modelled values),
		and maps the specific modules to be used in the sim.
		"""
		super().__init__(*args, **kwargs)
		self.channels = {}
		self.modeled_values = {
			'YAW_ANGLE': 0,
			'TX_POWER_STATE': 'OFF',
			'VCDU_NO': 0,
			'SC_MODE': 'NOMINAL'
		}

		#TO DO: Define the module map as an arg to __init__
		self.module_map = [
			{'cls':  DemoSatSeqModule, 'params': {}},
			{'cls':  DemoSatCmdModule, 'params': {}},
			{'cls':          EhaModule, 'params': {}},
			{'cls':         AdcsModule, 'params': {}},
			{'cls':          SciModule, 'params': {}},
			{'cls':          TelModule, 'params': {}},
			{'cls':          EvrModule, 'params': {}}
		]

		self.init_modules()

		self.cmd_dict = etree.parse(self.seq_collection.command_dict)


	def write_report(self, file_path, title='TTS Seq Simulation Report'):
		"""
		Generates an HTML report summarizing the simulation results.

		Args:
			file_path (str): The destination path for the HTML file.
			title (str): The title of the generated report.
		"""
		html_compiler = HtmlCompiler(title)
		pane_container = PaneContainer()
		pane_container.add_pane(self.plots, 'Simulated EHA')
		pane_container.add_pane(self.evr_table, 'Simulated EVRs')
		pane_container.add_pane(self.cmd_history_table, 'Command History')

		html_compiler.add_body_component(pane_container)
		html_compiler.render_to_file(file_path)

if __name__ == '__main__':
	"""
	Main execution block: Sets up paths, initializes the sequence collection, 
	runs the simulation, and generates the final report.
	"""
	demosat_project_dir = Path(__file__).parent.parent.parent.parent
	cmd_dict_path = demosat_project_dir.joinpath('demosat_dict/src/demosat_dict/dictionaries/v1/command.xml')
	dictionary_set_path = demosat_project_dir.joinpath('demosat_dict/src/demosat_dict/dictionaries/v1/')

	sc = DemoSatSeqCollection('DemoSat Seq Collection', command_dict=cmd_dict_path)
	config_dict = {'command_dictionary_path': cmd_dict_path}
	sc.load_sequences_from_filepath(demosat_project_dir.joinpath('demosat_seqdb'), config_dict)
	demosat_sim = DemoSatSimulation(sc, {}, dictionary_set_path=dictionary_set_path)
	demosat_sim.execute('background', '2023-33T14:00:00')
	demosat_sim.write_report('test.html', 'DemoSat Simulation Report')
	# demosat_sim.eha_container
	# print( [x for x in demosat_sim.channels['TX_POWER'] if x[1] == 'ON'])

	pdb.set_trace()