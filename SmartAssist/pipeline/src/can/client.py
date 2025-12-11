"""
CAN Bus Client
Communicates with CAN server via Unix socket

VERIFIED: Exact functionality from original can_client.py
"""
import select
import socket
import json
import time
import threading


class CanClient:
    """
    CAN Client for communicating with CAN server
    Uses Unix domain socket for IPC
    
    VERIFIED: All methods match original can_client.py
    """
    
    def __init__(self, socket_path='/tmp/can_server.sock', client_name='pipeline'):
        """
        Initialize CAN client
        
        :param socket_path: Path to Unix domain socket
        :param client_name: Client identifier
        """
        self.socket_path = socket_path
        self.client_name = client_name
        self.socket = None
        self.connected = False
        self.connection_lock = threading.Lock()
        self.retry_count = 0
        self.max_retries = 3
        
    def connect(self, timeout=1):
        """
        Connect to CAN server with client identification
        
        :param timeout: Connection timeout in seconds
        :return: True if connected, False otherwise
        
        VERIFIED: Exact logic from original
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self.socket.connect(self.socket_path)
                
                # Send identification message
                identification = {
                    'command': 'client_identification',
                    'client_name': self.client_name,
                    'timestamp': time.time()
                }
                
                self.socket.send(json.dumps(identification).encode())
                
                # Wait for acknowledgment
                ready = select.select([self.socket], [], [], 2.0)
                if ready[0]:
                    response_data = self.socket.recv(1024)
                    response = json.loads(response_data.decode('utf-8'))
                    if response.get('status') == 'success':
                        self.connected = True
                        print(f"Connected to CAN server as '{self.client_name}'")
                        return True
                    else:
                        print(f"Server rejected identification: {response}")
                        self.socket.close()
                        self.socket = None
                        return False
                else:
                    print("No identification acknowledgment from server")
                    self.socket.close()
                    self.socket = None
                    return False
                    
            except (socket.error, FileNotFoundError, json.JSONDecodeError) as e:
                if self.socket:
                    self.socket.close()
                    self.socket = None
                time.sleep(0.1)
                
        print(f"Failed to connect to CAN server as '{self.client_name}'")
        return False
        
    def disconnect(self):
        """
        Disconnect from the CAN server with notification
        
        VERIFIED: Exact logic from original
        """
        if self.socket and self.connected:
            try:
                disconnect_msg = {
                    'command': 'client_disconnect',
                    'client_name': self.client_name,
                    'timestamp': time.time()
                }
                self.socket.send(json.dumps(disconnect_msg).encode())
                time.sleep(0.1)
            except:
                pass
                
        if self.socket:
            self.socket.close()
            self.socket = None
        self.connected = False
        print(f"Disconnected from CAN server (client: {self.client_name})")
        
    def _send_request(self, request, max_retries=3):
        """
        Send request to CAN server with retry logic
        
        :param request: Request dictionary
        :param max_retries: Maximum number of retries
        :return: Response dictionary or None
        
        VERIFIED: Exact logic from original
        """
        # Add client identification to all requests
        request['client_name'] = self.client_name
        
        for attempt in range(max_retries):
            try:
                with self.connection_lock:
                    if not self.connected and not self.connect():
                        return None
                    
                    # Send request
                    self.socket.send(json.dumps(request).encode())
                    
                    # Wait for response with timeout
                    ready = select.select([self.socket], [], [], 2.0)
                    if ready[0]:
                        response_data = self.socket.recv(4096)
                        if response_data:
                            response = json.loads(response_data.decode('utf-8'))
                            self.retry_count = 0
                            return response
                        else:
                            # Connection closed by server
                            self.connected = False
                            self.socket.close()
                            self.socket = None
                            if attempt < max_retries - 1:
                                time.sleep(0.5)
                                continue
                    else:
                        # Timeout waiting for response
                        return None
                        
            except (socket.error, json.JSONDecodeError, BrokenPipeError) as e:
                self.connected = False
                if self.socket:
                    self.socket.close()
                    self.socket = None
                
                if attempt < max_retries - 1:
                    time.sleep(0.5)
                else:
                    print(f"Failed to send request after {max_retries} attempts. Giving up.")
                    return None
                    
        self.retry_count += 1
        return None
    
    def get_client_info(self):
        """Get client information"""
        return {
            'client_name': self.client_name,
            'connected': self.connected,
            'socket_path': self.socket_path,
            'retry_count': self.retry_count
        }
        
    def get_all_data(self):
        """Get all CAN data from server"""
        return self._send_request({'command': 'get_all'})
        
    def send_data(self, key, value):
        """Send data to the server"""
        return self._send_request({
            'command': 'send_data',
            'key': key,
            'value': value
        })
    
    def update_fps(self, fps_type, fps_data):
        """Update FPS data on the server"""
        return self._send_request({
            'command': 'update_fps',
            'fps_type': fps_type,
            'fps': fps_data
        })

    def update_camera_status(self, camera):
        """Update camera status on the server"""
        return self._send_request({
            'command': 'update_camera_status',
            'camera': camera,
        })
        
    def update_can_bytes(self, byte_updates):
        """Update CAN byte values on the server"""
        return self._send_request({
            'command': 'update_can_bytes',
            'bytes': byte_updates
        })

    def send_can_0F7(self):
        """Trigger CAN message send on 0x0F7"""
        return self._send_request({'command': 'send_0F7'})

    def send_can_1F7(self):
        """Trigger CAN message send on 0x1F7"""
        return self._send_request({'command': 'send_1F7'})
    
    def send_camera_heartbeat_status(self, key, heartbeat_data):
        """Send camera heartbeat status to the server"""
        return self._send_request({
            'command': 'send_camera_heartbeat_status',
            'key': key,
            'value': heartbeat_data
        })
    
    def start_logging(self):
        """Start logging on the server"""
        return self._send_request({'command': 'start_logging'})
    
    def stop_logging(self):
        """Stop logging on the server"""
        return self._send_request({'command': 'stop_logging'})
    
    def get_override_state(self):
        """Get the current override state from the CAN server"""
        return self._send_request({'command': 'get_override_state'})

    def get_pm_values(self, sensor_id):
        """Get the current PM values from the CAN server"""
        return self._send_request({'command': 'get_pm_values', 'sensor_id': sensor_id})

    def get_sd_usage(self):
        """Get SD card usage status"""
        return self._send_request({'command': 'get_sd_usage'})