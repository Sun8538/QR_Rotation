"""
Seed initial data for the database
"""
from datetime import datetime, date


def seed_initial_data():
    """Seed the database with initial data"""
    from app import db
    from app.models import Department, AcademicPeriod, Course
    
    # Check if data already exists
    if Department.query.first():
        return
    
    print("🌱 Seeding initial data...")
    
    # Create departments
    departments = [
        Department(id='dept-1', code='CSC', name='Computer Science'),
        Department(id='dept-2', code='MAT', name='Mathematics'),
        Department(id='dept-3', code='PHY', name='Physics'),
        Department(id='dept-4', code='ENG', name='English'),
        Department(id='dept-5', code='ECE', name='Electronics & Communication'),
    ]
    
    for dept in departments:
        db.session.add(dept)
    
    # Create academic periods
    current_year = datetime.now().year
    periods = [
        AcademicPeriod(
            id='period-1',
            name=f'Spring {current_year}',
            year=current_year,
            semester='spring',
            start_date=date(current_year, 1, 15),
            end_date=date(current_year, 5, 15),
            is_current=True,
            is_active=True
        ),
        AcademicPeriod(
            id='period-2',
            name=f'Fall {current_year}',
            year=current_year,
            semester='fall',
            start_date=date(current_year, 8, 15),
            end_date=date(current_year, 12, 15),
            is_current=False,
            is_active=True
        ),
    ]
    
    for period in periods:
        db.session.add(period)
    
    # Create courses
    courses = [
        Course(id='course-1', code='CSC-101', name='Introduction to Computer Science', description='Fundamentals of computing and programming', credits=3, department_id='dept-1'),
        Course(id='course-2', code='CSC-201', name='Data Structures', description='Study of data organization and algorithms', credits=4, department_id='dept-1'),
        Course(id='course-3', code='CSC-301', name='Database Systems', description='Design and implementation of database systems', credits=3, department_id='dept-1'),
        Course(id='course-4', code='MAT-101', name='Calculus I', description='Differential and integral calculus', credits=4, department_id='dept-2'),
        Course(id='course-5', code='MAT-201', name='Linear Algebra', description='Vector spaces and linear transformations', credits=3, department_id='dept-2'),
        Course(id='course-6', code='PHY-101', name='Physics I', description='Mechanics and thermodynamics', credits=4, department_id='dept-3'),
        Course(id='course-7', code='ECE-101', name='Basic Electronics', description='Introduction to electronic circuits', credits=3, department_id='dept-5'),
    ]
    
    for course in courses:
        db.session.add(course)
    
    db.session.commit()
    print("✅ Initial data seeded successfully!")
