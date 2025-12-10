"""
State Machine for Nozzle Control
Manages nozzle state based on detection results
"""
from datetime import datetime


class SmartStateMachine:
    """
    State machine for managing nozzle and fan states
    based on detection results
    """
    def __init__(self):
        self.nozzle_state = 0
        self.fan_speed = 0
        self.current_state = 'IDLE'
        self.current_status = 'N/A'
        self.time_difference = 0
        self.ao_status = 'N/A'
        self.ao_difference = 0
        
        # Timestamps
        self.last_nozzle_update = None
        self.last_ao_update = None
        
        # State history
        self.nozzle_history = []
        self.ao_history = []
    
    def status_send(self, recieved_ns=None, recieved_aos=None):
        """
        Update state machine based on received statuses
        
        :param recieved_ns: Nozzle status ('clear', 'blocked', 'check', 'gravel')
        :param recieved_aos: Action object status ('true' or None)
        """
        now = datetime.now()
        
        # Update nozzle state
        if recieved_ns:
            if recieved_ns == 'clear':
                self.nozzle_state = 1
            elif recieved_ns == 'blocked':
                self.nozzle_state = 2
            elif recieved_ns == 'check':
                self.nozzle_state = 3
            elif recieved_ns == 'gravel':
                self.nozzle_state = 4
            
            self.current_status = recieved_ns
            
            if self.last_nozzle_update:
                self.time_difference = (now - self.last_nozzle_update).total_seconds()
            self.last_nozzle_update = now
            
            self.nozzle_history.append({
                'status': recieved_ns,
                'timestamp': now,
                'state': self.nozzle_state
            })
        
        # Update action object state
        if recieved_aos:
            self.ao_status = recieved_aos
            
            if self.last_ao_update:
                self.ao_difference = (now - self.last_ao_update).total_seconds()
            self.last_ao_update = now
            
            self.ao_history.append({
                'status': recieved_aos,
                'timestamp': now
            })
        
        # Update fan speed based on conditions
        self._update_fan_speed()
        
        # Update overall state
        self._update_current_state()
    
    def _update_fan_speed(self):
        """Update fan speed based on current conditions"""
        if self.nozzle_state == 2:  # blocked
            self.fan_speed = 8  # High speed
        elif self.nozzle_state == 3:  # check
            self.fan_speed = 5  # Medium speed
        elif self.nozzle_state == 1:  # clear
            self.fan_speed = 2  # Low speed
        else:
            self.fan_speed = 0  # Off
    
    def _update_current_state(self):
        """Update current state description"""
        if self.nozzle_state == 0:
            self.current_state = 'IDLE'
        elif self.nozzle_state == 1:
            self.current_state = 'NOZZLE_CLEAR'
        elif self.nozzle_state == 2:
            self.current_state = 'NOZZLE_BLOCKED'
        elif self.nozzle_state == 3:
            self.current_state = 'NOZZLE_CHECK'
        elif self.nozzle_state == 4:
            self.current_state = 'GRAVEL_DETECTED'
    
    def get_current_state(self):
        """Get current state as string"""
        return self.current_state
    
    def get_state_dict(self):
        """Get complete state as dictionary"""
        return {
            'nozzle_state': self.nozzle_state,
            'fan_speed': self.fan_speed,
            'current_state': self.current_state,
            'current_status': self.current_status,
            'time_difference': self.time_difference,
            'ao_status': self.ao_status,
            'ao_difference': self.ao_difference
        }