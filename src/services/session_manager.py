"""
Enhanced Session Memory Manager for Jarvis
Provides cross-session memory, context awareness, and intelligent session management
"""

import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import threading
from collections import defaultdict

class SessionManager:
    def __init__(self, storage_path: str = "/tmp/jarvis_sessions"):
        self.storage_path = storage_path
        self.sessions = {}
        self.session_metadata = {}
        self.memory_cache = defaultdict(dict)
        self.context_weights = {}
        self.lock = threading.Lock()
        
        # Create storage directory
        os.makedirs(storage_path, exist_ok=True)
        
        # Load existing sessions
        self.load_sessions()
    
    def create_session(self, user_id: str = "default", mode: str = "default") -> str:
        """Create a new session with enhanced memory capabilities"""
        session_id = str(uuid.uuid4())
        
        with self.lock:
            session_data = {
                "id": session_id,
                "user_id": user_id,
                "mode": mode,
                "created_at": datetime.now().isoformat(),
                "last_activity": datetime.now().isoformat(),
                "messages": [],
                "context": {
                    "topics": [],
                    "entities": [],
                    "preferences": {},
                    "tools_used": [],
                    "file_references": []
                },
                "memory": {
                    "short_term": [],  # Recent interactions
                    "long_term": {},   # Persistent knowledge
                    "working": {}      # Current context
                },
                "statistics": {
                    "message_count": 0,
                    "tool_usage": {},
                    "session_duration": 0,
                    "topics_discussed": []
                }
            }
            
            self.sessions[session_id] = session_data
            self.session_metadata[session_id] = {
                "user_id": user_id,
                "mode": mode,
                "created_at": session_data["created_at"],
                "last_activity": session_data["last_activity"],
                "message_count": 0
            }
            
            # Save to disk
            self.save_session(session_id)
            
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session data with automatic loading if needed"""
        if session_id not in self.sessions:
            self.load_session(session_id)
        
        return self.sessions.get(session_id)
    
    def update_session_activity(self, session_id: str):
        """Update session last activity timestamp"""
        with self.lock:
            if session_id in self.sessions:
                self.sessions[session_id]["last_activity"] = datetime.now().isoformat()
                self.session_metadata[session_id]["last_activity"] = self.sessions[session_id]["last_activity"]
    
    def add_message(self, session_id: str, message: Dict) -> bool:
        """Add a message to session with context analysis"""
        session = self.get_session(session_id)
        if not session:
            return False
        
        with self.lock:
            # Add message
            session["messages"].append(message)
            session["statistics"]["message_count"] += 1
            
            # Update metadata
            self.session_metadata[session_id]["message_count"] = session["statistics"]["message_count"]
            
            # Analyze message for context
            self.analyze_message_context(session_id, message)
            
            # Update activity
            self.update_session_activity(session_id)
            
            # Manage memory
            self.update_session_memory(session_id, message)
            
            # Save to disk
            self.save_session(session_id)
            
        return True
    
    def analyze_message_context(self, session_id: str, message: Dict):
        """Analyze message for topics, entities, and context"""
        session = self.sessions[session_id]
        content = message.get("content", "").lower()
        
        # Simple topic extraction (in a real implementation, use NLP)
        topics = self.extract_topics(content)
        entities = self.extract_entities(content)
        
        # Update context
        for topic in topics:
            if topic not in session["context"]["topics"]:
                session["context"]["topics"].append(topic)
        
        for entity in entities:
            if entity not in session["context"]["entities"]:
                session["context"]["entities"].append(entity)
        
        # Track tool usage
        if message.get("tool_info"):
            tool_name = message["tool_info"].get("tool_name")
            if tool_name:
                session["context"]["tools_used"].append({
                    "tool": tool_name,
                    "timestamp": message.get("timestamp"),
                    "confidence": message["tool_info"].get("confidence", 0)
                })
                
                # Update statistics
                if tool_name not in session["statistics"]["tool_usage"]:
                    session["statistics"]["tool_usage"][tool_name] = 0
                session["statistics"]["tool_usage"][tool_name] += 1
    
    def extract_topics(self, content: str) -> List[str]:
        """Extract topics from message content (simplified implementation)"""
        # In a real implementation, use NLP libraries like spaCy or NLTK
        topic_keywords = {
            "programming": ["code", "python", "javascript", "programming", "development", "software"],
            "business": ["business", "strategy", "marketing", "sales", "revenue", "profit"],
            "technology": ["ai", "machine learning", "artificial intelligence", "tech", "innovation"],
            "finance": ["money", "investment", "finance", "budget", "cost", "price"],
            "health": ["health", "medical", "doctor", "medicine", "wellness"],
            "education": ["learn", "study", "education", "course", "tutorial", "training"]
        }
        
        topics = []
        for topic, keywords in topic_keywords.items():
            if any(keyword in content for keyword in keywords):
                topics.append(topic)
        
        return topics
    
    def extract_entities(self, content: str) -> List[str]:
        """Extract entities from message content (simplified implementation)"""
        # Simple entity extraction - in reality, use NER models
        entities = []
        
        # Look for URLs
        import re
        urls = re.findall(r'https?://[^\s]+', content)
        entities.extend([f"url:{url}" for url in urls])
        
        # Look for file extensions
        files = re.findall(r'\w+\.\w{2,4}', content)
        entities.extend([f"file:{file}" for file in files])
        
        return entities
    
    def update_session_memory(self, session_id: str, message: Dict):
        """Update session memory with new information"""
        session = self.sessions[session_id]
        
        # Add to short-term memory (last 10 interactions)
        session["memory"]["short_term"].append({
            "content": message.get("content", ""),
            "role": message.get("role", ""),
            "timestamp": message.get("timestamp"),
            "context_score": self.calculate_context_score(session_id, message)
        })
        
        # Keep only last 10 in short-term memory
        if len(session["memory"]["short_term"]) > 10:
            session["memory"]["short_term"] = session["memory"]["short_term"][-10:]
        
        # Update working memory with current context
        session["memory"]["working"] = {
            "current_topic": session["context"]["topics"][-1] if session["context"]["topics"] else None,
            "recent_tools": session["context"]["tools_used"][-3:] if session["context"]["tools_used"] else [],
            "conversation_flow": [msg["role"] for msg in session["messages"][-5:]]
        }
        
        # Update long-term memory with important information
        self.update_long_term_memory(session_id, message)
    
    def calculate_context_score(self, session_id: str, message: Dict) -> float:
        """Calculate relevance score for message context"""
        score = 0.5  # Base score
        
        # Boost score for tool usage
        if message.get("tool_info"):
            score += 0.3
        
        # Boost score for questions
        content = message.get("content", "").lower()
        if any(word in content for word in ["what", "how", "why", "when", "where"]):
            score += 0.2
        
        # Boost score for longer messages
        if len(content) > 100:
            score += 0.1
        
        return min(score, 1.0)
    
    def update_long_term_memory(self, session_id: str, message: Dict):
        """Update long-term memory with persistent knowledge"""
        session = self.sessions[session_id]
        content = message.get("content", "").lower()
        
        # Store preferences
        if "prefer" in content or "like" in content or "favorite" in content:
            preference_key = f"preference_{len(session['memory']['long_term'])}"
            session["memory"]["long_term"][preference_key] = {
                "type": "preference",
                "content": message.get("content"),
                "timestamp": message.get("timestamp"),
                "confidence": 0.8
            }
        
        # Store important facts
        if message.get("tool_info") and message["tool_info"].get("success"):
            fact_key = f"fact_{len(session['memory']['long_term'])}"
            session["memory"]["long_term"][fact_key] = {
                "type": "fact",
                "tool_used": message["tool_info"]["tool_name"],
                "result": message["tool_info"]["output"][:200],  # Truncate
                "timestamp": message.get("timestamp"),
                "confidence": message["tool_info"].get("confidence", 0.5)
            }
    
    def get_session_context(self, session_id: str) -> Dict:
        """Get comprehensive session context for AI responses"""
        session = self.get_session(session_id)
        if not session:
            return {}
        
        return {
            "current_mode": session.get("mode", "default"),
            "topics_discussed": session["context"]["topics"],
            "entities_mentioned": session["context"]["entities"],
            "tools_used": session["context"]["tools_used"],
            "short_term_memory": session["memory"]["short_term"],
            "working_memory": session["memory"]["working"],
            "relevant_long_term": self.get_relevant_long_term_memory(session_id),
            "session_statistics": session["statistics"],
            "preferences": session["context"]["preferences"]
        }
    
    def get_relevant_long_term_memory(self, session_id: str, limit: int = 5) -> List[Dict]:
        """Get most relevant long-term memories for current context"""
        session = self.sessions.get(session_id)
        if not session:
            return []
        
        long_term = session["memory"]["long_term"]
        
        # Sort by relevance (simplified - in reality, use semantic similarity)
        relevant_memories = []
        for key, memory in long_term.items():
            relevance_score = memory.get("confidence", 0.5)
            
            # Boost recent memories
            if memory.get("timestamp"):
                try:
                    memory_time = datetime.fromisoformat(memory["timestamp"])
                    hours_ago = (datetime.now() - memory_time).total_seconds() / 3600
                    if hours_ago < 24:
                        relevance_score += 0.2
                except:
                    pass
            
            relevant_memories.append((relevance_score, memory))
        
        # Sort by relevance and return top items
        relevant_memories.sort(key=lambda x: x[0], reverse=True)
        return [memory for score, memory in relevant_memories[:limit]]
    
    def switch_mode(self, session_id: str, new_mode: str) -> bool:
        """Switch session mode with context preservation"""
        session = self.get_session(session_id)
        if not session:
            return False
        
        with self.lock:
            old_mode = session.get("mode", "default")
            
            # Store mode-specific context
            mode_context_key = f"mode_context_{old_mode}"
            session["memory"]["long_term"][mode_context_key] = {
                "type": "mode_context",
                "mode": old_mode,
                "topics": session["context"]["topics"].copy(),
                "tools_used": session["context"]["tools_used"].copy(),
                "timestamp": datetime.now().isoformat(),
                "confidence": 0.9
            }
            
            # Switch mode
            session["mode"] = new_mode
            self.session_metadata[session_id]["mode"] = new_mode
            
            # Add mode switch message
            mode_switch_message = {
                "role": "system",
                "content": f"Mode switched from {old_mode} to {new_mode}",
                "timestamp": datetime.now().isoformat(),
                "mode_switch": {
                    "from": old_mode,
                    "to": new_mode
                }
            }
            
            session["messages"].append(mode_switch_message)
            
            # Update activity and save
            self.update_session_activity(session_id)
            self.save_session(session_id)
            
        return True
    
    def get_user_sessions(self, user_id: str) -> List[Dict]:
        """Get all sessions for a user"""
        user_sessions = []
        
        for session_id, metadata in self.session_metadata.items():
            if metadata["user_id"] == user_id:
                user_sessions.append({
                    "session_id": session_id,
                    "mode": metadata["mode"],
                    "created_at": metadata["created_at"],
                    "last_activity": metadata["last_activity"],
                    "message_count": metadata["message_count"]
                })
        
        # Sort by last activity
        user_sessions.sort(key=lambda x: x["last_activity"], reverse=True)
        return user_sessions
    
    def cleanup_old_sessions(self, days_old: int = 30):
        """Clean up sessions older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        sessions_to_remove = []
        
        for session_id, metadata in self.session_metadata.items():
            try:
                last_activity = datetime.fromisoformat(metadata["last_activity"])
                if last_activity < cutoff_date:
                    sessions_to_remove.append(session_id)
            except:
                # If we can't parse the date, consider it old
                sessions_to_remove.append(session_id)
        
        # Remove old sessions
        with self.lock:
            for session_id in sessions_to_remove:
                self.delete_session(session_id)
        
        return len(sessions_to_remove)
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and its data"""
        with self.lock:
            # Remove from memory
            if session_id in self.sessions:
                del self.sessions[session_id]
            
            if session_id in self.session_metadata:
                del self.session_metadata[session_id]
            
            # Remove from disk
            session_file = os.path.join(self.storage_path, f"{session_id}.json")
            if os.path.exists(session_file):
                os.remove(session_file)
                return True
        
        return False
    
    def save_session(self, session_id: str):
        """Save session to disk"""
        if session_id not in self.sessions:
            return
        
        session_file = os.path.join(self.storage_path, f"{session_id}.json")
        
        try:
            with open(session_file, 'w') as f:
                json.dump(self.sessions[session_id], f, indent=2)
        except Exception as e:
            print(f"Error saving session {session_id}: {e}")
    
    def load_session(self, session_id: str) -> bool:
        """Load session from disk"""
        session_file = os.path.join(self.storage_path, f"{session_id}.json")
        
        if not os.path.exists(session_file):
            return False
        
        try:
            with open(session_file, 'r') as f:
                session_data = json.load(f)
            
            self.sessions[session_id] = session_data
            
            # Update metadata
            self.session_metadata[session_id] = {
                "user_id": session_data.get("user_id", "default"),
                "mode": session_data.get("mode", "default"),
                "created_at": session_data.get("created_at"),
                "last_activity": session_data.get("last_activity"),
                "message_count": len(session_data.get("messages", []))
            }
            
            return True
            
        except Exception as e:
            print(f"Error loading session {session_id}: {e}")
            return False
    
    def load_sessions(self):
        """Load all sessions from disk"""
        if not os.path.exists(self.storage_path):
            return
        
        for filename in os.listdir(self.storage_path):
            if filename.endswith('.json'):
                session_id = filename[:-5]  # Remove .json extension
                self.load_session(session_id)
    
    def get_session_statistics(self) -> Dict:
        """Get overall session statistics"""
        total_sessions = len(self.sessions)
        total_messages = sum(len(session.get("messages", [])) for session in self.sessions.values())
        
        # Mode distribution
        mode_counts = defaultdict(int)
        for metadata in self.session_metadata.values():
            mode_counts[metadata["mode"]] += 1
        
        # Tool usage statistics
        tool_usage = defaultdict(int)
        for session in self.sessions.values():
            for tool, count in session.get("statistics", {}).get("tool_usage", {}).items():
                tool_usage[tool] += count
        
        return {
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "mode_distribution": dict(mode_counts),
            "tool_usage": dict(tool_usage),
            "average_messages_per_session": total_messages / total_sessions if total_sessions > 0 else 0
        }

# Global session manager instance
session_manager = SessionManager()

# Convenience functions
def create_session(user_id: str = "default", mode: str = "default") -> str:
    """Create a new session"""
    return session_manager.create_session(user_id, mode)

def get_session(session_id: str) -> Optional[Dict]:
    """Get session data"""
    return session_manager.get_session(session_id)

def add_message(session_id: str, message: Dict) -> bool:
    """Add message to session"""
    return session_manager.add_message(session_id, message)

def get_session_context(session_id: str) -> Dict:
    """Get session context"""
    return session_manager.get_session_context(session_id)

def switch_mode(session_id: str, new_mode: str) -> bool:
    """Switch session mode"""
    return session_manager.switch_mode(session_id, new_mode)

