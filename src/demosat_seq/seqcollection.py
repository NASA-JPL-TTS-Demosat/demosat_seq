import pdb
from pathlib import Path

from tts_seq.core.seqcollection import SeqCollection
from demosat_seq.seqdict import DemoSatSeqDict

class DemoSatSeqCollection(SeqCollection):
	"""
	DemoSat implementation of SeqCollection. Needed to set DemoSat-specific 
	globals. This also provides a hook for future DemoSat-specific extension.
	"""
	CALLING_COMMANDS = {'RUN_SEQ': 'seq_id'}
	SEQ_DICT_CLASS = DemoSatSeqDict
	SEQ_FILE_EXTENSION = '.seq.json'
