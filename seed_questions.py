from app import app, db
from models import SkillQuestion
import json

questions = [
    # PYTHON
    {
        "category": "python",
        "type": "mcq",
        "question_text": "Which of the following statements about Python's Global Interpreter Lock (GIL) is true?",
        "options_json": json.dumps(["A) It allows multiple threads to execute Python bytecodes simultaneously in CPython.", "B) It is a mutex that protects access to Python objects, preventing multiple threads from executing Python bytecodes at once.", "C) It only impacts multi-processing, not multi-threading.", "D) It makes Python fully thread-safe for all external C extensions automatically."]),
        "correct_answer": "B) It is a mutex that protects access to Python objects, preventing multiple threads from executing Python bytecodes at once."
    },
    {
        "category": "python",
        "type": "mcq",
        "question_text": "What is the time complexity of a list slicing operation `lst[a:b]` in Python?",
        "options_json": json.dumps(["A) O(1)", "B) O(b-a)", "C) O(N) where N is len(lst)", "D) O(log(b-a))"]),
        "correct_answer": "B) O(b-a)"
    },
    {
        "category": "python",
        "type": "mcq",
        "question_text": "Which of the following is the most memory-efficient way to concatenate a large number of strings in Python?",
        "options_json": json.dumps(["A) Using the + operator in a loop", "B) Using the string += operator", "C) Storing strings in a list and using ''.join()", "D) Using string interpolation (f-strings) inside a loop"]),
        "correct_answer": "C) Storing strings in a list and using ''.join()"
    },
    {
        "category": "python",
        "type": "mcq",
        "question_text": "What does the `@classmethod` decorator do in Python?",
        "options_json": json.dumps(["A) It passes the instance as the first argument automatically.", "B) It passes the class as the first argument automatically.", "C) It prevents the method from modifying class state.", "D) It acts as a static method with no implicit first argument."]),
        "correct_answer": "B) It passes the class as the first argument automatically."
    },
    {
        "category": "python",
        "type": "mcq",
        "question_text": "Which collections module data structure is optimized for fast appends and pops from both ends?",
        "options_json": json.dumps(["A) list", "B) set", "C) deque", "D) OrderedDict"]),
        "correct_answer": "C) deque"
    },
    {
        "category": "python",
        "type": "coding",
        "question_text": "Write a python function `find_longest_substring(s: str) -> int` that takes a string and returns the length of the longest substring without repeating characters. Optimal time complexity should be O(N).",
        "base_code": "def find_longest_substring(s: str) -> int:\n    # Your code here\n    pass",
        "correct_answer": "def find_longest_substring(s: str) -> int:\n    char_index = {}\n    max_len = 0\n    start = 0\n    for i, c in enumerate(s):\n        if c in char_index and char_index[c] >= start:\n            start = char_index[c] + 1\n        char_index[c] = i\n        max_len = max(max_len, i - start + 1)\n    return max_len"
    },
    {
        "category": "python",
        "type": "coding",
        "question_text": "Write a python function `lru_cache_impl(capacity: int)` that returns a class implementing an LRU Cache with `get(key)` and `put(key, value)` both running in O(1) time.",
        "base_code": "class LRUCache:\n    def __init__(self, capacity: int):\n        pass\n\n    def get(self, key: int) -> int:\n        pass\n\n    def put(self, key: int, value: int) -> None:\n        pass",
        "correct_answer": "from collections import OrderedDict\nclass LRUCache:\n    def __init__(self, capacity: int):\n        self.cache = OrderedDict()\n        self.capacity = capacity\n    def get(self, key: int) -> int:\n        if key not in self.cache: return -1\n        self.cache.move_to_end(key)\n        return self.cache[key]\n    def put(self, key: int, value: int) -> None:\n        if key in self.cache: self.cache.move_to_end(key)\n        self.cache[key] = value\n        if len(self.cache) > self.capacity:\n            self.cache.popitem(last=False)"
    },

    # JAVA
    {
        "category": "java",
        "type": "mcq",
        "question_text": "In Java Database Connectivity (JDBC), what is the difference between Statement and PreparedStatement?",
        "options_json": json.dumps(["A) Statement is faster for compiled queries.", "B) PreparedStatement prevents SQL injection by precompiling the SQL query.", "C) Statement can only execute SELECT queries.", "D) PreparedStatement cannot handle parameterized queries."]),
        "correct_answer": "B) PreparedStatement prevents SQL injection by precompiling the SQL query."
    },
    {
        "category": "java",
        "type": "mcq",
        "question_text": "Which of the following internal mechanisms does HashMap use in Java 8+ to resolve high collision rates?",
        "options_json": json.dumps(["A) Linear Probing", "B) Separate Chaining exclusively with LinkedLists", "C) Transforming LinkedList buckets into Red-Black Trees when bucket size exceeds 8", "D) Double Hashing"]),
        "correct_answer": "C) Transforming LinkedList buckets into Red-Black Trees when bucket size exceeds 8"
    },
    {
        "category": "java",
        "type": "mcq",
        "question_text": "What happens if an exception is thrown inside a `finally` block?",
        "options_json": json.dumps(["A) It is ignored and the original exception is propagated.", "B) The program terminates immediately without executing the rest of the block.", "C) The original exception is lost and the exception from the finally block propagates.", "D) It is automatically logged and swallowed."]),
        "correct_answer": "C) The original exception is lost and the exception from the finally block propagates."
    },
    {
        "category": "java",
        "type": "mcq",
        "question_text": "Which JVM Garbage Collector is designed for multi-processor machines with large memories and targets pause-time relatively predictably?",
        "options_json": json.dumps(["A) Serial GC", "B) Parallel GC", "C) G1 GC (Garbage-First)", "D) Epsilon GC"]),
        "correct_answer": "C) G1 GC (Garbage-First)"
    },
    {
        "category": "java",
        "type": "mcq",
        "question_text": "What is the primary benefit of the `volatile` keyword in Java multi-threading?",
        "options_json": json.dumps(["A) Ensures mutual exclusion (locks the variable).", "B) Guarantees thread-safety for compound operations like i++.", "C) Ensures visibility of changes to variables across threads.", "D) Makes the variable immutable."]),
        "correct_answer": "C) Ensures visibility of changes to variables across threads."
    },
    {
        "category": "java",
        "type": "coding",
        "question_text": "Write a Java method `public int[] twoSum(int[] nums, int target)` that returns the indices of the two numbers such that they add up to target. Assume exactly one solution exists. O(N) required.",
        "base_code": "class Solution {\n    public int[] twoSum(int[] nums, int target) {\n        // Your code here\n        return new int[]{};\n    }\n}",
        "correct_answer": "class Solution {\n    public int[] twoSum(int[] nums, int target) {\n        java.util.Map<Integer, Integer> map = new java.util.HashMap<>();\n        for (int i = 0; i < nums.length; i++) {\n            int comp = target - nums[i];\n            if (map.containsKey(comp)) return new int[]{map.get(comp), i};\n            map.put(nums[i], i);\n        }\n        return new int[]{};\n    }\n}"
    },
    {
        "category": "java",
        "type": "coding",
        "question_text": "Write a thread-safe Singleton class `LazySingleton` in Java using Double-Checked Locking.",
        "base_code": "public class LazySingleton {\n    // Implement thread-safe singleton\n}",
        "correct_answer": "public class LazySingleton {\n    private static volatile LazySingleton instance;\n    private LazySingleton() {}\n    public static LazySingleton getInstance() {\n        if (instance == null) {\n            synchronized (LazySingleton.class) {\n                if (instance == null) {\n                    instance = new LazySingleton();\n                }\n            }\n        }\n        return instance;\n    }\n}"
    },

    # JAVASCRIPT
    {
        "category": "javascript",
        "type": "mcq",
        "question_text": "In JavaScript, what is the output of `console.log(typeof null)`?",
        "options_json": json.dumps(["A) 'null'", "B) 'undefined'", "C) 'object'", "D) 'number'"]),
        "correct_answer": "C) 'object'"
    },
    {
        "category": "javascript",
        "type": "mcq",
        "question_text": "Which of the following best describes the JavaScript Event Loop?",
        "options_json": json.dumps(["A) A synchronous queue that executes functions in a strictly blocking manner.", "B) A multi-threaded process for parallel DOM rendering.", "C) A monitoring mechanism that pushes tasks from the callback queue to the call stack when the stack is empty.", "D) A server-side mechanism for handling HTTP requests."]),
        "correct_answer": "C) A monitoring mechanism that pushes tasks from the callback queue to the call stack when the stack is empty."
    },
    {
        "category": "javascript",
        "type": "mcq",
        "question_text": "What is 'Hoisting' in JavaScript?",
        "options_json": json.dumps(["A) Variable assignments being moved to the bottom of the execution context.", "B) Declarations of variables and functions being moved to the top of their respective scopes before code execution.", "C) Upgrading an HTTP connection to WebSockets.", "D) Creating a closure."]),
        "correct_answer": "B) Declarations of variables and functions being moved to the top of their respective scopes before code execution."
    },
    {
        "category": "javascript",
        "type": "mcq",
        "question_text": "What is the difference between `==` and `===`?",
        "options_json": json.dumps(["A) `==` checks value only, `===` checks value and type.", "B) `==` checks type only, `===` checks value only.", "C) They are functionally identical.", "D) `===` performs array comparison, `==` performs object comparison."]),
        "correct_answer": "A) `==` checks value only, `===` checks value and type."
    },
    {
        "category": "javascript",
        "type": "mcq",
        "question_text": "Which array method creates a new array with all elements that pass the test implemented by the provided function?",
        "options_json": json.dumps(["A) map()", "B) reduce()", "C) filter()", "D) forEach()"]),
        "correct_answer": "C) filter()"
    },
    {
        "category": "javascript",
        "type": "coding",
        "question_text": "Write a JavaScript function `debounce(fn, ms)` that returns a debounced version of the provided function.",
        "base_code": "function debounce(fn, ms) {\n  // Your code here\n}",
        "correct_answer": "function debounce(fn, ms) {\n  let timeoutId;\n  return function(...args) {\n    clearTimeout(timeoutId);\n    timeoutId = setTimeout(() => fn.apply(this, args), ms);\n  };\n}"
    },
    {
        "category": "javascript",
        "type": "coding",
        "question_text": "Write a deep clone function `deepClone(obj)` for nested object/arrays (without using structuredClone or JSON parse/stringify).",
        "base_code": "function deepClone(obj) {\n  // Your code here\n}",
        "correct_answer": "function deepClone(obj) {\n  if (obj === null || typeof obj !== 'object') return obj;\n  if (Array.isArray(obj)) {\n    const arr = [];\n    for (let item of obj) arr.push(deepClone(item));\n    return arr;\n  }\n  const clone = {};\n  for (let key in obj) {\n    if (obj.hasOwnProperty(key)) clone[key] = deepClone(obj[key]);\n  }\n  return clone;\n}"
    },

    # C++
    {
        "category": "c++",
        "type": "mcq",
        "question_text": "In C++, what is a virtual destructor used for?",
        "options_json": json.dumps(["A) To prevent memory leaks when deleting a derived class object safely through a base class pointer.", "B) To allow derived classes to not implement a destructor.", "C) To automatically initialize virtual methods.", "D) To restrict object creation on the heap only."]),
        "correct_answer": "A) To prevent memory leaks when deleting a derived class object safely through a base class pointer."
    },
    {
        "category": "c++",
        "type": "mcq",
        "question_text": "What does RAII stand for in C++?",
        "options_json": json.dumps(["A) Resource Allocation Is Instant", "B) Resource Acquisition Is Initialization", "C) Runtime Allocation Initial Iterator", "D) Run And Interrupt Instantly"]),
        "correct_answer": "B) Resource Acquisition Is Initialization"
    },
    {
        "category": "c++",
        "type": "mcq",
        "question_text": "What is the difference between `std::unique_ptr` and `std::shared_ptr`?",
        "options_json": json.dumps(["A) unique_ptr uses reference counting, shared_ptr assigns bare pointers.", "B) shared_ptr represents exclusive ownership, unique_ptr represents shared ownership.", "C) unique_ptr represents exclusive ownership, shared_ptr maintains a reference count for shared ownership.", "D) unique_ptr can be copied easily, shared_ptr cannot."]),
        "correct_answer": "C) unique_ptr represents exclusive ownership, shared_ptr maintains a reference count for shared ownership."
    },
    {
        "category": "c++",
        "type": "mcq",
        "question_text": "What keyword prevents a virtual function from being overridden further in derived classes?",
        "options_json": json.dumps(["A) const", "B) final", "C) override", "D) explicit"]),
        "correct_answer": "B) final"
    },
    {
        "category": "c++",
        "type": "mcq",
        "question_text": "Which STL container is implemented as a self-balancing binary search tree (usually a Red-Black tree)?",
        "options_json": json.dumps(["A) std::vector", "B) std::unordered_map", "C) std::set", "D) std::deque"]),
        "correct_answer": "C) std::set"
    },
    {
        "category": "c++",
        "type": "coding",
        "question_text": "Implement a C++ function `ListNode* reverseList(ListNode* head)` to reverse a singly linked list in-place.",
        "base_code": "struct ListNode {\n    int val;\n    ListNode *next;\n    ListNode(int x) : val(x), next(nullptr) {}\n};\n\nListNode* reverseList(ListNode* head) {\n    // Your code here\n    return nullptr;\n}",
        "correct_answer": "ListNode* reverseList(ListNode* head) {\n    ListNode* prev = nullptr;\n    ListNode* current = head;\n    while (current) {\n        ListNode* nextTemp = current->next;\n        current->next = prev;\n        prev = current;\n        current = nextTemp;\n    }\n    return prev;\n}"
    },
    {
        "category": "c++",
        "type": "coding",
        "question_text": "Write a C++ class implementation of a thread-safe atomic counter using `std::mutex`.",
        "base_code": "#include <mutex>\n\nclass AtomicCounter {\npublic:\n    void increment() {\n        // Your code here\n    }\n    int get() {\n        // Your code here\n        return 0;\n    }\n};",
        "correct_answer": "class AtomicCounter {\n    int count = 0;\n    std::mutex mtx;\npublic:\n    void increment() {\n        std::lock_guard<std::mutex> lock(mtx);\n        count++;\n    }\n    int get() {\n        std::lock_guard<std::mutex> lock(mtx);\n        return count;\n    }\n};"
    },
    
    # DSA
    {
        "category": "dsa",
        "type": "mcq",
        "question_text": "What is the worst-case time complexity of QuickSort?",
        "options_json": json.dumps(["A) O(N log N)", "B) O(N^2)", "C) O(N)", "D) O(log N)"]),
        "correct_answer": "B) O(N^2)"
    },
    {
        "category": "dsa",
        "type": "mcq",
        "question_text": "Dijkstra’s algorithm is used to solve which problem?",
        "options_json": json.dumps(["A) Minimum Spanning Tree", "B) Single-Source Shortest Path on graphs with non-negative weights", "C) Travelling Salesperson", "D) Maximum Flow"]),
        "correct_answer": "B) Single-Source Shortest Path on graphs with non-negative weights"
    },
    {
        "category": "dsa",
        "type": "mcq",
        "question_text": "Which data structure is most optimally used for implementing an LRU Cache?",
        "options_json": json.dumps(["A) Array + Priority Queue", "B) Binary Search Tree", "C) Hash Map + Doubly Linked List", "D) Two Stacks"]),
        "correct_answer": "C) Hash Map + Doubly Linked List"
    },
    {
        "category": "dsa",
        "type": "mcq",
        "question_text": "What is the time complexity of searching an element in an unbalanced Binary Search Tree in the worst case?",
        "options_json": json.dumps(["A) O(1)", "B) O(log N)", "C) O(N)", "D) O(N log N)"]),
        "correct_answer": "C) O(N)"
    },
    {
        "category": "dsa",
        "type": "mcq",
        "question_text": "Which algorithm finds the Minimum Spanning Tree using a Greedy approach by selecting the globally shortest edge?",
        "options_json": json.dumps(["A) Bellman-Ford", "B) Kruskal's", "C) Floyd-Warshall", "D) Kahn's"]),
        "correct_answer": "B) Kruskal's"
    },
    {
        "category": "dsa",
        "type": "coding",
        "question_text": "Given a sorted array and a target integer, write a binary search function `binary_search(arr, target)` that returns the index, or -1 if not found.",
        "base_code": "def binary_search(arr, target):\n    # Your code here\n    pass",
        "correct_answer": "def binary_search(arr, target):\n    left, right = 0, len(arr) - 1\n    while left <= right:\n        mid = (left + right) // 2\n        if arr[mid] == target: return mid\n        elif arr[mid] < target: left = mid + 1\n        else: right = mid - 1\n    return -1"
    },
    {
        "category": "dsa",
        "type": "coding",
        "question_text": "Write a recursive function `inorder_traversal(root)` for a binary tree that returns a list of its node values.",
        "base_code": "# class TreeNode: def __init__(self, val=0): self.val = val; self.left = None; self.right = None\n\ndef inorder_traversal(root):\n    # Your code here\n    pass",
        "correct_answer": "def inorder_traversal(root):\n    if not root: return []\n    return inorder_traversal(root.left) + [root.val] + inorder_traversal(root.right)"
    },

    # DevOps
    {
        "category": "devops",
        "type": "mcq",
        "question_text": "In Docker, what is the difference between a CMD and ENTRYPOINT instruction?",
        "options_json": json.dumps(["A) CMD cannot be overridden by docker run arguments, ENTRYPOINT can.", "B) ENTRYPOINT specifies an executable that will always run, while CMD specifies arguments or a default command that is easily overridden.", "C) They are identical aliases.", "D) CMD runs at build time, ENTRYPOINT runs at runtime."]),
        "correct_answer": "B) ENTRYPOINT specifies an executable that will always run, while CMD specifies arguments or a default command that is easily overridden."
    },
    {
        "category": "devops",
        "type": "mcq",
        "question_text": "What is the primary role of an Ingress controller in Kubernetes?",
        "options_json": json.dumps(["A) To schedule pods onto nodes.", "B) To manage internal pod-to-pod east-west traffic.", "C) To manage external access to HTTP/HTTPS services inside the cluster.", "D) To provision persistent volumes dynamically."]),
        "correct_answer": "C) To manage external access to HTTP/HTTPS services inside the cluster."
    },
    {
        "category": "devops",
        "type": "mcq",
        "question_text": "Which of the following CI/CD practices focuses on automatically deploying all code changes directly to the production environment without manual gates?",
        "options_json": json.dumps(["A) Continuous Integration", "B) Continuous Delivery", "C) Continuous Deployment", "D) Agile Sprints"]),
        "correct_answer": "C) Continuous Deployment"
    },
    {
        "category": "devops",
        "type": "mcq",
        "question_text": "What is Terraform primarily used for?",
        "options_json": json.dumps(["A) Application performance monitoring.", "B) Infrastructure as Code (IaC) for provisioning and managing cloud resources.", "C) Container orchestration like Kubernetes.", "D) Managing source code versions."]),
        "correct_answer": "B) Infrastructure as Code (IaC) for provisioning and managing cloud resources."
    },
    {
        "category": "devops",
        "type": "mcq",
        "question_text": "In Linux networking, what command displays the current iptables firewall rules?",
        "options_json": json.dumps(["A) iptables -L", "B) netstat -tulpn", "C) ifconfig", "D) route -n"]),
        "correct_answer": "A) iptables -L"
    },
    {
        "category": "devops",
        "type": "coding",
        "question_text": "Write a multi-stage Dockerfile that compiles a simple Go application `main.go`. Build the app in a 'golang:1.20' image and copy the binary into a minimal 'alpine:latest' image.",
        "base_code": "FROM golang:1.20\n# Your code here",
        "correct_answer": "FROM golang:1.20 as builder\nWORKDIR /app\nCOPY . .\nRUN go build -o myapp main.go\n\nFROM alpine:latest\nWORKDIR /root/\nCOPY --from=builder /app/myapp .\nCMD [\"./myapp\"]"
    },
    {
        "category": "devops",
        "type": "coding",
        "question_text": "Write a basic Kubernetes Deployment YAML specifying 3 replicas for an image `nginx:1.14.2` matching the label `app: web`.",
        "base_code": "apiVersion: apps/v1\n# Your code here",
        "correct_answer": "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: my-nginx\nspec:\n  replicas: 3\n  selector:\n    matchLabels:\n      app: web\n  template:\n    metadata:\n      labels:\n        app: web\n    spec:\n      containers:\n      - name: nginx\n        image: nginx:1.14.2\n        ports:\n        - containerPort: 80"
    }
]

with app.app_context():
    # Clear existing to prevent duplicates if script is run multiple times
    SkillQuestion.query.delete()
    
    for q in questions:
        new_q = SkillQuestion(
            category=q['category'],
            type=q['type'],
            question_text=q['question_text'],
            options_json=q.get('options_json', '[]'),
            correct_answer=q.get('correct_answer'),
            base_code=q.get('base_code')
        )
        db.session.add(new_q)
    
    db.session.commit()
    print(f"✅ Successfully seeded {len(questions)} FAANG-level questions into the Database.")
