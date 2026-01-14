"""
Student routes for dashboard, classes, attendance, and QR scanning
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date
from app import db, socketio
from app.models import (
    User, Student, ClassInstance, ClassSession, Enrollment, 
    AttendanceRecord, Course, AcademicPeriod, Notification
)
from app.utils.qr_generator import QRCodeGenerator
import json
import uuid

student_bp = Blueprint('student', __name__)


def student_required(f):
    """Decorator to ensure user is a student"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'student':
            flash('Access denied. Student account required.', 'error')
            return redirect(url_for('auth.student_login'))
        return f(*args, **kwargs)
    return decorated_function


@student_bp.route('/dashboard')
@login_required
@student_required
def dashboard():
    """Student dashboard"""
    student = Student.query.filter_by(user_id=current_user.id).first()
    
    if not student:
        flash('Student profile not found.', 'error')
        return redirect(url_for('main.index'))
    
    # Get enrolled classes (student_id in Enrollment references students.user_id)
    enrollments = Enrollment.query.filter_by(
        student_id=student.user_id, 
        status='active'
    ).all()
    
    classes = []
    today = date.today()
    today_str = today.strftime('%A')  # Day name like 'Monday'
    
    for enrollment in enrollments:
        class_instance = enrollment.class_instance
        course = class_instance.course
        
        # Check if class meets today based on schedule
        days_list = class_instance.days_list
        scheduled_today = today_str in days_list
        
        # Get attendance stats
        total_sessions = ClassSession.query.filter_by(
            class_instance_id=class_instance.id,
            status='completed'
        ).count()
        
        attended_sessions = db.session.query(AttendanceRecord).join(ClassSession).filter(
            ClassSession.class_instance_id == class_instance.id,
            AttendanceRecord.student_id == current_user.id,
            AttendanceRecord.status.in_(['present', 'late', 'excused'])
        ).count()
        
        attendance_rate = round((attended_sessions / total_sessions * 100)) if total_sessions > 0 else 0
        
        # Get today's session if any
        today_session = ClassSession.query.filter_by(
            class_instance_id=class_instance.id,
            date=today
        ).first()
        
        # Check if there's an active session today
        has_active_session = today_session and today_session.status == 'active' if today_session else False
        
        # Class meets today if scheduled OR has an active session
        meets_today = scheduled_today or has_active_session
        
        classes.append({
            'id': class_instance.id,
            'code': course.code,
            'name': course.name,
            'room': class_instance.room_location,
            'schedule': f"{', '.join(days_list)} {class_instance.start_time}-{class_instance.end_time}",
            'meets_today': meets_today,
            'attendance_rate': attendance_rate,
            'total_sessions': total_sessions,
            'attended_sessions': attended_sessions,
            'today_session': today_session,
            'has_active_session': has_active_session
        })
    
    # Get today's attendance stats
    today_stats = {
        'scans_today': 0,
        'present': 0,
        'late': 0,
        'absent': 0
    }
    
    today_records = db.session.query(AttendanceRecord).join(ClassSession).filter(
        AttendanceRecord.student_id == current_user.id,
        ClassSession.date == today
    ).all()
    
    today_stats['scans_today'] = len(today_records)
    for record in today_records:
        if record.status == 'present':
            today_stats['present'] += 1
        elif record.status == 'late':
            today_stats['late'] += 1
        elif record.status == 'absent':
            today_stats['absent'] += 1
    
    # Get recent notifications
    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(Notification.created_at.desc()).limit(5).all()
    
    return render_template('student/dashboard.html',
        student=student,
        classes=classes,
        today_stats=today_stats,
        notifications=notifications,
        current_time=datetime.now()
    )


@student_bp.route('/classes')
@login_required
@student_required
def classes():
    """Student classes list"""
    student = Student.query.filter_by(user_id=current_user.id).first()
    
    enrollments = Enrollment.query.filter_by(
        student_id=current_user.id,
        status='active'
    ).all()
    
    classes = []
    for enrollment in enrollments:
        class_instance = enrollment.class_instance
        course = class_instance.course
        professor = User.query.get(class_instance.professor_id)
        
        # Get attendance stats
        total_sessions = ClassSession.query.filter_by(
            class_instance_id=class_instance.id,
            status='completed'
        ).count()
        
        attended_sessions = db.session.query(AttendanceRecord).join(ClassSession).filter(
            ClassSession.class_instance_id == class_instance.id,
            AttendanceRecord.student_id == current_user.id,
            AttendanceRecord.status.in_(['present', 'late', 'excused'])
        ).count()
        
        attendance_rate = round((attended_sessions / total_sessions * 100)) if total_sessions > 0 else 0
        
        classes.append({
            'id': class_instance.id,
            'code': course.code,
            'name': course.name,
            'description': course.description,
            'credits': course.credits,
            'professor': professor.full_name if professor else 'Unknown',
            'professor_email': professor.email if professor else '',
            'room': class_instance.room_location,
            'schedule': f"{', '.join(class_instance.days_list)} {class_instance.start_time}-{class_instance.end_time}",
            'attendance_rate': attendance_rate,
            'total_sessions': total_sessions,
            'attended_sessions': attended_sessions,
            'enrollment_date': enrollment.enrollment_date
        })
    
    return render_template('student/classes.html', classes=classes)


@student_bp.route('/classes/<class_id>')
@login_required
@student_required
def class_detail(class_id):
    """Class detail page"""
    enrollment = Enrollment.query.filter_by(
        student_id=current_user.id,
        class_instance_id=class_id,
        status='active'
    ).first()
    
    if not enrollment:
        flash('You are not enrolled in this class.', 'error')
        return redirect(url_for('student.classes'))
    
    class_instance = enrollment.class_instance
    course = class_instance.course
    professor = User.query.get(class_instance.professor_id)
    
    # Get all sessions
    sessions = ClassSession.query.filter_by(
        class_instance_id=class_id
    ).order_by(ClassSession.date).all()
    
    # Get student's attendance records for this class
    attendance_records = AttendanceRecord.query.filter(
        AttendanceRecord.student_id == current_user.id,
        AttendanceRecord.session_id.in_([s.id for s in sessions])
    ).all()
    
    attendance_map = {record.session_id: record for record in attendance_records}
    
    # Organize sessions
    past_sessions = []
    upcoming_sessions = []
    today = date.today()
    
    for session in sessions:
        session_data = {
            'id': session.id,
            'session_number': session.session_number,
            'date': session.date,
            'start_time': session.start_time,
            'end_time': session.end_time,
            'room': session.room_location,
            'status': session.status,
            'is_active': session.is_active,
            'attendance': attendance_map.get(session.id)
        }
        
        if session.date < today:
            past_sessions.append(session_data)
        else:
            upcoming_sessions.append(session_data)
    
    # Calculate stats
    completed_sessions = [s for s in past_sessions if s['status'] == 'completed']
    attended = sum(1 for s in completed_sessions if s['attendance'] and s['attendance'].status in ['present', 'late', 'excused'])
    attendance_rate = round((attended / len(completed_sessions) * 100)) if completed_sessions else 0
    
    class_data = {
        'id': class_instance.id,
        'code': course.code,
        'name': course.name,
        'description': course.description,
        'credits': course.credits,
        'professor': professor.full_name if professor else 'Unknown',
        'professor_email': professor.email if professor else '',
        'room': class_instance.room_location,
        'schedule': f"{', '.join(class_instance.days_list)} {class_instance.start_time}-{class_instance.end_time}",
        'enrollment_date': enrollment.enrollment_date
    }
    
    stats = {
        'total_sessions': len(completed_sessions),
        'attended_sessions': attended,
        'attendance_rate': attendance_rate
    }
    
    return render_template('student/class_detail.html',
        class_data=class_data,
        stats=stats,
        past_sessions=past_sessions,
        upcoming_sessions=upcoming_sessions
    )


@student_bp.route('/scan')
@login_required
@student_required
def scan():
    """QR code scanning page"""
    student = Student.query.filter_by(user_id=current_user.id).first()
    
    # Check if QR data is in URL params (from scanning)
    qr_data = request.args.get('data')
    
    return render_template('student/scan.html', 
        student=student,
        qr_data=qr_data
    )


@student_bp.route('/scan/process', methods=['POST'])
@login_required
@student_required
def process_scan():
    """Process QR code scan"""
    try:
        data = request.get_json()
        qr_data = data.get('qr_data')
        location_data = data.get('location')  # Get location from request
        
        if not qr_data:
            return jsonify({'success': False, 'error': 'No QR data provided'})
        
        # Parse QR data
        if isinstance(qr_data, str):
            qr_data = json.loads(qr_data)
        
        # Validate QR code
        validation = QRCodeGenerator.validate_qr(qr_data)
        
        if not validation['isValid']:
            return jsonify({'success': False, 'error': validation['error']})
        
        session_id = validation['sessionId']
        
        # Get session
        session = ClassSession.query.get(session_id)
        if not session:
            return jsonify({'success': False, 'error': 'Session not found'})
        
        if session.status != 'active':
            return jsonify({'success': False, 'error': 'Session is not active'})
        
        # Check enrollment
        enrollment = Enrollment.query.filter_by(
            student_id=current_user.id,
            class_instance_id=session.class_instance_id,
            status='active'
        ).first()
        
        if not enrollment:
            return jsonify({'success': False, 'error': 'You are not enrolled in this class'})
        
        # Check if already marked
        existing = AttendanceRecord.query.filter_by(
            session_id=session_id,
            student_id=current_user.id
        ).first()
        
        if existing:
            return jsonify({
                'success': False, 
                'error': 'Attendance already marked',
                'attendance': {
                    'status': existing.status,
                    'scanned_at': existing.scanned_at.isoformat()
                }
            })
        
        # Verify location if enabled and location provided
        location_verified = False
        location_distance = None
        
        from flask import current_app
        if current_app.config.get('ENABLE_GEOLOCATION', False) and location_data:
            student_lat = location_data.get('latitude')
            student_lng = location_data.get('longitude')
            
            if student_lat and student_lng:
                room_location = session.room_location
                classroom_coords = current_app.config.get('CLASSROOM_LOCATIONS', {}).get(room_location)
                
                if classroom_coords:
                    # Calculate distance using Haversine formula
                    from math import radians, cos, sin, asin, sqrt
                    
                    def haversine(lat1, lon1, lat2, lon2):
                        """Calculate distance between two points in meters"""
                        R = 6371000  # Earth radius in meters
                        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
                        dlat = lat2 - lat1
                        dlon = lon2 - lon1
                        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                        c = 2 * asin(sqrt(a))
                        return R * c
                    
                    location_distance = haversine(
                        student_lat, student_lng,
                        classroom_coords['lat'], classroom_coords['lng']
                    )
                    
                    location_verified = location_distance <= classroom_coords.get('radius', 100)
                    
                    # Optional: Reject if location verification fails
                    # if not location_verified:
                    #     return jsonify({
                    #         'success': False,
                    #         'error': f'You must be within {classroom_coords.get("radius", 100)}m of the classroom. You are {int(location_distance)}m away.'
                    #     })
        
        # Determine if late
        session_start = datetime.combine(session.date, datetime.strptime(session.start_time, '%H:%M').time())
        now = datetime.now()
        minutes_late = int((now - session_start).total_seconds() / 60)
        is_late = minutes_late > 5
        
        # Create attendance record
        status = 'late' if is_late else 'present'
        
        attendance = AttendanceRecord(
            id=str(uuid.uuid4()),
            session_id=session_id,
            student_id=current_user.id,
            scanned_at=now,
            status=status,
            minutes_late=minutes_late if is_late else 0,
            device_fingerprint=request.headers.get('User-Agent', 'unknown'),
            ip_address=request.remote_addr,
            latitude=location_data.get('latitude') if location_data else None,
            longitude=location_data.get('longitude') if location_data else None,
            location_verified=location_verified,
            location_distance=location_distance
        )
        
        db.session.add(attendance)
        
        # Update session count
        session.attendance_count += 1
        
        # Create notification
        class_instance = session.class_instance
        course = class_instance.course
        
        notification = Notification(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            type='attendance_recorded',
            title='Attendance Recorded',
            message=f'Marked {status} for {course.code}',
            link='/student/attendance',
            session_id=session_id,
            metadata=json.dumps({
                'className': course.code,
                'status': status,
                'minutesLate': minutes_late if is_late else 0
            })
        )
        db.session.add(notification)
        
        db.session.commit()
        
        # Get student info for real-time update
        student = Student.query.filter_by(user_id=current_user.id).first()
        
        # Emit socket event for real-time updates
        socketio.emit('attendance_update', {
            'sessionId': session_id,
            'studentId': current_user.id,
            'status': status,
            'scanned_at': now.isoformat(),
            'attendanceCount': session.attendance_count,
            'newRecord': {
                'name': current_user.full_name,
                'student_id': student.student_id if student else current_user.email,
                'status': status,
                'time': now.strftime('%H:%M:%S')
            }
        }, room=f'session-{session_id}')
        
        return jsonify({
            'success': True,
            'message': f'Attendance marked: {status}',
            'attendance': {
                'status': status,
                'scanned_at': now.isoformat(),
                'minutes_late': minutes_late if is_late else 0,
                'class': {
                    'code': course.code,
                    'name': course.name
                }
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


@student_bp.route('/attendance')
@login_required
@student_required
def attendance():
    """Attendance history page"""
    student = Student.query.filter_by(user_id=current_user.id).first()
    
    # Get all attendance records
    records = db.session.query(AttendanceRecord, ClassSession, ClassInstance, Course).join(
        ClassSession, AttendanceRecord.session_id == ClassSession.id
    ).join(
        ClassInstance, ClassSession.class_instance_id == ClassInstance.id
    ).join(
        Course, ClassInstance.course_id == Course.id
    ).filter(
        AttendanceRecord.student_id == current_user.id
    ).order_by(AttendanceRecord.scanned_at.desc()).all()
    
    attendance_list = []
    for record, session, class_instance, course in records:
        professor = User.query.get(class_instance.professor_id)
        attendance_list.append({
            'id': record.id,
            'date': session.date,
            'time': record.scanned_at.strftime('%H:%M'),
            'status': record.status,
            'minutes_late': record.minutes_late,
            'class_code': course.code,
            'class_name': course.name,
            'professor': professor.full_name if professor else 'Unknown',
            'room': session.room_location
        })
    
    # Calculate overall stats
    total = len(attendance_list)
    present = sum(1 for a in attendance_list if a['status'] == 'present')
    late = sum(1 for a in attendance_list if a['status'] == 'late')
    absent = sum(1 for a in attendance_list if a['status'] == 'absent')
    excused = sum(1 for a in attendance_list if a['status'] == 'excused')
    
    stats = {
        'total': total,
        'present': present,
        'late': late,
        'absent': absent,
        'excused': excused,
        'attendance_rate': round(((present + late + excused) / total * 100)) if total > 0 else 0
    }
    
    return render_template('student/attendance.html',
        attendance_list=attendance_list,
        stats=stats
    )


@student_bp.route('/profile')
@login_required
@student_required
def profile():
    """Student profile page"""
    student = Student.query.filter_by(user_id=current_user.id).first()
    return render_template('student/profile.html', student=student)


@student_bp.route('/profile/update', methods=['POST'])
@login_required
@student_required
def update_profile():
    """Update student profile"""
    try:
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        phone = request.form.get('phone', '').strip()
        major = request.form.get('major', '').strip()
        
        if first_name:
            current_user.first_name = first_name
        if last_name:
            current_user.last_name = last_name
        if phone:
            current_user.phone = phone
        
        student = Student.query.filter_by(user_id=current_user.id).first()
        if student and major:
            student.major = major
        
        db.session.commit()
        flash('Profile updated successfully.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating profile: {str(e)}', 'error')
    
    return redirect(url_for('student.profile'))
