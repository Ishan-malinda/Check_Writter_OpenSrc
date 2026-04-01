"""Convert numeric amount to English words for Sri Lankan cheques."""

ONES = [
    "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
    "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
    "Seventeen", "Eighteen", "Nineteen",
]
TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _below_thousand(n: int) -> str:
    if n == 0:
        return ""
    elif n < 20:
        return ONES[n]
    elif n < 100:
        rest = ONES[n % 10]
        return TENS[n // 10] + (" " + rest if rest else "")
    else:
        rest = _below_thousand(n % 100)
        return ONES[n // 100] + " Hundred" + (" and " + rest if rest else "")


def _to_words(n: int) -> str:
    if n == 0:
        return "Zero"
    parts = []
    if n >= 1_000_000_000:
        parts.append(_below_thousand(n // 1_000_000_000) + " Billion")
        n %= 1_000_000_000
    if n >= 1_000_000:
        parts.append(_below_thousand(n // 1_000_000) + " Million")
        n %= 1_000_000
    if n >= 1_000:
        parts.append(_below_thousand(n // 1_000) + " Thousand")
        n %= 1_000
    if n > 0:
        parts.append(_below_thousand(n))
    return " ".join(parts)


def amount_to_words(amount: float) -> str:
    """Return cheque-style words for a rupee amount, e.g. 'Rupees One Thousand Five Hundred and 50/100 Only'."""
    amount = round(amount, 2)
    rupees = int(amount)
    cents = round((amount - rupees) * 100)

    words = _to_words(rupees)
    if cents > 0:
        words += f" and {cents:02d}/100"
    words += " Only"
    return words


if __name__ == "__main__":
    tests = [0, 1, 100, 1500.50, 25000, 1234567.75]
    for t in tests:
        print(f"{t:>12.2f}  ->  {amount_to_words(t)}")
