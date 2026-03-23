import pdb
from tts_seq.cmd_modeling.commands import CommandStep

class AngularToGoal(CommandStep):
    """
    Models an angular value transitioning linearly over time until it reaches a goal.
    Handles the circular nature of angles, always taking the shortest path.
    
    :param goal_label: Attribute name on the module containing the target angle.
    :type goal_label: str
    :param actual_label: Key in simulation modeled_values to be updated.
    :type actual_label: str
    :param rate_per_s: The angular rate in degrees per second.
    :type rate_per_s: float
    :param min_angle: The minimum angle value (default: -180).
    :type min_angle: float
    :param max_angle: The maximum angle value (default: 180).
    :type max_angle: float
    """
    def __init__(self, module, goal_label, actual_label, rate_per_s, min_angle=-180, max_angle=180):
        super().__init__(module)
        self.goal_label = goal_label
        self.actual_label = actual_label
        self.rate_per_s = rate_per_s
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.range = max_angle - min_angle
    
    def normalize_angle(self, angle):
        """
        Normalize an angle to be within the specified range.
        """
        # Normalize to 0 to range
        normalized = (angle - self.min_angle) % self.range
        # Shift back to min_angle to max_angle
        return normalized + self.min_angle
    
    def shortest_angular_distance(self, from_angle, to_angle):
        """
        Calculate the shortest angular distance between two angles.
        Returns a signed value indicating direction and magnitude.
        """
        # Normalize both angles
        from_angle = self.normalize_angle(from_angle)
        to_angle = self.normalize_angle(to_angle)
        
        # Calculate the direct distance
        direct_dist = to_angle - from_angle
        
        # Calculate the wrapped distance
        if direct_dist > self.range / 2:
            wrapped_dist = direct_dist - self.range
        elif direct_dist < -self.range / 2:
            wrapped_dist = direct_dist + self.range
        else:
            wrapped_dist = direct_dist
            
        return wrapped_dist
    
    def simulate(self):
        """
        Simulation logic to step towards a goal angle via the shortest path.
        """
        goal_value = getattr(self.module, self.goal_label)
        actual_value = self.sim.modeled_values[self.actual_label]
        
        # Calculate the shortest angular distance
        angular_dist = self.shortest_angular_distance(actual_value, goal_value)
        
        # If we're already at the goal or very close
        if abs(angular_dist) < 0.001:
            self.complete = True
            return
            
        # If we're less than one time step away
        step_size = self.rate_per_s * self.sim.TIME_STEP_S
        if abs(angular_dist) <= step_size:
            self.sim.modeled_values[self.actual_label] = goal_value
            self.complete = True
            return
            
        # Otherwise, take a step in the right direction
        if angular_dist > 0:
            self.sim.modeled_values[self.actual_label] += step_size
        else:
            self.sim.modeled_values[self.actual_label] -= step_size
            
        # Normalize the result
        self.sim.modeled_values[self.actual_label] = self.normalize_angle(self.sim.modeled_values[self.actual_label])
