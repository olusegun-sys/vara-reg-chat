import json
import requests
import time
from pathlib import Path

API_URL = "http://localhost:8000/api/chat"
HEALTH_URL = "http://localhost:8000/api/health"
DATASET_PATH = Path(__file__).parent / "golden_dataset.json"
SLEEP_BETWEEN_TESTS = 25


def load_dataset():
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def preflight_check():
    print("Preflight: checking backend health...")
    try:
        r = requests.get(HEALTH_URL, timeout=10)
        if r.status_code != 200:
            print(f"❌ Backend returned HTTP {r.status_code}. Aborting.")
            return False
        data = r.json()
        if not data.get("vector_store_loaded"):
            print(f"❌ Vector store not loaded. Aborting.")
            return False
        print(f"✅ Backend healthy. {data.get('chunk_count', 0)} chunks loaded.\n")
        return True
    except requests.exceptions.ConnectionError:
        print("❌ Cannot reach backend at localhost:8000. Is uvicorn running?")
        return False
    except requests.exceptions.Timeout:
        print("❌ Backend health check timed out after 10s. Aborting.")
        return False
    except Exception as e:
        print(f"❌ Preflight failed: {e}")
        return False


def normalize(text):
    return (text
        .replace("\u2011", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u00a0", " ")
        .replace("\u202f", " ")
        .lower())


def evaluate_question(test_case):
    payload = {
        "question": test_case["question"],
        "jurisdiction": test_case["jurisdiction"],
        "history": []
    }

    try:
        response = requests.post(API_URL, json=payload, timeout=90)
        if response.status_code != 200:
            return {"pass": False, "reason": f"HTTP Error {response.status_code}"}
        data = response.json()
        answer_raw = data.get("answer", "")
        sources = data.get("sources", [])

        doc_found = False
        is_web_result = False
        for s in sources:
            doc_name = s.get("document", "").lower()
            url = s.get("source_url", "").lower()
            if url and "eur-lex" not in url and "vara.ae" not in url and "render" not in url:
                is_web_result = True
            expected_lower = test_case["expected_document"].lower()
            if expected_lower in doc_name or doc_name in expected_lower:
                doc_found = True

        if test_case["expected_document"] == "Web Search Result":
            doc_found = is_web_result

        keyword_str = test_case["expected_keyword"].lower()
        keywords = [k.strip() for k in keyword_str.split(",")]
        normalized_answer = normalize(answer_raw)
        normalized_keywords = [normalize(k) for k in keywords]
        keyword_found = any(k in normalized_answer for k in normalized_keywords)

        if "rate limit" in normalized_answer or "⚠️" in answer_raw:
            return {"pass": False, "reason": "LLM rate-limited"}

        if doc_found and keyword_found:
            return {"pass": True, "reason": "OK"}
        else:
            reasons = []
            if not doc_found:
                got = [s.get('document', '')[:40] for s in sources]
                reasons.append(f"Retrieval miss (expected '{test_case['expected_document']}', got {got})")
            if not keyword_found:
                reasons.append(f"Keyword miss (expected any of '{keyword_str}')")
            return {"pass": False, "reason": " | ".join(reasons)}
    except Exception as e:
        return {"pass": False, "reason": f"Exception: {str(e)}"}


def main():
    print("Starting RAG Evaluation...")
    if not preflight_check():
        return
    print(f"Sleep between tests: {SLEEP_BETWEEN_TESTS}s\n")
    dataset = load_dataset()
    passed = 0
    total = len(dataset)

    for idx, test_case in enumerate(dataset):
        print(f"[{idx + 1}/{total}] {test_case['id']}")
        print(f"  Q: {test_case['question']}")
        result = evaluate_question(test_case)
        if result["pass"]:
            print("  ✅ PASS")
            passed += 1
        else:
            print(f"  ❌ FAIL: {result['reason']}")
        if idx < total - 1:
            print(f"  Sleeping {SLEEP_BETWEEN_TESTS}s...")
            time.sleep(SLEEP_BETWEEN_TESTS)

    print("\n" + "="*50)
    print(f"FINAL SCORE: {passed}/{total} ({(passed/total)*100:.1f}%)")
    print("="*50)


if __name__ == "__main__":
    main()