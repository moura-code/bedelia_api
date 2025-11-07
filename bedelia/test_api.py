#!/usr/bin/env python3
"""
Test script for Bedelia API endpoints.

Run after loading data with: python3 manage.py load_bedelia

Usage:
    python3 test_api.py
"""
import requests
import json
from pprint import pprint

# Base URL for API
BASE_URL = "http://localhost:8000/api"

def print_section(title):
    """Print a section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def test_programs():
    """Test getting all programs."""
    print_section("TEST 1: Get All Programs")
    
    response = requests.get(f"{BASE_URL}/programs/")
    
    if response.status_code == 200:
        programs = response.json()
        print(f"✅ Found {len(programs)} programs")
        for prog in programs[:5]:
            print(f"  - {prog['name']} ({prog['plan_year']})")
        return programs[0]['id'] if programs else None
    else:
        print(f"❌ Error: {response.status_code}")
        return None


def test_subjects(program_id=None):
    """Test getting subjects."""
    print_section("TEST 2: Get Subjects")
    
    url = f"{BASE_URL}/subjects/"
    if program_id:
        url += f"?programs={program_id}"
    
    response = requests.get(url)
    
    if response.status_code == 200:
        subjects = response.json()
        print(f"✅ Found {len(subjects)} subjects")
        for subj in subjects[:5]:
            print(f"  - {subj['code']}: {subj['name']} ({subj['credits']} credits)")
    else:
        print(f"❌ Error: {response.status_code}")


def test_available_courses():
    """Test checking available courses."""
    print_section("TEST 3: Check Available Courses")
    
    completed = ["1020", "GAL1", "1411"]
    
    payload = {
        "completed_codes": completed,
        "only_active": False,
        "offering_type": "COURSE"
    }
    
    response = requests.post(
        f"{BASE_URL}/subjects/available_courses/",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Completed: {data['completed_count']} courses")
        print(f"✅ Available: {data['available_count']} courses")
        print("\nFirst 5 available courses:")
        for offering in data['available_offerings'][:5]:
            subj = offering['subject']
            print(f"  - {subj['code']}: {subj['name']}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)


def test_unlocked_by():
    """Test checking what courses unlock."""
    print_section("TEST 4: What Does CDIV Unlock?")
    
    payload = {
        "course_codes": ["CDIV"],
        "only_active": False
    }
    
    response = requests.post(
        f"{BASE_URL}/subjects/unlocked_by/",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Completing {data['input_courses']} unlocks {data['unlocked_count']} courses")
        print("\nSome unlocked courses:")
        for offering in data['unlocked_offerings'][:10]:
            subj = offering['subject']
            print(f"  - {subj['code']}: {subj['name']}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)


def test_recommendations():
    """Test course recommendations."""
    print_section("TEST 5: Course Recommendations")
    
    completed = ["1020", "GAL1", "1411", "1061"]
    
    payload = {
        "completed_codes": completed,
        "only_active": False,
        "max_results": 5
    }
    
    response = requests.post(
        f"{BASE_URL}/course-recommendations/",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Completed: {data['completed_count']} courses")
        print(f"✅ Available now: {data['total_available']} courses")
        print("\nTop recommendations:")
        for rec in data['recommendations']:
            subj = rec['offering']['subject']
            print(f"  [{rec['priority'].upper()}] {subj['code']}: {subj['name']}")
            print(f"      → {rec['reason']}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)


def test_pathway():
    """Test course pathway planning."""
    print_section("TEST 6: Pathway to Target Course")
    
    payload = {
        "target_code": "1321",  # PROGRAMACION 2
        "completed_codes": ["1020", "GAL1"]
    }
    
    response = requests.post(
        f"{BASE_URL}/course-pathway/",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        data = response.json()
        target = data['target_course']
        print(f"🎯 Target: {target['code']} - {target['name']}")
        print(f"✅ Completed: {len(data['completed_courses'])} courses")
        print(f"📋 Missing: {data['total_missing']} courses")
        print(f"🚦 Can take now: {data['can_take_now']}")
        
        if data['pathway']:
            print("\nCourses you need first:")
            for course in data['pathway']:
                print(f"  - {course['code']}: {course['name']} ({course['credits']} credits)")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)


def main():
    """Run all tests."""
    print("\n🧪 BEDELIA API TEST SUITE")
    print("=" * 80)
    print("Make sure the Django server is running:")
    print("  cd bedelia && python3 manage.py runserver")
    print("=" * 80)
    
    try:
        # Test basic endpoints
        program_id = test_programs()
        test_subjects(program_id)
        
        # Test custom smart endpoints
        test_available_courses()
        test_unlocked_by()
        test_recommendations()
        test_pathway()
        
        print_section("✅ ALL TESTS COMPLETED")
        
    except requests.ConnectionError:
        print("\n❌ ERROR: Could not connect to server")
        print("Please start the server with: python3 manage.py runserver")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

