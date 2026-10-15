from src.rerank import rerank_chunks

test_cases = [
    ("What is a put option?", {21, 43}),
    ("What is implied volatility?", {105}),
    ("What is hedging?", {339, 340}),
    ("What is a forward contract?", {19}),
    ("What is intrinsic value?", {49, 50}),
    ("What does option delta measure?", {117, 118}),
    ("What is a straddle?", {187}),
]

hard_test_cases = [
    (
        "Why can a deep in-the-money European call have positive theta, but an American call may not?",
        {126},
    ),
    (
        "Why does a long Christmas tree resemble a short strangle despite containing a purchased option?",
        {199, 202},
    ),
    (
        "Why does a long calendar spread benefit from rising implied volatility but suffer from large underlying price movements?",
        {203, 204, 205},
    ),
    (
        "Why might an American call be exercised before a dividend but not several days earlier?",
        {318, 319, 320},
    ),
    (
        "A put has a 0.40 dividend and earns 0.02 daily interest if exercised. Explain its early-exercise blackout period.",
        {321, 322, 323},
    ),
    (
        "How do stock borrowing costs affect early exercise incentives differently for calls and puts?",
        {41, 323},
    ),
    (
        "Why does early exercise of a futures option depend on its settlement convention?",
        {323, 324},
    ),
    (
        "Explain gamma rent and the tradeoff between dynamic hedging profits and theta losses.",
        {387},
    ),
    (
        "How can calendar spread implied volatilities reveal mispriced expiration months and motivate a time butterfly?",
        {423, 424, 425},
    ),
    (
        "How do you calculate forward volatility between three-month 20 percent and six-month 30 percent implied volatilities?",
        {426},
    ),
]

test_cases.extend(hard_test_cases)

hits_at_1 = 0
hits_at_5 = 0
for question, expected_pages in test_cases:
    results = rerank_chunks(question, limit=5)

    retrieved_pages = [page for _, page, _, _ in results]

    hit_at_1 = bool(retrieved_pages and retrieved_pages[0] in expected_pages)

    hit_at_5 = bool(set(retrieved_pages) & expected_pages)

    hits_at_1 += hit_at_1
    hits_at_5 += hit_at_5

    print(f"\nQuestion: {question}")
    print(f"Retrieved pages: {retrieved_pages}")
    print(f"Hit@1: {hit_at_1}")
    print(f"Hit@5: {hit_at_5}")

total = len(test_cases)

print("\nEVALUATION SUMMARY")
print(f"Hit@1: {hits_at_1 / total:.1%}")
print(f"Hit@5: {hits_at_5 / total:.1%}")
