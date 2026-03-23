import pdb
import os
import tempfile
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from tts_seq.authoring.autonomous import AutonomousSeqAuthor
from demosat_seq.seqdict import DemoSatSeqNDict

class DemoSatBackgroundSeqBuilder(AutonomousSeqAuthor):
    """
    Autonomous sequence author for the DemoSat mission.
    
    This class builds a sequence of commands from a schedule of activities,
    recursively processing nested activities.
    """
    def __init__(self, plan: Dict[str, Any], command_dictionary_path: str, seqid: str):
        super().__init__(plan)
        self.command_dictionary_path = command_dictionary_path
        self.seqid = seqid
    
    def build_sequence(self):
        """
        Build a sequence of commands based on the plan.
        
        Returns:
            DemoSatSeqNDict: Sequence dictionary object
        """
        # Get activities from the plan
        activities = self.plan.get('activities', [])
        
        # Build sequence commands
        self.commands = []
        
        # Add header
        self.commands.append(";# DemoSat Background Sequence")
        self.commands.append(f";# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Add mission information if available
        mission = self.plan.get('mission')
        if mission:
            self.commands.append(f";# Mission: {mission}")
        
        # Add schedule time range if available
        start_time = self.plan.get('start_time')
        end_time = self.plan.get('end_time')
        if start_time and end_time:
            self.commands.append(f";# Schedule period: {start_time} to {end_time}")
            
        self.commands.append("")
        
        # Process activities recursively
        self._process_activities(activities)
        
        # Join commands into a sequence
        sequence = "\n".join(self.commands)
        
        # Create a temporary file for the sequence
        fd, tmp_file = tempfile.mkstemp(suffix='.seq')

        with os.fdopen(fd, 'w') as f:
            f.write(sequence)
        
        # Return a DemoSatSeqNDict initialized with the temporary file
        seq =  DemoSatSeqNDict(tmp_file, {'command_dictionary_path': self.command_dictionary_path})
        seq.id = self.seqid #to do; do this idiomatically with seqn
        return seq

    def _process_activities(self, activities):
        """
        Process activities recursively and add their commands to the sequence.
        
        Args:
            activities: List of activities to process
        """
        activities.sort(key=lambda x: x.get('begin_time'))
        
        for activity in activities:
            activity_type = activity.get('type')
            activity_name = activity.get('name')
            activity_command = activity.get('command')
            activity_seqid = activity.get('seqid')
            begin_time = activity.get('begin_time')
            description = activity.get('description')
            
            # Format begin time if available
            time_str = ""
            if begin_time:
                try:
                    dt = datetime.strptime(begin_time, "%Y-%m-%dT%H:%M:%S.%f")
                except ValueError:
                    dt = datetime.strptime(begin_time, "%Y-%m-%dT%H:%M:%S")
                time_str = dt.strftime('A%Y-%jT%H:%M:%S')
            
            # Add activity header with more information
            header = f";# {activity_name} ({activity_type}) at {time_str}"
            self.commands.append(header)
            
            # Add description if available
            if description:
                self.commands.append(f";# Description: {description}")
            
            # Add command if present
            if activity_command:
                self.commands.append(f"{time_str} {activity_command}")
            if activity_seqid:
                self.commands.append(f"{time_str} RUN_SEQ {activity_seqid}")
            # Process child activities if present
            children = activity.get('children', [])
            if children:
                self._process_activities(children)
                
            # Add empty line after activity
            self.commands.append("")