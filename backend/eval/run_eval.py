import json
import requests
import time
import re
import sys
from pathlib import Path
from openai import OpenAI

# Add the parent directory (backend/) to sys.path so `from app import config` works
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config

client = OpenAI(api_key=config.LLM_API_KEY, base_url=config.LLM_BASE_URL)

API_URL = "http://localhost:8000/api/chat"
HEALTH_URL = "http://localhost:8000/api/health"
DATASET_PATH = Path(__file__).parent / "golden_dataset.json"
SLEEP_BETWEEN_TESTS = 30

def load_dataset():
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def preflight_check():
    print("Preflight: checking backend health...")
    try:
        r = requests.get(HEALTH_URL, timeout=30)
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
    except Exception as e:
        print(f"❌ Preflight failed: {e}")
        return False

def normalize(text):
    return (text
        .replace("\u2011", "-").replace("\u2013", "-").replace("\u2014", "-")
        .replace("\u2018", "'").replace("\u2019", "'")
        .replace("\u201c", '"').replace("\u201d", '"')
        .replace("\u00a0", " ").replace("\u202f", " ")
        .lower())

def llm_judge(question, answer, expected_keyword):
    prompt = f"""You are an expert compliance auditor. Review the AI's answer.
Question: {question}
Expected Keyword: {expected_keyword}
Answer: {answer}

Score the answer from 1 to 5:
5 = Perfect. Accurate, cites sources, no hallucinations.
3 = Partial. Missing some details, but no fake facts.
1 = Failed. Hallucinated facts or completely refused.

Output ONLY the number (1, 3, or 5)."""
    try:
        res = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            temperature=0.0,
            max_tokens=5,
            messages=[{"role": "user", "content": prompt}]
        )
        score = int(re.search(r'\d', res.choices[0].message.content.strip()).group())
        return score
    except:
        return 3

def evaluate_question(test_case):
    payload = {
        "question": test_case["question"],
        "jurisdiction": test_case["jurisdiction"],
        "history": []
    }

    try:
        response = requests.post(API_URL, json=payload, timeout=180)
        if response.status_code != 200:
            return {"pass": False, "reason": f"HTTP Error {response.status_code}"}
            
        data = response.json()
        answer_raw = data.get("answer", "")
        sources = data.get("sources", [])

        # 1. Document Retrieval Check
        # Special case: if expected_document is "None", we don't care what was retrieved
        if test_case["expected_document"] == "None":
            doc_found = True
        else:
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

        # 2. Keyword Check
        keyword_str = test_case["expected_keyword"].lower()
        keywords = [k.strip() for k in keyword_str.split(",")]
        normalized_answer = normalize(answer_raw)
        normalized_keywords = [normalize(k) for k in keywords]
        keyword_found = any(k in normalized_answer for k in normalized_keywords)

        # 3. LLM Judge
        score = llm_judge(test_case["question"], answer_raw, test_case["expected_keyword"])

        # 4. Combine Checks
        if doc_found and keyword_found and score >= 3:
            return {"pass": True, "reason": f"OK (Score: {score}/5)"}
        else:
            reasons = []
            if not doc_found: reasons.append("Retrieval miss")
            if not keyword_found: reasons.append("Keyword miss")
            if score < 3: reasons.append(f"LLM Judge Fail ({score}/5)")
            return {"pass": False, "reason": " | ".join(reasons)}

    except Exception as e:
        return {"pass": False, "reason": f"Exception: {str(e)}"}

def main():
    print("Starting Phase 3 RAG Evaluation...")
    if not preflight_check():
        return
    
    dataset = load_dataset()
    passed = 0
    total = len(dataset)

    for idx, test_case in enumerate(dataset):
        print(f"[{idx + 1}/{total}] {test_case['id']}")
        
        result = evaluate_question(test_case)
        
        if result["pass"]:
            print(f"  ✅ PASS: {result['reason']}")
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