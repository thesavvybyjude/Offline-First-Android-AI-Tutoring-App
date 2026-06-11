"""
Offline Sync Layer
Implements delta sync protocol with conflict resolution
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Optional
from flask import Flask, request, jsonify
from backend.database import DatabaseManager


class SyncLayer:
    """Offline-first synchronization layer with delta sync"""
    
    def __init__(self, db_manager: DatabaseManager = None,
                 server_url: str = "http://localhost:5000"):
        self.db = db_manager or DatabaseManager()
        self.server_url = server_url
        self.app = Flask(__name__)
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup Flask routes for sync server"""
        
        @self.app.route('/sync/push', methods=['POST'])
        def push_changes():
            """Receive pushed changes from client"""
            data = request.json
            student_id = data.get('student_id')
            changes = data.get('changes', [])
            
            results = []
            for change in changes:
                result = self._process_server_change(change)
                results.append(result)
            
            return jsonify({
                'success': True,
                'processed': len(results),
                'results': results
            })
        
        @self.app.route('/sync/pull/<int:student_id>', methods=['GET'])
        def pull_changes(student_id):
            """Send unsynced changes to client"""
            # Get all unsynced records
            students = self.db.get_unsynced_records('students')
            records = self.db.get_unsynced_records('repetition_records')
            
            changes = []
            
            for student in students:
                changes.append({
                    'table': 'students',
                    'action': 'UPDATE',
                    'data': student
                })
            
            for record in records:
                changes.append({
                    'table': 'repetition_records',
                    'action': 'UPDATE',
                    'data': record
                })
            
            return jsonify({
                'success': True,
                'changes': changes
            })
        
        @self.app.route('/health', methods=['GET'])
        def health():
            """Health check endpoint"""
            return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})
    
    def _process_server_change(self, change: Dict) -> Dict:
        """Process a change received from client on server"""
        table = change.get('table')
        data = change.get('data')
        action = change.get('action')
        
        try:
            if table == 'students':
                return self._sync_student(data, action)
            elif table == 'repetition_records':
                return self._sync_repetition_record(data, action)
            else:
                return {'success': False, 'error': f'Unknown table: {table}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _sync_student(self, data: Dict, action: str) -> Dict:
        """Sync student record with conflict resolution"""
        student_id = data.get('id')
        existing = self.db.get_student(student_id)
        
        if existing:
            # Conflict resolution: last-write-wins by timestamp
            if data.get('updated_at') > existing.get('updated_at'):
                # Update with newer data
                conn = self.db.connect()
                cursor = conn.cursor()
                cursor.execute(
                    """UPDATE students SET name=?, grade_level=?, school_id=?, updated_at=?
                       WHERE id=?""",
                    (data['name'], data['grade_level'], data['school_id'],
                     data['updated_at'], student_id)
                )
                conn.commit()
                return {'success': True, 'action': 'updated'}
            else:
                return {'success': True, 'action': 'skipped (older)'}
        else:
            # Insert new record
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO students (id, name, grade_level, school_id, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (student_id, data['name'], data['grade_level'], data['school_id'],
                 data['created_at'], data['updated_at'])
            )
            conn.commit()
            return {'success': True, 'action': 'inserted'}
    
    def _sync_repetition_record(self, data: Dict, action: str) -> Dict:
        """Sync repetition record with conflict resolution"""
        student_id = data.get('student_id')
        item_id = data.get('item_id')
        
        existing = self.db.get_repetition_record(student_id, item_id)
        
        if existing:
            # Conflict resolution: keep higher repetition count
            if data.get('repetitions', 0) > existing.get('repetitions', 0):
                # Update with higher repetition count
                conn = self.db.connect()
                cursor = conn.cursor()
                cursor.execute(
                    """UPDATE repetition_records 
                       SET ease_factor=?, interval_days=?, repetitions=?, 
                           last_quality=?, next_review=?, updated_at=?
                       WHERE student_id=? AND item_id=?""",
                    (data['ease_factor'], data['interval_days'], data['repetitions'],
                     data['last_quality'], data['next_review'], data['updated_at'],
                     student_id, item_id)
                )
                conn.commit()
                
                # Log conflict
                self.db._log_sync_action(student_id, 'repetition_records',
                                       existing['id'], 'CONFLICT_RESOLVED')
                
                return {'success': True, 'action': 'updated (conflict resolved)'}
            else:
                return {'success': True, 'action': 'skipped (lower repetitions)'}
        else:
            # Insert new record
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO repetition_records 
                   (student_id, item_id, ease_factor, interval_days, repetitions, 
                    last_quality, next_review, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (student_id, item_id, data['ease_factor'], data['interval_days'],
                 data['repetitions'], data['last_quality'], data['next_review'],
                 data['updated_at'])
            )
            conn.commit()
            return {'success': True, 'action': 'inserted'}
    
    def push_changes(self, student_id: int) -> Dict:
        """Push unsynced changes to server"""
        import requests
        
        # Get unsynced records
        students = self.db.get_unsynced_records('students')
        records = self.db.get_unsynced_records('repetition_records')
        
        changes = []
        
        for student in students:
            changes.append({
                'table': 'students',
                'action': 'UPDATE',
                'data': student
            })
        
        for record in records:
            changes.append({
                'table': 'repetition_records',
                'action': 'UPDATE',
                'data': record
            })
        
        if not changes:
            return {'success': True, 'pushed': 0, 'message': 'No changes to sync'}
        
        # Push to server
        try:
            response = requests.post(
                f"{self.server_url}/sync/push",
                json={'student_id': student_id, 'changes': changes},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Mark records as synced
                for change in changes:
                    table = change['table']
                    record_id = change['data']['id']
                    self.db.mark_as_synced(table, record_id)
                
                return {
                    'success': True,
                    'pushed': result.get('processed', 0),
                    'message': 'Changes synced successfully'
                }
            else:
                return {
                    'success': False,
                    'error': f"Server error: {response.status_code}"
                }
        except Exception as e:
            return {
                'success': False,
                'error': f"Sync failed: {str(e)}"
            }
    
    def pull_changes(self, student_id: int) -> Dict:
        """Pull changes from server"""
        import requests
        
        try:
            response = requests.get(
                f"{self.server_url}/sync/pull/{student_id}",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                changes = data.get('changes', [])
                
                # Process changes
                for change in changes:
                    self._process_client_change(change)
                
                return {
                    'success': True,
                    'pulled': len(changes),
                    'message': f'Pulled {len(changes)} changes'
                }
            else:
                return {
                    'success': False,
                    'error': f"Server error: {response.status_code}"
                }
        except Exception as e:
            return {
                'success': False,
                'error': f"Pull failed: {str(e)}"
            }
    
    def _process_client_change(self, change: Dict):
        """Process a change pulled from server on client"""
        table = change.get('table')
        data = change.get('data')
        
        if table == 'students':
            self._sync_student(data, change.get('action'))
        elif table == 'repetition_records':
            self._sync_repetition_record(data, change.get('action'))
    
    def sync(self, student_id: int) -> Dict:
        """Perform bidirectional sync"""
        # Push local changes
        push_result = self.push_changes(student_id)
        
        # Pull remote changes
        pull_result = self.pull_changes(student_id)
        
        return {
            'push': push_result,
            'pull': pull_result,
            'success': push_result.get('success', False) and pull_result.get('success', False)
        }
    
    def run_server(self, host: str = "0.0.0.0", port: int = 5000, debug: bool = False):
        """Run the sync server"""
        print(f"Starting sync server on {host}:{port}")
        self.app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    # Run sync server
    sync = SyncLayer()
    sync.run_server(debug=True)
