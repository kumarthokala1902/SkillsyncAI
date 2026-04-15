import os
import sys
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app, db
from models import SkillQuestion

def seed_questions():
    with app.app_context():
        # Clear existing questions to avoid duplicates during development
        # db.session.query(SkillQuestion).delete()
        
        questions = [
            # PYTHON
            {
                "category": "python", "type": "mcq", 
                "question_text": "What is the output of print(type([]) is list)?",
                "options_json": json.dumps(["True", "False", "Error", "None"]),
                "correct_answer": "True"
            },
            {
                "category": "python", "type": "mcq", 
                "question_text": "Which of these is used for list comprehension?",
                "options_json": json.dumps(["[x for x in list]", "{x for x in list}", "(x for x in list)", "None of these"]),
                "correct_answer": "[x for x in list]"
            },
            {
                "category": "python", "type": "mcq", 
                "question_text": "How do you define a function in Python?",
                "options_json": json.dumps(["def func():", "function func():", "func():", "define func():"]),
                "correct_answer": "def func():"
            },
            {
                "category": "python", "type": "mcq", 
                "question_text": "What is __init__ in Python classes?",
                "options_json": json.dumps(["A constructor method", "A destructor method", "A static method", "An instance variable"]),
                "correct_answer": "A constructor method"
            },
            {
                "category": "python", "type": "mcq", 
                "question_text": "Which module is used for regular expressions?",
                "options_json": json.dumps(["re", "regex", "regexp", "re-py"]),
                "correct_answer": "re"
            },
            {
                "category": "python", "type": "coding", 
                "question_text": "Write a function 'fib(n)' that returns the n-th Fibonacci number.",
                "base_code": "def fib(n):\n    # Your code here\n    pass"
            },
            {
                "category": "python", "type": "coding", 
                "question_text": "Write a function 'is_palindrome(s)' that returns True if the string s is a palindrome.",
                "base_code": "def is_palindrome(s):\n    # Your code here\n    pass"
            },

            # JAVASCRIPT
            {
                "category": "javascript", "type": "mcq", 
                "question_text": "What is the result of '2' + 2?",
                "options_json": json.dumps(["'22'", "4", "NaN", "Error"]),
                "correct_answer": "'22'"
            },
            {
                "category": "javascript", "type": "mcq", 
                "question_text": "Which keyword is used to define a constant in ES6?",
                "options_json": json.dumps(["const", "let", "var", "constant"]),
                "correct_answer": "const"
            },
            {
                "category": "javascript", "type": "mcq", 
                "question_text": "What does '===' operator do?",
                "options_json": json.dumps(["Checks value and type equality", "Checks value equality ONLY", "Assignment operator", "None of these"]),
                "correct_answer": "Checks value and type equality"
            },
            {
                "category": "javascript", "type": "mcq", 
                "question_text": "How do you write a comment in JavaScript?",
                "options_json": json.dumps(["//", "/* */", "#", "Both // and /* */"]),
                "correct_answer": "Both // and /* */"
            },
            {
                "category": "javascript", "type": "mcq", 
                "question_text": "What is the output of console.log(typeof null)?",
                "options_json": json.dumps(["'object'", "'null'", "'undefined'", "'boolean'"]),
                "correct_answer": "'object'"
            },
            {
                "category": "javascript", "type": "coding", 
                "question_text": "Write a function 'sumArray(arr)' that returns the sum of all elements in an array.",
                "base_code": "function sumArray(arr) {\n    // Your code here\n}"
            },
            {
                "category": "javascript", "type": "coding", 
                "question_text": "Write a function 'findMax(arr)' that returns the maximum number in an array.",
                "base_code": "function findMax(arr) {\n    // Your code here\n}"
            },

            # DSA
            {
                "category": "dsa", "type": "mcq", 
                "question_text": "What is the average time complexity of QuickSort?",
                "options_json": json.dumps(["O(n log n)", "O(n^2)", "O(n)", "O(log n)"]),
                "correct_answer": "O(n log n)"
            },
            {
                "category": "dsa", "type": "mcq", 
                "question_text": "Which data structure follows LIFO?",
                "options_json": json.dumps(["Stack", "Queue", "Linked List", "Tree"]),
                "correct_answer": "Stack"
            },
            {
                "category": "dsa", "type": "mcq", 
                "question_text": "What is the time complexity of binary search?",
                "options_json": json.dumps(["O(log n)", "O(n)", "O(n log n)", "O(1)"]),
                "correct_answer": "O(log n)"
            },
            {
                "category": "dsa", "type": "mcq", 
                "question_text": "Which of these is NOT a stable sorting algorithm?",
                "options_json": json.dumps(["Quick Sort", "Merge Sort", "Bubble Sort", "Insertion Sort"]),
                "correct_answer": "Quick Sort"
            },
            {
                "category": "dsa", "type": "mcq", 
                "question_text": "What is a balanced binary tree?",
                "options_json": json.dumps(["Heights of subtrees differ by at most 1", "Levels differ by at most 1", "Total nodes is 2^n - 1", "All leaf nodes are at same level"]),
                "correct_answer": "Heights of subtrees differ by at most 1"
            },
            {
                "category": "dsa", "type": "coding", 
                "question_text": "Reverse a Singly Linked List.",
                "base_code": "class ListNode:\n    def __init__(self, val=0, next=None):\n        self.val = val\n        self.next = next\n\ndef reverseList(head: ListNode) -> ListNode:\n    # Your code here"
            },
            {
                "category": "dsa", "type": "coding", 
                "question_text": "Find the middle element of a linked list.",
                "base_code": "def findMiddle(head):\n    # Your code here"
            },

            # C++
            {
                "category": "cpp", "type": "mcq", 
                "question_text": "Which operator is used to access members of a pointer to a struct/class?",
                "options_json": json.dumps(["->", ".", "&", "*"]),
                "correct_answer": "->"
            },
            {
                "category": "cpp", "type": "mcq", 
                "question_text": "What is the size of 'char' in C++?",
                "options_json": json.dumps(["1 byte", "2 bytes", "4 bytes", "Depends on OS"]),
                "correct_answer": "1 byte"
            },
            {
                "category": "cpp", "type": "mcq", 
                "question_text": "What is a virtual function used for in C++?",
                "options_json": json.dumps(["Runtime polymorphism", "Compile-time polymorphism", "Encapsulation", "Static binding"]),
                "correct_answer": "Runtime polymorphism"
            },
            {
                "category": "cpp", "type": "mcq", 
                "question_text": "Which library is used for input-output?",
                "options_json": json.dumps(["iostream", "stdio.h", "conio.h", "stdlib.h"]),
                "correct_answer": "iostream"
            },
            {
                "category": "cpp", "type": "mcq", 
                "question_text": "What is 'this' pointer?",
                "options_json": json.dumps(["Points to current object", "Points to parent object", "A global pointer", "None of these"]),
                "correct_answer": "Points to current object"
            },
            {
                "category": "cpp", "type": "coding", 
                "question_text": "Implement a class 'Rectangle' with getArea() method.",
                "base_code": "class Rectangle {\npublic:\n    int width, height;\n    int getArea() {\n        // Your code here\n    }\n};"
            },
            {
                "category": "cpp", "type": "coding", 
                "question_text": "Swap two numbers using pointers.",
                "base_code": "void swap(int* a, int* b) {\n    // Your code here\n}"
            },

            # JAVA
            {
                "category": "java", "type": "mcq", 
                "question_text": "Which of these is NOT a primitive data type in Java?",
                "options_json": json.dumps(["String", "int", "float", "boolean"]),
                "correct_answer": "String"
            },
            {
                "category": "java", "type": "mcq", 
                "question_text": "Which keyword is used to inherit a class?",
                "options_json": json.dumps(["extends", "implements", "inherits", "using"]),
                "correct_answer": "extends"
            },
            {
                "category": "java", "type": "mcq", 
                "question_text": "What is the default value of a boolean variable?",
                "options_json": json.dumps(["false", "true", "null", "0"]),
                "correct_answer": "false"
            },
            {
                "category": "java", "type": "mcq", 
                "question_text": "Which method is the starting point of any Java program?",
                "options_json": json.dumps(["main()", "start()", "init()", "run()"]),
                "correct_answer": "main()"
            },
            {
                "category": "java", "type": "mcq", 
                "question_text": "What does garbage collector do?",
                "options_json": json.dumps(["Reclaims unused memory", "Deletes files", "Optimizes code", "Frees CPU cycles"]),
                "correct_answer": "Reclaims unused memory"
            },
            {
                "category": "java", "type": "coding", 
                "question_text": "Write a Java method to check if a number is even.",
                "base_code": "public class Main {\n    public static boolean isEven(int n) {\n        // Your code here\n    }\n}"
            },
            {
                "category": "java", "type": "coding", 
                "question_text": "Find the factorial of a number using recursion.",
                "base_code": "public int factorial(int n) {\n    // Your code here\n}"
            },

            # DEVOPS
            {
                "category": "devops", "type": "mcq", 
                "question_text": "What does 'CI' stand for in 'CI/CD'?",
                "options_json": json.dumps(["Continuous Integration", "Constant Improvement", "Code Inspection", "Complete Installation"]),
                "correct_answer": "Continuous Integration"
            },
            {
                "category": "devops", "type": "mcq", 
                "question_text": "Which tool is NOT primarily for containerization?",
                "options_json": json.dumps(["Jenkins", "Docker", "Podman", "LXC"]),
                "correct_answer": "Jenkins"
            },
            {
                "category": "devops", "type": "mcq", 
                "question_text": "What is the purpose of Kubernetes?",
                "options_json": json.dumps(["Container Orchestration", "Source Code Management", "Unit Testing", "Database Management"]),
                "correct_answer": "Container Orchestration"
            },
            {
                "category": "devops", "type": "mcq", 
                "question_text": "Which command is used to see container logs in Docker?",
                "options_json": json.dumps(["docker logs", "docker show", "docker view", "docker inspect"]),
                "correct_answer": "docker logs"
            },
            {
                "category": "devops", "type": "mcq", 
                "question_text": "What is 'Infrastructure as Code'?",
                "options_json": json.dumps(["Managing infra via config files", "Coding on hardware", "Writing OS in Python", "None of these"]),
                "correct_answer": "Managing infra via config files"
            },
            {
                "category": "devops", "type": "coding", 
                "question_text": "Write a simple Dockerfile for a Node.js app.",
                "base_code": "# Use node:14 image\nFROM node:14\n# Your code here"
            },
            {
                "category": "devops", "type": "coding", 
                "question_text": "Write a simple Bash script to check if a file 'config.txt' exists.",
                "base_code": "#!/bin/bash\n# Check if config.txt exists"
            }
        ]

        for q_data in questions:
            # Check if question already exists (simplified check)
            exists = SkillQuestion.query.filter_by(
                category=q_data["category"], 
                question_text=q_data["question_text"]
            ).first()
            if not exists:
                q = SkillQuestion(**q_data)
                db.session.add(q)
        
        db.session.commit()
        print(f"Seeded {len(questions)} questions successfully.")

if __name__ == "__main__":
    seed_questions()
