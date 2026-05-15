import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app.app as api
from utils.schema_extractor import extract_schema_from_db


class SchemaAwareGenerationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "employee_test.db"
        self._create_test_db(self.db_path)
        self.client = api.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _create_test_db(self, db_path):
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.executescript(
            """
            CREATE TABLE departments (
                department_id INTEGER PRIMARY KEY,
                department_name TEXT NOT NULL,
                location TEXT NOT NULL
            );

            CREATE TABLE jobs (
                job_id INTEGER PRIMARY KEY,
                job_title TEXT NOT NULL
            );

            CREATE TABLE employees (
                employee_id INTEGER PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                department_id INTEGER NOT NULL,
                job_id INTEGER NOT NULL,
                employment_status TEXT NOT NULL,
                FOREIGN KEY (department_id) REFERENCES departments(department_id),
                FOREIGN KEY (job_id) REFERENCES jobs(job_id)
            );

            CREATE TABLE salaries (
                salary_id INTEGER PRIMARY KEY,
                employee_id INTEGER NOT NULL,
                base_salary REAL NOT NULL,
                bonus REAL NOT NULL,
                FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
            );
            """
        )
        cur.executemany(
            "INSERT INTO departments VALUES (?,?,?)",
            [
                (1, "Engineering", "Austin"),
                (2, "Sales", "New York"),
            ],
        )
        cur.executemany(
            "INSERT INTO jobs VALUES (?,?)",
            [
                (1, "Software Engineer"),
                (2, "Account Executive"),
            ],
        )
        cur.executemany(
            "INSERT INTO employees VALUES (?,?,?,?,?,?)",
            [
                (1, "Asha", "Rao", 1, 1, "Active"),
                (2, "Mira", "Shah", 1, 1, "On Leave"),
                (3, "Noah", "Kim", 2, 2, "Active"),
            ],
        )
        cur.executemany(
            "INSERT INTO salaries VALUES (?,?,?,?)",
            [
                (1, 1, 120000, 5000),
                (2, 2, 99000, 3000),
                (3, 3, 87000, 8000),
            ],
        )
        conn.commit()
        conn.close()

    def _create_library_db(self, db_path):
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.executescript(
            """
            CREATE TABLE authors (
                author_id INTEGER PRIMARY KEY,
                author_name TEXT NOT NULL,
                country TEXT NOT NULL
            );

            CREATE TABLE books (
                book_id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                author_id INTEGER NOT NULL,
                published_date TEXT NOT NULL,
                genre TEXT NOT NULL,
                pages INTEGER NOT NULL,
                FOREIGN KEY (author_id) REFERENCES authors(author_id)
            );
            """
        )
        cur.executemany(
            "INSERT INTO authors VALUES (?,?,?)",
            [
                (1, "Ada Writer", "USA"),
                (2, "Bert Novelist", "UK"),
            ],
        )
        cur.executemany(
            "INSERT INTO books VALUES (?,?,?,?,?,?)",
            [
                (1, "Future Systems", 1, "2022-05-10", "Technology", 310),
                (2, "Old Tales", 1, "2018-04-01", "Fantasy", 250),
                (3, "Data Stories", 2, "2021-07-20", "Technology", 190),
            ],
        )
        conn.commit()
        conn.close()

    def _post_db(self, endpoint, question):
        with self.db_path.open("rb") as db_file:
            return self.client.post(
                endpoint,
                data={
                    "question": question,
                    "model": "test-model",
                    "row_limit": "10",
                    "dialect": "SQLite",
                    "db_file": (db_file, self.db_path.name),
                },
                content_type="multipart/form-data",
            )

    def test_prompt_does_not_include_generic_hardcoded_examples(self):
        schema = extract_schema_from_db(self.db_path)
        prompt = api.format_prompt_with_schema("Show employees in engineering", schema, dialect="SQLite")

        self.assertNotIn("List the names of students", prompt)
        self.assertNotIn("SELECT * FROM employees WHERE department = 'Sales'", prompt)
        self.assertIn("department_name", prompt)
        self.assertIn("Engineering", prompt)

    def test_live_query_repairs_generic_department_column(self):
        responses = [
            {"response": "SELECT * FROM employees WHERE department = 'Engineering';"},
            {
                "response": (
                    "SELECT e.employee_id, e.first_name, e.last_name, d.department_name "
                    "FROM employees e "
                    "JOIN departments d ON e.department_id = d.department_id "
                    "WHERE LOWER(d.department_name) = LOWER('Engineering');"
                )
            },
        ]

        with patch("app.app.ollama.generate", side_effect=responses):
            response = self._post_db("/query", "Show all employees in engineering")

        body = response.get_json()
        self.assertEqual(response.status_code, 200, body)
        self.assertEqual(body["execution"]["row_count"], 2)
        self.assertGreaterEqual(len(body["repair_attempts"]), 1)
        self.assertIn("departments", body["sql"])

    def test_translation_with_uploaded_db_validates_and_repairs_sql(self):
        responses = [
            {"response": "SELECT first_name, last_name, salary FROM employees;"},
            {
                "response": (
                    "SELECT e.first_name, e.last_name, s.base_salary "
                    "FROM employees e "
                    "JOIN salaries s ON e.employee_id = s.employee_id;"
                )
            },
        ]

        with patch("app.app.ollama.generate", side_effect=responses):
            response = self._post_db("/translate", "Show employee salaries")

        body = response.get_json()
        self.assertEqual(response.status_code, 200, body)
        self.assertTrue(body["validated"])
        self.assertGreaterEqual(len(body["repair_attempts"]), 1)
        self.assertIn("salaries", body["sql"])
        self.assertNotIn(" salary FROM employees", body["sql"])

    def test_live_query_repairs_generic_status_request(self):
        responses = [
            {"response": "SELECT * FROM employee WHERE status = 'Active';"},
            {
                "response": (
                    "SELECT * FROM employees "
                    "WHERE LOWER(employment_status) = LOWER('Active');"
                )
            },
        ]

        with patch("app.app.ollama.generate", side_effect=responses):
            response = self._post_db("/query", "List active employees")

        body = response.get_json()
        self.assertEqual(response.status_code, 200, body)
        self.assertEqual(body["execution"]["row_count"], 2)
        self.assertIn("employment_status", body["sql"])

    def test_live_query_uses_schema_fallback_for_missing_job_title_join(self):
        responses = [
            {
                "response": (
                    "SELECT e.employee_id, e.first_name, e.last_name, job_title "
                    "FROM employees e "
                    "JOIN departments d ON e.department_id = d.department_id "
                    "WHERE LOWER(d.department_name) = LOWER('Engineering');"
                )
            }
        ]

        with patch("app.app.ollama.generate", side_effect=responses):
            response = self._post_db("/query", "Show all employees in engineering")

        body = response.get_json()
        self.assertEqual(response.status_code, 200, body)
        self.assertEqual(body["execution"]["row_count"], 2)
        self.assertIn("departments", body["sql"])
        self.assertNotIn(" job_title ", body["sql"])
        self.assertTrue(any(attempt.get("repair") == "generic schema-driven query plan" for attempt in body["repair_attempts"]))

    def test_employee_system_database_question_executes_without_model_repair(self):
        real_db_path = Path(__file__).resolve().parents[1] / "employee system.db"
        responses = [
            {
                "response": (
                    "SELECT e.first_name, e.last_name, job_title "
                    "FROM employees e "
                    "JOIN departments d ON e.department_id = d.department_id "
                    "WHERE LOWER(d.department_name) = LOWER('Engineering');"
                )
            }
        ]

        with real_db_path.open("rb") as db_file:
            with patch("app.app.ollama.generate", side_effect=responses):
                response = self.client.post(
                    "/query",
                    data={
                        "question": "show all employees in engineering",
                        "model": "test-model",
                        "row_limit": "100",
                        "dialect": "SQLite",
                        "db_file": (db_file, real_db_path.name),
                    },
                    content_type="multipart/form-data",
                )

        body = response.get_json()
        self.assertEqual(response.status_code, 200, body)
        self.assertGreater(body["execution"]["row_count"], 0)
        self.assertIn("departments", body["sql"])

    def test_employee_system_hired_after_year_uses_hire_date_filter(self):
        real_db_path = Path(__file__).resolve().parents[1] / "employee system.db"
        responses = [
            {"response": "SELECT e.* FROM employees e;"}
        ]

        with real_db_path.open("rb") as db_file:
            with patch("app.app.ollama.generate", side_effect=responses):
                response = self.client.post(
                    "/query",
                    data={
                        "question": "Show all employees hired after 2020",
                        "model": "test-model",
                        "row_limit": "100",
                        "dialect": "SQLite",
                        "db_file": (db_file, real_db_path.name),
                    },
                    content_type="multipart/form-data",
                )

        body = response.get_json()
        self.assertEqual(response.status_code, 200, body)
        self.assertIn('"hire_date" > \'2020-12-31\'', body["sql"])
        self.assertGreater(body["execution"]["row_count"], 0)
        self.assertTrue(
            all(row["hire_date"] > "2020-12-31" for row in body["execution"]["rows"]),
            body["execution"]["rows"],
        )

    def test_department_with_most_employees_returns_department_aggregate(self):
        real_db_path = Path(__file__).resolve().parents[1] / "employee system.db"
        responses = [
            {
                "response": (
                    "SELECT e.*, d.department_name FROM employees e "
                    "JOIN departments d ON e.department_id = d.department_id;"
                )
            }
        ]

        with real_db_path.open("rb") as db_file:
            with patch("app.app.ollama.generate", side_effect=responses):
                response = self.client.post(
                    "/query",
                    data={
                        "question": "Which department has the most employees?",
                        "model": "test-model",
                        "row_limit": "100",
                        "dialect": "SQLite",
                        "db_file": (db_file, real_db_path.name),
                    },
                    content_type="multipart/form-data",
                )

        body = response.get_json()
        self.assertEqual(response.status_code, 200, body)
        self.assertIn("COUNT", body["sql"])
        self.assertIn("departments", body["sql"])
        self.assertEqual(body["execution"]["row_count"], 1)
        self.assertIn("department_name", body["execution"]["columns"])
        self.assertIn("employee_count", body["execution"]["columns"])
        self.assertNotIn("email", body["execution"]["columns"])

    def test_department_details_returns_department_table(self):
        real_db_path = Path(__file__).resolve().parents[1] / "employee system.db"
        responses = [{"response": "SELECT * FROM employees;"}]

        with real_db_path.open("rb") as db_file:
            with patch("app.app.ollama.generate", side_effect=responses):
                response = self.client.post(
                    "/query",
                    data={
                        "question": "Show department table details",
                        "model": "test-model",
                        "row_limit": "100",
                        "dialect": "SQLite",
                        "db_file": (db_file, real_db_path.name),
                    },
                    content_type="multipart/form-data",
                )

        body = response.get_json()
        self.assertEqual(response.status_code, 200, body)
        self.assertEqual(body["sql"], 'SELECT * FROM "departments";')
        self.assertEqual(body["execution"]["row_count"], 5)
        self.assertIn("department_name", body["execution"]["columns"])
        self.assertNotIn("email", body["execution"]["columns"])

    def test_generic_schema_planner_handles_non_employee_library_db(self):
        library_path = Path(self.temp_dir.name) / "library.db"
        self._create_library_db(library_path)
        responses = [{"response": "SELECT * FROM books;"}]

        with library_path.open("rb") as db_file:
            with patch("app.app.ollama.generate", side_effect=responses):
                response = self.client.post(
                    "/query",
                    data={
                        "question": "Show books published after 2020",
                        "model": "test-model",
                        "row_limit": "100",
                        "dialect": "SQLite",
                        "db_file": (db_file, library_path.name),
                    },
                    content_type="multipart/form-data",
                )

        body = response.get_json()
        self.assertEqual(response.status_code, 200, body)
        self.assertIn('"published_date" > \'2020-12-31\'', body["sql"])
        self.assertEqual(body["execution"]["row_count"], 2)
        self.assertTrue(all(row["published_date"] > "2020-12-31" for row in body["execution"]["rows"]))

    def test_generic_schema_planner_counts_related_non_employee_tables(self):
        library_path = Path(self.temp_dir.name) / "library.db"
        self._create_library_db(library_path)
        responses = [{"response": "SELECT * FROM books;"}]

        with library_path.open("rb") as db_file:
            with patch("app.app.ollama.generate", side_effect=responses):
                response = self.client.post(
                    "/query",
                    data={
                        "question": "Which author has the most books?",
                        "model": "test-model",
                        "row_limit": "100",
                        "dialect": "SQLite",
                        "db_file": (db_file, library_path.name),
                    },
                    content_type="multipart/form-data",
                )

        body = response.get_json()
        self.assertEqual(response.status_code, 200, body)
        self.assertIn("COUNT", body["sql"])
        self.assertIn("authors", body["sql"])
        self.assertEqual(body["execution"]["row_count"], 1)
        self.assertIn("book_count", body["execution"]["columns"])


if __name__ == "__main__":
    unittest.main()
