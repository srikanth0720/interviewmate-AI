from backend.questions import QUESTIONS

def test_question_categories_exist():
    assert {"Python", "DSA", "DBMS", "HR", "Behavioral"} <= set(QUESTIONS)

def test_each_category_has_questions():
    assert all(len(items) >= 5 for items in QUESTIONS.values())
