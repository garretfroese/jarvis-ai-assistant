"""
Learning and Adaptation Service
Implements machine learning capabilities, pattern recognition, and continuous improvement
"""

import os
import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, Counter
from src.services.autonomy_service import memory_manager
from src.models.database import CommandLog, SecurityEvent

class PatternRecognizer:
    """Pattern recognition for user behavior and system performance"""
    
    def __init__(self):
        self.memory_manager = memory_manager
    
    def analyze_command_patterns(self, days: int = 7) -> Dict:
        """Analyze command usage patterns"""
        try:
            # Get recent command logs
            since_date = datetime.utcnow() - timedelta(days=days)
            logs = CommandLog.query.filter(CommandLog.created_at >= since_date).all()
            
            if not logs:
                return {'error': 'No command data available'}
            
            # Analyze patterns
            command_frequency = Counter(log.command for log in logs)
            hourly_usage = defaultdict(int)
            success_rates = defaultdict(lambda: {'total': 0, 'success': 0})
            execution_times = defaultdict(list)
            
            for log in logs:
                hour = log.created_at.hour
                hourly_usage[hour] += 1
                
                success_rates[log.command]['total'] += 1
                if log.status == 'success':
                    success_rates[log.command]['success'] += 1
                
                if log.execution_time:
                    execution_times[log.command].append(log.execution_time)
            
            # Calculate success rates
            command_success_rates = {}
            for command, stats in success_rates.items():
                command_success_rates[command] = (stats['success'] / stats['total']) * 100
            
            # Calculate average execution times
            avg_execution_times = {}
            for command, times in execution_times.items():
                avg_execution_times[command] = sum(times) / len(times) if times else 0
            
            patterns = {
                'analysis_period': f'{days} days',
                'total_commands': len(logs),
                'unique_commands': len(command_frequency),
                'most_used_commands': dict(command_frequency.most_common(10)),
                'hourly_usage_distribution': dict(hourly_usage),
                'command_success_rates': command_success_rates,
                'average_execution_times': avg_execution_times,
                'peak_usage_hour': max(hourly_usage, key=hourly_usage.get) if hourly_usage else None,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Store patterns in memory
            self.memory_manager.store('command_patterns', patterns, category='analytics', expires_in_hours=24)
            
            return patterns
            
        except Exception as e:
            return {'error': str(e)}
    
    def detect_anomalies(self) -> Dict:
        """Detect anomalous behavior patterns"""
        try:
            # Get recent security events
            recent_events = SecurityEvent.query.filter(
                SecurityEvent.created_at >= datetime.utcnow() - timedelta(hours=24)
            ).all()
            
            # Get recent command logs
            recent_commands = CommandLog.query.filter(
                CommandLog.created_at >= datetime.utcnow() - timedelta(hours=24)
            ).all()
            
            anomalies = []
            
            # Check for unusual failure rates
            command_failures = defaultdict(int)
            command_totals = defaultdict(int)
            
            for log in recent_commands:
                command_totals[log.command] += 1
                if log.status != 'success':
                    command_failures[log.command] += 1
            
            for command, failures in command_failures.items():
                failure_rate = (failures / command_totals[command]) * 100
                if failure_rate > 50:  # More than 50% failure rate
                    anomalies.append({
                        'type': 'high_failure_rate',
                        'command': command,
                        'failure_rate': failure_rate,
                        'severity': 'medium'
                    })
            
            # Check for security events
            if len(recent_events) > 10:  # More than 10 security events in 24h
                anomalies.append({
                    'type': 'high_security_events',
                    'count': len(recent_events),
                    'severity': 'high'
                })
            
            # Check for unusual execution times
            for log in recent_commands:
                if log.execution_time and log.execution_time > 300:  # More than 5 minutes
                    anomalies.append({
                        'type': 'long_execution_time',
                        'command': log.command,
                        'execution_time': log.execution_time,
                        'severity': 'low'
                    })
            
            return {
                'anomalies': anomalies,
                'total_anomalies': len(anomalies),
                'analysis_period': '24 hours',
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def predict_next_command(self, recent_commands: List[str]) -> Dict:
        """Predict next likely command based on patterns"""
        try:
            # Get historical command sequences
            patterns = self.memory_manager.retrieve('command_patterns')
            if not patterns:
                return {'error': 'No pattern data available'}
            
            # Simple sequence prediction based on frequency
            if not recent_commands:
                # Return most common command
                most_used = patterns.get('most_used_commands', {})
                if most_used:
                    next_command = max(most_used, key=most_used.get)
                    confidence = most_used[next_command] / sum(most_used.values())
                    return {
                        'predicted_command': next_command,
                        'confidence': confidence,
                        'reasoning': 'Most frequently used command'
                    }
            
            # Look for sequence patterns
            last_command = recent_commands[-1]
            
            # Get commands that typically follow the last command
            # This is a simplified approach - could be enhanced with ML
            common_sequences = {
                'github_create_repo': ['github_deploy', 'railway_deploy'],
                'github_deploy': ['railway_deploy', 'cicd_deploy'],
                'setup_slack_bot': ['send_email', 'manage_files'],
                'deploy_code': ['system_info', 'railway_status']
            }
            
            if last_command in common_sequences:
                next_commands = common_sequences[last_command]
                return {
                    'predicted_commands': next_commands,
                    'confidence': 0.7,
                    'reasoning': f'Common sequence after {last_command}'
                }
            
            return {
                'predicted_command': None,
                'confidence': 0,
                'reasoning': 'No clear pattern detected'
            }
            
        except Exception as e:
            return {'error': str(e)}

class LearningEngine:
    """Machine learning engine for continuous improvement"""
    
    def __init__(self):
        self.memory_manager = memory_manager
        self.pattern_recognizer = PatternRecognizer()
    
    def learn_from_interactions(self) -> Dict:
        """Learn from user interactions and system performance"""
        try:
            # Analyze command patterns
            patterns = self.pattern_recognizer.analyze_command_patterns()
            
            # Detect anomalies
            anomalies = self.pattern_recognizer.detect_anomalies()
            
            # Generate learning insights
            insights = self.generate_learning_insights(patterns, anomalies)
            
            # Store learning results
            learning_data = {
                'patterns': patterns,
                'anomalies': anomalies,
                'insights': insights,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            self.memory_manager.store('learning_data', learning_data, category='learning', expires_in_hours=168)  # 1 week
            
            return learning_data
            
        except Exception as e:
            return {'error': str(e)}
    
    def generate_learning_insights(self, patterns: Dict, anomalies: Dict) -> List[Dict]:
        """Generate actionable insights from patterns and anomalies"""
        insights = []
        
        try:
            # Insights from command patterns
            if 'most_used_commands' in patterns:
                most_used = patterns['most_used_commands']
                if most_used:
                    top_command = max(most_used, key=most_used.get)
                    insights.append({
                        'type': 'optimization',
                        'category': 'performance',
                        'insight': f"Command '{top_command}' is used most frequently. Consider optimizing its performance.",
                        'priority': 'medium',
                        'action': f'optimize_command_{top_command}'
                    })
            
            # Insights from success rates
            if 'command_success_rates' in patterns:
                success_rates = patterns['command_success_rates']
                for command, rate in success_rates.items():
                    if rate < 80:
                        insights.append({
                            'type': 'reliability',
                            'category': 'error_handling',
                            'insight': f"Command '{command}' has low success rate ({rate:.1f}%). Needs improvement.",
                            'priority': 'high',
                            'action': f'improve_error_handling_{command}'
                        })
            
            # Insights from execution times
            if 'average_execution_times' in patterns:
                exec_times = patterns['average_execution_times']
                for command, time in exec_times.items():
                    if time > 60:  # More than 1 minute
                        insights.append({
                            'type': 'performance',
                            'category': 'speed',
                            'insight': f"Command '{command}' takes {time:.1f}s on average. Consider optimization.",
                            'priority': 'medium',
                            'action': f'optimize_speed_{command}'
                        })
            
            # Insights from anomalies
            if 'anomalies' in anomalies:
                for anomaly in anomalies['anomalies']:
                    if anomaly['severity'] == 'high':
                        insights.append({
                            'type': 'security',
                            'category': 'anomaly',
                            'insight': f"High severity anomaly detected: {anomaly['type']}",
                            'priority': 'critical',
                            'action': f'investigate_anomaly_{anomaly["type"]}'
                        })
            
            # Usage pattern insights
            if 'peak_usage_hour' in patterns and patterns['peak_usage_hour'] is not None:
                peak_hour = patterns['peak_usage_hour']
                insights.append({
                    'type': 'usage',
                    'category': 'scheduling',
                    'insight': f"Peak usage at hour {peak_hour}. Consider resource scaling.",
                    'priority': 'low',
                    'action': f'scale_resources_hour_{peak_hour}'
                })
            
            return insights
            
        except Exception as e:
            return [{'error': str(e)}]
    
    def adapt_behavior(self, insights: List[Dict]) -> Dict:
        """Adapt system behavior based on learning insights"""
        try:
            adaptations = []
            
            for insight in insights:
                if insight.get('priority') == 'critical':
                    # Immediate adaptations for critical issues
                    adaptation = self.apply_critical_adaptation(insight)
                    if adaptation:
                        adaptations.append(adaptation)
                
                elif insight.get('priority') == 'high':
                    # Schedule high priority adaptations
                    adaptation = self.schedule_adaptation(insight)
                    if adaptation:
                        adaptations.append(adaptation)
            
            return {
                'adaptations_applied': len(adaptations),
                'adaptations': adaptations,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def apply_critical_adaptation(self, insight: Dict) -> Optional[Dict]:
        """Apply critical adaptations immediately"""
        try:
            action = insight.get('action', '')
            
            if 'investigate_anomaly' in action:
                # Trigger security investigation
                self.memory_manager.store(
                    f'security_alert_{datetime.utcnow().timestamp()}',
                    {
                        'type': 'anomaly_investigation',
                        'insight': insight,
                        'status': 'active',
                        'created_at': datetime.utcnow().isoformat()
                    },
                    category='security_alerts'
                )
                
                return {
                    'type': 'security_investigation',
                    'action': action,
                    'status': 'triggered'
                }
            
            return None
            
        except Exception as e:
            print(f"Critical adaptation error: {e}")
            return None
    
    def schedule_adaptation(self, insight: Dict) -> Optional[Dict]:
        """Schedule adaptation for later execution"""
        try:
            # Store adaptation for scheduled execution
            adaptation_id = f"adaptation_{datetime.utcnow().timestamp()}"
            
            self.memory_manager.store(
                f'scheduled_adaptation:{adaptation_id}',
                {
                    'insight': insight,
                    'status': 'scheduled',
                    'created_at': datetime.utcnow().isoformat()
                },
                category='adaptations'
            )
            
            return {
                'type': 'scheduled_adaptation',
                'adaptation_id': adaptation_id,
                'action': insight.get('action'),
                'priority': insight.get('priority')
            }
            
        except Exception as e:
            print(f"Adaptation scheduling error: {e}")
            return None
    
    def get_learning_summary(self) -> Dict:
        """Get summary of learning progress and insights"""
        try:
            learning_data = self.memory_manager.retrieve('learning_data')
            if not learning_data:
                return {'error': 'No learning data available'}
            
            insights = learning_data.get('insights', [])
            patterns = learning_data.get('patterns', {})
            anomalies = learning_data.get('anomalies', {})
            
            summary = {
                'total_insights': len(insights),
                'critical_insights': len([i for i in insights if i.get('priority') == 'critical']),
                'high_priority_insights': len([i for i in insights if i.get('priority') == 'high']),
                'total_commands_analyzed': patterns.get('total_commands', 0),
                'unique_commands': patterns.get('unique_commands', 0),
                'anomalies_detected': anomalies.get('total_anomalies', 0),
                'learning_categories': list(set(i.get('category') for i in insights if i.get('category'))),
                'last_analysis': learning_data.get('timestamp'),
                'recommendations': self.generate_recommendations(insights)
            }
            
            return summary
            
        except Exception as e:
            return {'error': str(e)}
    
    def generate_recommendations(self, insights: List[Dict]) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Group insights by category
        categories = defaultdict(list)
        for insight in insights:
            category = insight.get('category', 'general')
            categories[category].append(insight)
        
        # Generate category-specific recommendations
        if 'performance' in categories:
            recommendations.append("Consider implementing performance optimizations for frequently used commands")
        
        if 'error_handling' in categories:
            recommendations.append("Improve error handling and validation for commands with low success rates")
        
        if 'security' in categories:
            recommendations.append("Review security measures and investigate detected anomalies")
        
        if 'usage' in categories:
            recommendations.append("Optimize resource allocation based on usage patterns")
        
        return recommendations

class AdaptationEngine:
    """Engine for applying learned adaptations"""
    
    def __init__(self):
        self.memory_manager = memory_manager
        self.learning_engine = LearningEngine()
    
    def execute_scheduled_adaptations(self) -> Dict:
        """Execute scheduled adaptations"""
        try:
            # Get scheduled adaptations
            adaptations = self.memory_manager.search(category='adaptations', pattern='scheduled_adaptation')
            
            executed = []
            failed = []
            
            for adaptation_data in adaptations:
                adaptation_id = adaptation_data['key'].split(':')[1]
                adaptation = adaptation_data['value']
                
                if adaptation.get('status') == 'scheduled':
                    result = self.execute_adaptation(adaptation_id, adaptation)
                    if result['success']:
                        executed.append(adaptation_id)
                    else:
                        failed.append({'id': adaptation_id, 'error': result['error']})
            
            return {
                'executed': len(executed),
                'failed': len(failed),
                'executed_adaptations': executed,
                'failed_adaptations': failed,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def execute_adaptation(self, adaptation_id: str, adaptation: Dict) -> Dict:
        """Execute a specific adaptation"""
        try:
            insight = adaptation.get('insight', {})
            action = insight.get('action', '')
            
            # Mark as executing
            adaptation['status'] = 'executing'
            adaptation['started_at'] = datetime.utcnow().isoformat()
            self.memory_manager.store(f'scheduled_adaptation:{adaptation_id}', adaptation, category='adaptations')
            
            # Execute based on action type
            if 'optimize_command' in action:
                result = self.optimize_command_performance(action)
            elif 'improve_error_handling' in action:
                result = self.improve_error_handling(action)
            elif 'optimize_speed' in action:
                result = self.optimize_command_speed(action)
            else:
                result = {'success': False, 'error': f'Unknown action type: {action}'}
            
            # Update adaptation status
            adaptation['status'] = 'completed' if result['success'] else 'failed'
            adaptation['completed_at'] = datetime.utcnow().isoformat()
            adaptation['result'] = result
            
            self.memory_manager.store(f'scheduled_adaptation:{adaptation_id}', adaptation, category='adaptations')
            
            return result
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def optimize_command_performance(self, action: str) -> Dict:
        """Optimize command performance"""
        try:
            command = action.split('_')[-1]
            
            # Store optimization recommendation
            optimization = {
                'command': command,
                'type': 'performance_optimization',
                'recommendations': [
                    'Add caching for frequently accessed data',
                    'Implement connection pooling',
                    'Add request batching',
                    'Optimize database queries'
                ],
                'created_at': datetime.utcnow().isoformat()
            }
            
            self.memory_manager.store(f'optimization:{command}', optimization, category='optimizations')
            
            return {'success': True, 'message': f'Performance optimization plan created for {command}'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def improve_error_handling(self, action: str) -> Dict:
        """Improve error handling for a command"""
        try:
            command = action.split('_')[-1]
            
            # Store error handling improvement plan
            improvement = {
                'command': command,
                'type': 'error_handling_improvement',
                'improvements': [
                    'Add input validation',
                    'Implement retry logic',
                    'Add detailed error messages',
                    'Implement graceful degradation'
                ],
                'created_at': datetime.utcnow().isoformat()
            }
            
            self.memory_manager.store(f'improvement:{command}', improvement, category='improvements')
            
            return {'success': True, 'message': f'Error handling improvement plan created for {command}'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def optimize_command_speed(self, action: str) -> Dict:
        """Optimize command execution speed"""
        try:
            command = action.split('_')[-1]
            
            # Store speed optimization plan
            optimization = {
                'command': command,
                'type': 'speed_optimization',
                'optimizations': [
                    'Implement asynchronous processing',
                    'Add parallel execution',
                    'Optimize algorithm complexity',
                    'Cache intermediate results'
                ],
                'created_at': datetime.utcnow().isoformat()
            }
            
            self.memory_manager.store(f'speed_optimization:{command}', optimization, category='optimizations')
            
            return {'success': True, 'message': f'Speed optimization plan created for {command}'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

# Global instances
pattern_recognizer = PatternRecognizer()
learning_engine = LearningEngine()
adaptation_engine = AdaptationEngine()

