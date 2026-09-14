from flask import Blueprint, request, jsonify, session
from datetime import datetime
import json
from pathlib import Path
import uuid
from functools import wraps

sessions_bp = Blueprint('sessions', __name__)

def admin_required(f):
    """Decorator to require admin authentication for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return jsonify({'error': 'Admin authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def get_sessions_db_path():
    return Path(__file__).parent.parent.parent / 'sessions.json'

def load_sessions_db():
    db_path = get_sessions_db_path()
    if db_path.exists():
        with open(db_path, 'r') as f:
            return json.load(f)
    return {"sessions": []}

def save_sessions_db(db):
    db_path = get_sessions_db_path()
    with open(db_path, 'w') as f:
        json.dump(db, f, indent=2)

@sessions_bp.route('/start', methods=['POST'])
@admin_required
def start_session():
    """Start a new session (admin only)"""
    try:
        data = request.get_json()
        db = load_sessions_db()
        
        session = {
            'id': str(uuid.uuid4()),
            'title': data.get('title', f"Session {datetime.now().strftime('%Y-%m-%d %H:%M')}"),
            'user': data.get('user', 'anonymous'),
            'started_at': datetime.now().isoformat(),
            'messages': [],
            'total_cost': 0.0,
            'total_tokens': 0,
            'models_used': []
        }
        
        db['sessions'].append(session)
        save_sessions_db(db)
        
        return jsonify({'success': True, 'session': session})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@sessions_bp.route('/<session_id>', methods=['GET'])
@admin_required
def get_session(session_id):
    """Get a specific session (admin only)"""
    db = load_sessions_db()
    for session in db['sessions']:
        if session['id'] == session_id:
            return jsonify(session)
    return jsonify({'error': 'Session not found'}), 404

@sessions_bp.route('/<session_id>/message', methods=['POST'])
@admin_required
def add_message_to_session(session_id):
    """Add a message to session (admin only)"""
    try:
        data = request.get_json()
        db = load_sessions_db()
        
        for session in db['sessions']:
            if session['id'] == session_id:
                message = {
                    'id': str(uuid.uuid4()),
                    'timestamp': datetime.now().isoformat(),
                    'role': data.get('role'),
                    'content': data.get('content'),
                    'model': data.get('model'),
                    'tokens': data.get('tokens', 0),
                    'cost': data.get('cost', 0.0),
                    'files': data.get('files', [])
                }
                
                session['messages'].append(message)
                session['total_tokens'] += message['tokens']
                session['total_cost'] += message['cost']
                
                if message['model'] and message['model'] not in session['models_used']:
                    session['models_used'].append(message['model'])
                
                save_sessions_db(db)
                return jsonify({'success': True, 'message': message})
        
        return jsonify({'error': 'Session not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@sessions_bp.route('/<session_id>/end', methods=['POST'])
@admin_required
def end_session(session_id):
    """End a session (admin only)"""
    try:
        db = load_sessions_db()
        for session in db['sessions']:
            if session['id'] == session_id:
                session['ended_at'] = datetime.now().isoformat()
                save_sessions_db(db)
                return jsonify({'success': True, 'session': session})
        return jsonify({'error': 'Session not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@sessions_bp.route('/list', methods=['GET'])
@admin_required
def list_sessions():
    """Get all sessions (admin only)"""
    db = load_sessions_db()
    user = request.args.get('user')
    
    if user:
        filtered = [s for s in db['sessions'] if s.get('user') == user]
        return jsonify({'sessions': filtered})
    
    return jsonify(db)

@sessions_bp.route('/<session_id>', methods=['DELETE'])
@admin_required
def delete_session(session_id):
    """Delete a session (admin only)"""
    try:
        db = load_sessions_db()
        db['sessions'] = [s for s in db['sessions'] if s['id'] != session_id]
        save_sessions_db(db)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def sanitize_csv_value(value):
    """Sanitize CSV values to prevent formula injection attacks.
    Values starting with =, +, -, @ can be executed as formulas in Excel/Sheets."""
    if not isinstance(value, str):
        return value
    # Prefix with single quote to prevent formula execution
    if value and value[0] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + value
    return value

@sessions_bp.route('/<session_id>/export', methods=['GET'])
@admin_required
def export_session(session_id):
    """Export session as TXT, CSV, or PDF (admin only)"""
    from flask import send_file
    import io
    import csv
    
    export_format = request.args.get('format', 'txt')  # Default to TXT for Arabic support
    
    db = load_sessions_db()
    for sess in db['sessions']:
        if sess['id'] == session_id:
            
            if export_format == 'txt':
                # Plain text export with full Arabic support
                lines = []
                lines.append("=" * 60)
                lines.append(f"Session Export: {sess.get('title', 'N/A')}")
                lines.append("=" * 60)
                lines.append("")
                lines.append(f"Session ID: {sess['id']}")
                lines.append(f"Title: {sess.get('title', 'N/A')}")
                lines.append(f"User: {sess.get('user', 'N/A')}")
                lines.append(f"Started: {sess.get('start_time', 'N/A')}")
                lines.append(f"Ended: {sess.get('end_time', 'Not ended')}")
                lines.append("")
                lines.append("-" * 60)
                lines.append("Messages:")
                lines.append("-" * 60)
                lines.append("")
                
                for msg in sess.get('messages', []):
                    role = "User" if msg.get('role') == 'user' else "AI"
                    content = msg.get('content', '')
                    timestamp = msg.get('timestamp', '')
                    lines.append(f"[{role}] ({timestamp})")
                    lines.append(content)
                    lines.append("")
                    lines.append("-" * 40)
                    lines.append("")
                
                # Create UTF-8 text file with BOM for proper Arabic display
                output = io.BytesIO()
                output.write(b'\xef\xbb\xbf')  # UTF-8 BOM
                output.write('\n'.join(lines).encode('utf-8'))
                output.seek(0)
                
                filename = f"session_{sess.get('title', session_id).replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                return send_file(output, mimetype='text/plain; charset=utf-8', as_attachment=True, download_name=filename)
            
            elif export_format == 'csv':
                # CSV export with proper UTF-8 encoding for Arabic
                buffer = io.StringIO()
                writer = csv.writer(buffer)
                
                # Write header (sanitized for security)
                writer.writerow([sanitize_csv_value('Session Export - ' + sess.get('title', 'N/A'))])
                writer.writerow([])
                writer.writerow(['Session ID', sanitize_csv_value(sess['id'])])
                writer.writerow(['Title', sanitize_csv_value(sess.get('title', 'N/A'))])
                writer.writerow(['User', sanitize_csv_value(sess.get('user', 'N/A'))])
                writer.writerow(['Started', sanitize_csv_value(sess.get('start_time', 'N/A'))])
                writer.writerow(['Ended', sanitize_csv_value(sess.get('end_time', 'Not ended'))])
                writer.writerow([])
                writer.writerow(['Role', 'Content', 'Timestamp'])
                
                # Write messages (sanitized to prevent CSV injection)
                for msg in sess.get('messages', []):
                    role = "User" if msg.get('role') == 'user' else "AI"
                    content = sanitize_csv_value(msg.get('content', ''))
                    timestamp = sanitize_csv_value(msg.get('timestamp', ''))
                    writer.writerow([role, content, timestamp])
                
                # Convert to bytes with BOM for Excel Arabic support
                output = io.BytesIO()
                output.write(b'\xef\xbb\xbf')  # UTF-8 BOM
                output.write(buffer.getvalue().encode('utf-8'))
                output.seek(0)
                
                filename = f"session_{sess.get('title', session_id).replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                return send_file(output, mimetype='text/csv; charset=utf-8', as_attachment=True, download_name=filename)
            
            else:
                # PDF export (English only - Helvetica doesn't support Arabic)
                from reportlab.lib.pagesizes import letter
                from reportlab.lib.units import inch
                from reportlab.pdfgen import canvas
                from reportlab.lib import colors
                
                buffer = io.BytesIO()
                c = canvas.Canvas(buffer, pagesize=letter)
                width, height = letter
                
                y_position = height - 1*inch
                c.setFont("Helvetica-Bold", 18)
                c.drawString(1*inch, y_position, "Session Export")
                y_position -= 0.5*inch
                
                c.setFont("Helvetica", 11)
                c.drawString(1*inch, y_position, f"Session ID: {sess['id']}")
                y_position -= 0.3*inch
                c.drawString(1*inch, y_position, f"Title: {sess.get('title', 'N/A')}")
                y_position -= 0.3*inch
                c.drawString(1*inch, y_position, f"User: {sess.get('user', 'N/A')}")
                y_position -= 0.3*inch
                c.drawString(1*inch, y_position, f"Started: {sess.get('start_time', 'N/A')}")
                y_position -= 0.3*inch
                c.drawString(1*inch, y_position, f"Ended: {sess.get('end_time', 'Not ended')}")
                y_position -= 0.5*inch
                
                c.setStrokeColor(colors.grey)
                c.line(1*inch, y_position, width - 1*inch, y_position)
                y_position -= 0.4*inch
                
                c.setFont("Helvetica-Bold", 14)
                c.drawString(1*inch, y_position, "Messages:")
                y_position -= 0.4*inch
                
                messages = sess.get('messages', [])
                for i, msg in enumerate(messages):
                    if y_position < 1.5*inch:
                        c.showPage()
                        y_position = height - 1*inch
                    
                    c.setFont("Helvetica-Bold", 11)
                    role = "User" if msg.get('role') == 'user' else "AI"
                    c.drawString(1*inch, y_position, f"{role}:")
                    y_position -= 0.25*inch
                    
                    c.setFont("Helvetica", 10)
                    # Filter out non-Latin characters for PDF (Arabic not supported)
                    content = msg.get('content', '')[:500]
                    content = ''.join(c if ord(c) < 256 else '?' for c in content)
                    text_object = c.beginText(1*inch, y_position)
                    text_object.setFont("Helvetica", 10)
                    
                    max_width = width - 2*inch
                    words = content.split()
                    line = ""
                    for word in words:
                        test_line = line + word + " "
                        if c.stringWidth(test_line, "Helvetica", 10) < max_width:
                            line = test_line
                        else:
                            text_object.textLine(line)
                            y_position -= 0.2*inch
                            if y_position < 1.5*inch:
                                c.drawText(text_object)
                                c.showPage()
                                y_position = height - 1*inch
                                text_object = c.beginText(1*inch, y_position)
                                text_object.setFont("Helvetica", 10)
                            line = word + " "
                    if line:
                        text_object.textLine(line)
                        y_position -= 0.2*inch
                    
                    c.drawText(text_object)
                    y_position -= 0.3*inch
                
                c.save()
                buffer.seek(0)
                
                filename = f"session_{sess.get('title', session_id).replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name=filename)
    
    return jsonify({'error': 'Session not found'}), 404
