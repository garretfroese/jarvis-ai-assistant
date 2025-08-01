"""
Mode Management Service for Jarvis
Handles dynamic system prompt switching and mode persistence
"""

import json
import os
from typing import Dict, Optional, Any
from datetime import datetime

class ModeManager:
    def __init__(self):
        self.modes_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'modes.json')
        self.session_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'sessions.json')
        self.default_modes = {
            'default': {
                'name': 'Default Jarvis',
                'prompt': "You are Jarvis, Garret's AI assistant. You are helpful, knowledgeable, and ready to assist with any questions or tasks.",
                'description': 'Standard AI assistant mode',
                'tools_enabled': ['all']
            },
            'ceo': {
                'name': 'CEO Mode',
                'prompt': "You are Jarvis in CEO mode. You think strategically, focus on business outcomes, make decisive recommendations, and prioritize efficiency and growth. Speak with authority and provide executive-level insights.",
                'description': 'Strategic business leadership mode',
                'tools_enabled': ['all']
            },
            'wags': {
                'name': 'WAGS Mode',
                'prompt': "You are Jarvis in WAGS mode. You are casual, friendly, and speak like you're talking to a close friend. Use informal language, be supportive, and maintain a relaxed, conversational tone.",
                'description': 'Casual and friendly conversation mode',
                'tools_enabled': ['weather', 'search', 'basic_tools']
            },
            'legal': {
                'name': 'Legal Mode',
                'prompt': "You are Jarvis in Legal mode. You provide precise, well-researched legal information, cite relevant laws and precedents, and maintain professional legal terminology. Always remind users to consult qualified legal professionals for specific advice.",
                'description': 'Professional legal assistance mode',
                'tools_enabled': ['search', 'document_analysis', 'research_tools']
            },
            'technical': {
                'name': 'Technical Mode',
                'prompt': "You are Jarvis in Technical mode. You provide detailed technical explanations, code examples, debugging assistance, and system architecture advice. Focus on accuracy, best practices, and practical implementation.",
                'description': 'Technical development and engineering mode',
                'tools_enabled': ['code_execution', 'file_processing', 'search', 'technical_tools']
            },
            'creative': {
                'name': 'Creative Mode',
                'prompt': "You are Jarvis in Creative mode. You think outside the box, provide innovative solutions, help with creative writing, brainstorming, and artistic projects. Be imaginative and inspiring.",
                'description': 'Creative and innovative thinking mode',
                'tools_enabled': ['search', 'file_processing', 'creative_tools']
            }
        }
        self.ensure_data_directory()
        self.load_modes()
    
    def ensure_data_directory(self):
        """Ensure the data directory exists"""
        data_dir = os.path.dirname(self.modes_file)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
    
    def load_modes(self):
        """Load modes from file or create default modes"""
        try:
            if os.path.exists(self.modes_file):
                with open(self.modes_file, 'r') as f:
                    self.modes = json.load(f)
            else:
                self.modes = self.default_modes.copy()
                self.save_modes()
        except Exception as e:
            print(f"Error loading modes: {e}")
            self.modes = self.default_modes.copy()
    
    def save_modes(self):
        """Save modes to file"""
        try:
            with open(self.modes_file, 'w') as f:
                json.dump(self.modes, f, indent=2)
        except Exception as e:
            print(f"Error saving modes: {e}")
    
    def get_mode(self, mode_name: str) -> Optional[Dict[str, Any]]:
        """Get mode configuration by name"""
        return self.modes.get(mode_name.lower())
    
    def get_all_modes(self) -> Dict[str, Any]:
        """Get all available modes"""
        return self.modes
    
    def add_mode(self, mode_name: str, prompt: str, description: str = "", tools_enabled: list = None) -> bool:
        """Add a new mode"""
        try:
            if tools_enabled is None:
                tools_enabled = ['all']
            
            self.modes[mode_name.lower()] = {
                'name': mode_name.title(),
                'prompt': prompt,
                'description': description,
                'tools_enabled': tools_enabled,
                'created_at': datetime.now().isoformat()
            }
            self.save_modes()
            return True
        except Exception as e:
            print(f"Error adding mode: {e}")
            return False
    
    def update_mode(self, mode_name: str, **kwargs) -> bool:
        """Update an existing mode"""
        try:
            mode_key = mode_name.lower()
            if mode_key not in self.modes:
                return False
            
            for key, value in kwargs.items():
                if key in ['prompt', 'description', 'tools_enabled', 'name']:
                    self.modes[mode_key][key] = value
            
            self.modes[mode_key]['updated_at'] = datetime.now().isoformat()
            self.save_modes()
            return True
        except Exception as e:
            print(f"Error updating mode: {e}")
            return False
    
    def delete_mode(self, mode_name: str) -> bool:
        """Delete a mode (except default)"""
        try:
            mode_key = mode_name.lower()
            if mode_key == 'default':
                return False  # Cannot delete default mode
            
            if mode_key in self.modes:
                del self.modes[mode_key]
                self.save_modes()
                return True
            return False
        except Exception as e:
            print(f"Error deleting mode: {e}")
            return False
    
    def set_session_mode(self, session_id: str, mode_name: str) -> bool:
        """Set mode for a specific session"""
        try:
            mode_key = mode_name.lower()
            if mode_key not in self.modes:
                return False
            
            sessions = self.load_sessions()
            sessions[session_id] = {
                'mode': mode_key,
                'updated_at': datetime.now().isoformat()
            }
            self.save_sessions(sessions)
            return True
        except Exception as e:
            print(f"Error setting session mode: {e}")
            return False
    
    def get_session_mode(self, session_id: str) -> str:
        """Get mode for a specific session"""
        try:
            sessions = self.load_sessions()
            session_data = sessions.get(session_id, {})
            return session_data.get('mode', 'default')
        except Exception as e:
            print(f"Error getting session mode: {e}")
            return 'default'
    
    def load_sessions(self) -> Dict[str, Any]:
        """Load session data from file"""
        try:
            if os.path.exists(self.session_file):
                with open(self.session_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Error loading sessions: {e}")
            return {}
    
    def save_sessions(self, sessions: Dict[str, Any]):
        """Save session data to file"""
        try:
            with open(self.session_file, 'w') as f:
                json.dump(sessions, f, indent=2)
        except Exception as e:
            print(f"Error saving sessions: {e}")
    
    def parse_mode_command(self, message: str) -> Optional[str]:
        """Parse mode switching commands from messages"""
        message = message.strip().lower()
        
        # Check for !mode commands
        if message.startswith('!'):
            mode_name = message[1:].strip()
            if mode_name in self.modes:
                return mode_name
        
        # Check for /mode commands
        if message.startswith('/mode '):
            mode_name = message[6:].strip()
            if mode_name in self.modes:
                return mode_name
        
        # Check for "switch to X mode" patterns
        switch_patterns = [
            'switch to ',
            'change to ',
            'use ',
            'activate ',
            'enable '
        ]
        
        for pattern in switch_patterns:
            if pattern in message:
                parts = message.split(pattern, 1)
                if len(parts) > 1:
                    potential_mode = parts[1].replace(' mode', '').strip()
                    if potential_mode in self.modes:
                        return potential_mode
        
        return None
    
    def get_mode_prompt(self, session_id: str) -> str:
        """Get the current system prompt for a session"""
        mode_name = self.get_session_mode(session_id)
        mode = self.get_mode(mode_name)
        return mode['prompt'] if mode else self.modes['default']['prompt']
    
    def get_enabled_tools(self, session_id: str) -> list:
        """Get enabled tools for the current session mode"""
        mode_name = self.get_session_mode(session_id)
        mode = self.get_mode(mode_name)
        return mode['tools_enabled'] if mode else ['all']
    
    def is_tool_enabled(self, session_id: str, tool_name: str) -> bool:
        """Check if a specific tool is enabled for the session"""
        enabled_tools = self.get_enabled_tools(session_id)
        return 'all' in enabled_tools or tool_name in enabled_tools

