import numpy as np
from scipy.optimize import linear_sum_assignment

def compute_cost(faculty, course, weights, limits):
    """
    Computes the cost for assigning a given course (ignoring sections)
    to a faculty member.

    Args:
        faculty (dict): Contains faculty attributes.
        course (dict): Contains course attributes.
                       It should include a field 'course_code' used for lookup.
        weights (dict): Weights for different cost components.
        limits (dict): Limits such as maximum courses and per-semester limits.

    Returns:
        float: Total cost for this assignment.
    """
    # Use original course code for preference lookup.
    course_code = course['course_code']

    # 1. Preference cost
    pref = faculty['preferences'].get(course_code, None)
    if pref is None:
        pref_cost = 100  # High cost if the course is not in the preference list
    else:
        if pref == 1:
            pref_cost = 0
        elif pref == 2:
            pref_cost = 10
        elif pref == 3:
            pref_cost = 20
        else:
            pref_cost = 30

    # 2. Workload cost: Lower cost if the faculty has more capacity remaining.
    overall_penalty = weights['overall'] * (limits['max_courses'] - faculty['courses_left'])
    ug_penalty = 0
    if course['type'] == 'UG':
        ug_penalty = weights['ug'] * (limits['max_ug'] - faculty['ug_left'])
    workload_cost = overall_penalty + ug_penalty

    # 3. Semester cost: Enforce per-semester limits.
    semester_cost = 0
    if course['type'] == 'UG':
        if faculty['current_semester_ug'] >= limits['ug_semester']:
            semester_cost += 1000  # High penalty for exceeding UG limit
    elif course['type'] == 'PG':
        if faculty['current_semester_pg'] >= limits['pg_semester']:
            semester_cost += 1000  # High penalty for exceeding PG limit

    # 4. Historical cost: Penalize repeated teaching of the same course.
    history_cost = weights['history'] * faculty['history'].get(course_code, 0)

    # 5. Timestamp cost: For UG, lower (earlier) is better; for PG, later is better.
    if course['type'] == 'UG':
        timestamp_cost = weights['timestamp'] * faculty['timestamp']
    elif course['type'] == 'PG':
        timestamp_cost = weights['timestamp'] * (1 - faculty['timestamp'])
    else:
        timestamp_cost = 0

    total_cost = pref_cost + workload_cost + semester_cost + history_cost + timestamp_cost
    return total_cost

def expand_courses(courses):
    """
    Expands each course into multiple sections based on the 'sections' attribute.
    Each expanded entry contains the original course code in 'course_code'
    and a separate 'section' field. The 'code' field is updated to include the section.

    Args:
        courses (list): List of course dictionaries. Each dict should include:
                        - 'code': Original course identifier (e.g. "C1")
                        - 'sections': Number of sections (default is 1 if missing)
                        - 'type': 'UG' or 'PG'

    Returns:
        list: Expanded list where each section is a separate dictionary.
    """
    expanded = []
    for course in courses:
        num_sections = course.get('sections', 1)
        # Retain the original course code in a separate key.
        original_code = course['code']
        for sec in range(1, num_sections + 1):
            section_entry = course.copy()
            section_entry['course_code'] = original_code  # For preference lookup
            # Update 'code' to reflect section, e.g., "C1-S1", "C1-S2", etc.
            section_entry['code'] = f"{original_code}-S{sec}"
            section_entry['section'] = sec
            expanded.append(section_entry)
    return expanded

def build_cost_matrix(faculties, expanded_courses, weights, limits):
    """
    Builds a cost matrix for all faculty-section pairs.

    Args:
        faculties (list): List of faculty attribute dictionaries.
        expanded_courses (list): List of course (section) dictionaries.
        weights (dict): Weights for cost components.
        limits (dict): Assignment limits.

    Returns:
        numpy.ndarray: Cost matrix of shape (num_faculties, num_sections).
    """
    num_faculties = len(faculties)
    num_sections = len(expanded_courses)
    cost_matrix = np.zeros((num_faculties, num_sections))
    for i, faculty in enumerate(faculties):
        for j, course in enumerate(expanded_courses):
            cost_matrix[i, j] = compute_cost(faculty, course, weights, limits)
    return cost_matrix

def allocate_courses(cost_matrix):
    """
    Uses the Hungarian algorithm to allocate sections based on the cost matrix.
    Returns both the allocation and the list of unassigned section indices.

    Args:
        cost_matrix (numpy.ndarray): The cost matrix.

    Returns:
        allocation (list of tuples): Each tuple is (faculty_index, section_index).
        unassigned (list): List of section indices that remain unassigned.
    """
    row_ind, col_ind = linear_sum_assignment(cost_matrix)
    allocation = list(zip(row_ind, col_ind))

    # Determine which sections (columns) were not assigned
    assigned_sections = set(col_ind)
    total_sections = set(range(cost_matrix.shape[1]))
    unassigned = list(total_sections - assigned_sections)

    return allocation, unassigned

def run_allotment(faculties, courses):

    expanded_courses = expand_courses(courses)

    # Define weights for each cost component.
    weights = {
        'overall': 1,      # weight for overall workload penalty
        'ug': 1,           # weight for UG-specific workload penalty
        'history': 5,      # weight for historical teaching penalty
        'timestamp': 10    # weight for timestamp penalty
    }

    # Define limits for assignments.
    limits = {
        'max_courses': 5,      # maximum courses per cycle per faculty
        'max_ug': 2,           # maximum UG courses per cycle per faculty
        'ug_semester': 1,      # maximum UG courses per semester per faculty
        'pg_semester': 2       # maximum PG courses per semester per faculty
    }

    # Build the cost matrix using the expanded course list.
    cost_matrix = build_cost_matrix(faculties, expanded_courses, weights, limits)
    print("Cost Matrix:")
    print(cost_matrix)

    # Allocate sections using the Hungarian algorithm.
    allocation, unassigned = allocate_courses(cost_matrix)
    allocations = {}
    print("\nAllocation:")
    for faculty_idx, section_idx in allocation:
        faculty_name = faculties[faculty_idx]['name']
        section_code = expanded_courses[section_idx]['code']
        print(f"{faculty_name} is assigned to {section_code}")
        allocations[faculty_name] = section_code

    # Print unallotted sections.
    unallotted_sections = []
    if unassigned:
        print("\nUnallotted Sections:")
        for section_idx in unassigned:
            print(expanded_courses[section_idx]['code'])
            unallotted_sections.append(expanded_courses[section_idx]['code'])
    else:
        print("\nAll sections have been allotted.")

    return allocations, unallotted_sections
