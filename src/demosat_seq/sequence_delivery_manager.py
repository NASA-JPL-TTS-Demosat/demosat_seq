from tts_seq.core.sequence_delivery_manager import SequenceDeliveryManager
from demosat_seq.seqdict import DemoSatSeqNDict
from demosat_seq.seqdict import DemoSatSeqDict

class DemoSatSequenceDeliveryManager(SequenceDeliveryManager):
    SEQUENCE_STATUSES = ['draft', 'delivered', 'approved', 'rejected']
    RESOLUTION_ORDER = ['approved',  'delivered', 'draft']
    DELIVERABLE_STATUSES = ['approved',  'delivered', 'draft']
    ONBOARD_SEQUENCE_DIRECTORY = 'onboard_sequences'
    SEQUENCE_SPAWNING_COMMANDS = {
        'RUN_SEQ': 'seq_id'
    }
    SEQUENCE_SUFFIX = '.seq.json'
    SEQDICT_CLASS = DemoSatSeqDict