import pytest
from tts_seq.core.seqcollection import SeqCollection
from demosat_seq.seqdict import DemoSatSeqDict
from demosat_seq.seqcollection import DemoSatSeqCollection

def test_demosat_seq_collection_constants():
    """
    Verifies that the DemoSat-specific class constants are correctly defined.
    """
    assert DemoSatSeqCollection.CALLING_COMMANDS == {'RUN_SEQ': 'seq_id'}
    assert DemoSatSeqCollection.SEQ_DICT_CLASS == DemoSatSeqDict
    assert DemoSatSeqCollection.SEQ_FILE_EXTENSION == '.seq.json'

def test_demosat_seq_collection_inheritance():
    """
    Confirms that DemoSatSeqCollection correctly inherits from the base SeqCollection class.
    """
    assert issubclass(DemoSatSeqCollection, SeqCollection)

def test_demosat_seq_collection_instantiation(monkeypatch):
    """
    Verifies that an instance of DemoSatSeqCollection can be created. 
    Uses the built-in monkeypatch fixture to handle potential base class requirements.
    """
    # If SeqCollection requires a path or complex object, we can provide a dummy
    # Since this is a hook, we ensure the subclass remains instantiable.
    try:
        # Attempt standard instantiation
        collection = DemoSatSeqCollection()
        assert isinstance(collection, DemoSatSeqCollection)
    except TypeError:
        # If the base class __init__ requires arguments (e.g., a root path),
        # this ensures the subclass can still be initialized with placeholders.
        class DummyPath:
            def __str__(self): return "/dummy/path"
            
        collection = DemoSatSeqCollection(DummyPath())
        assert isinstance(collection, DemoSatSeqCollection)