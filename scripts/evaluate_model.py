"""Basic evaluation for generated NL2SQL output."""

import json
import re
from pathlib import Path

import ollama
from tqdm import tqdm


MODEL_NAME = "gemma3:1b"
RESULT_FILE = Path("evaluation_results.json")


SAMPLE_TEST_DATA = [
    {
        "question": "Show all employees with salary above 50000",
        "sql": "SELECT * FROM employee WHERE salary > 50000;",
    },
    {
        "question": "List all departments",
        "sql": "SELECT * FROM department;",
    },
    {
        "question": "Find the average salary of all employees",
        "sql": "SELECT AVG(salary) FROM employee;",
    },
]


def normalize_sql(sql: str) -> str:
    return re.sub(r"\s+", " ", sql.strip().lower())


def exact_match(predicted: str, expected: str) -> bool:
    return normalize_sql(predicted) == normalize_sql(expected)


def token_overlap(predicted: str, expected: str) -> float:
    predicted_tokens = re.findall(r"\w+|[^\w\s]", predicted.lower())
    expected_tokens = re.findall(r"\w+|[^\w\s]", expected.lower())
    if not expected_tokens:
        return 0.0
    matches = sum(1 for token in predicted_tokens if token in expected_tokens)
    return matches / len(expected_tokens)


def clean_sql(text: str) -> str:
    sql = text.strip()
    if "```sql" in sql:
        sql = sql.split("```sql", 1)[1].split("```", 1)[0].strip()
    elif sql.startswith("```"):
        sql = sql.strip("`").strip()

    sql = " ".join(line.strip() for line in sql.splitlines() if line.strip())
    if sql and not sql.endswith(";"):
        sql += ";"
    return sql


def generate_sql(question: str) -> str:
    prompt = f"""Convert the following natural language question into SQL.
Return only the SQL query.

Question: {question}
SQL:"""

    response = ollama.generate(
        model=MODEL_NAME,
        prompt=prompt,
        options={"temperature": 0.2, "top_p": 0.9},
    )
    return clean_sql(response["response"])


def load_test_data() -> list[dict]:
    for path in [Path("data/spider_test.json"), Path("data/wikisql_test.json")]:
        if path.exists():
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
            print(f"Loaded {len(data)} examples from {path}")
            return data

    print("No processed test dataset found. Using sample test data.")
    return SAMPLE_TEST_DATA


def main() -> None:
    test_data = load_test_data()
    exact_matches = 0
    overlap_total = 0.0

    for index, example in enumerate(tqdm(test_data, desc="Evaluating")):
        predicted = generate_sql(example["question"])
        expected = example["sql"]

        if exact_match(predicted, expected):
            exact_matches += 1
        overlap_total += token_overlap(predicted, expected)

        if index < 3:
            print()
            print(f"Question: {example['question']}")
            print(f"Expected: {expected}")
            print(f"Predicted: {predicted}")

    total = len(test_data)
    results = {
        "total_examples": total,
        "exact_match_accuracy": exact_matches / total if total else 0,
        "exact_matches": exact_matches,
        "average_token_overlap": overlap_total / total if total else 0,
    }

    RESULT_FILE.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print()
    print(json.dumps(results, indent=2))
    print(f"Saved results to {RESULT_FILE}")


if __name__ == "__main__":
    main()
