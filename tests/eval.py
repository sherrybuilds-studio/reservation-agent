"""
Retrieval eval: gold questions against the ChromaDB index built from data/menu.json.
Tests retrieval quality directly (no LLM, Supabase or WhatsApp needed).
Run from the repo root, after python -m rag.indexer: python -m tests.eval
"""
import sys

from rag.retriever import retrieve

# Share of gold questions that must pass; below it the eval exits 1 (CI fails).
THRESHOLD_PCT = 100

TESTS = [
    {
        "id": 1,
        "name": "Menu item — Adana Kebab",
        "query": "What is the Adana Kebab?",
        "must_contain": ["adana", "lamb", "charcoal"],
        "must_not_contain": [],
        "category": None
    },
    {
        "id": 2,
        "name": "Allergen inquiry — gluten",
        "query": "Which dishes are gluten free?",
        "must_contain": ["gluten"],
        "must_not_contain": [],
        "category": None
    },
    {
        "id": 3,
        "name": "Opening hours",
        "query": "What time do you open on Friday?",
        "must_contain": ["friday", "12:00"],
        "must_not_contain": [],
        "category": None
    },
    {
        "id": 4,
        "name": "Reservation policy — groups",
        "query": "Do I need to make a reservation?",
        "must_contain": ["reservation"],
        "must_not_contain": [],
        "category": None
    },
    {
        "id": 5,
        "name": "Fully booked scenario — waitlist mention",
        "query": "What happens if the restaurant is fully booked?",
        "must_contain": ["waitlist", "notif"],
        "must_not_contain": [],
        "category": None
    },
    {
        "id": 6,
        "name": "German language query — vegetarian",
        "query": "Haben Sie vegetarische Gerichte?",
        "must_contain": ["vegetar"],
        "must_not_contain": [],
        "category": None
    },
    {
        "id": 7,
        "name": "Upsell opportunity — special",
        "query": "Is there anything special on Friday?",
        "must_contain": ["friday", "special"],
        "must_not_contain": [],
        "category": None
    },
    {
        "id": 8,
        "name": "Vegan options",
        "query": "What vegan food do you have?",
        "must_contain": ["vegan"],
        "must_not_contain": [],
        "category": None
    },
    {
        "id": 9,
        "name": "Price inquiry — Baklava",
        "query": "How much does the Baklava cost?",
        "must_contain": ["baklava", "9.50"],
        "must_not_contain": [],
        "category": None
    },
    {
        "id": 10,
        "name": "Location and transport",
        "query": "Where are you located and how do I get there?",
        "must_contain": ["musterstra", "10115"],
        "must_not_contain": [],
        "category": None
    }
]


def run_test(test):
    results = retrieve(test["query"], n_results=3, category_filter=test.get("category"))

    if not results:
        return False, "No results returned", 0.0

    # Combine all retrieved text for checking
    combined_text = " ".join(r["text"] for r in results).lower()
    top_score = results[0]["score"] if results else 0.0

    failures = []
    for keyword in test["must_contain"]:
        if keyword.lower() not in combined_text:
            failures.append(f"missing '{keyword}'")

    for keyword in test["must_not_contain"]:
        if keyword.lower() in combined_text:
            failures.append(f"should not contain '{keyword}'")

    if failures:
        return False, ", ".join(failures), top_score

    return True, "PASS", top_score


def main():
    print("=" * 60)
    print("RETRIEVAL EVAL — gold questions")
    print("=" * 60)
    print()

    passed = 0
    failed = 0
    scores = []

    for test in TESTS:
        ok, reason, score = run_test(test)
        scores.append(score)
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"[{test['id']:02d}] {status} | {test['name']}")
        if not ok:
            print(f"       → {reason}")
        print(f"       → top score: {score:.4f}")

        if ok:
            passed += 1
        else:
            failed += 1

    avg_score = sum(scores) / len(scores) if scores else 0
    score_pct = passed / len(TESTS) * 100

    print()
    print("=" * 60)
    print(f"RESULTS: {passed}/{len(TESTS)} passed")
    print(f"SCORE:   {score_pct:.0f}% (threshold {THRESHOLD_PCT}%)")
    print(f"AVG RETRIEVAL SCORE: {avg_score:.4f}")
    print("=" * 60)

    if score_pct < THRESHOLD_PCT:
        print(f"\n⚠️  {failed} test(s) failed, below the {THRESHOLD_PCT}% threshold. Check the index and retriever.")
        sys.exit(1)
    print("\n🎉 All tests passed!")
    sys.exit(0)


if __name__ == "__main__":
    main()
