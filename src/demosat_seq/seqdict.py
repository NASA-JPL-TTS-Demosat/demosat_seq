import pdb
import os
import shutil

from tts_seq.core.seqjson_dict import SeqJsonDict
from tts_seq.core.seqn_dict import SeqNDict

class DemoSatSeqDict(SeqJsonDict):
	"""
	Simple pass-through to SeqJsonDict. This is implemented so
	rather than calling SeqJsonDict directly within DemoSat code,
	we instead call this. That way if we do introduce ant extensions
	in the future, we don't need to run around changing SeqJsonDict
	calls throughout the codebase.
	"""
	TIME_FORMATS = {
		'ABSOLUTE': '%Y-%jT%H:%M:%S',
		'COMMAND_RELATIVE': '%H:%M:%S'
	}


class DemoSatSeqNDict(SeqNDict):
	"""
	Simple pass-through to SeqJsonDict. This is implemented so
	rather than calling SeqJsonDict directly within DemoSat code,
	we instead call this. That way if we do introduce ant extensions
	in the future, we don't need to run around changing SeqJsonDict
	calls throughout the codebase.
	"""
	TIME_FORMATS = {
		'ABSOLUTE': '%Y-%jT%H:%M:%S',
		'COMMAND_RELATIVE': '%H:%M:%S'
	}
