"""
password_generator.py - Cryptographically secure password generator
and password strength checker.
"""

import secrets
import string
import re


# ------------------------------------------------------------------ #
#  Generator                                                           #
# ------------------------------------------------------------------ #

def generate_password(
    length: int = 16,
    use_upper: bool = True,
    use_lower: bool = True,
    use_digits: bool = True,
    use_symbols: bool = True,
) -> str:
    """
    Generate a cryptographically-secure random password.

    At least one character from each enabled character class is
    guaranteed (avoids passwords that accidentally skip a required
    class due to randomness).
    """
    if not any([use_upper, use_lower, use_digits, use_symbols]):
        raise ValueError("At least one character class must be selected.")

    if length < 4:
        raise ValueError("Password length must be at least 4.")

    charset = ""
    required_chars: list[str] = []

    if use_upper:
        charset += string.ascii_uppercase
        required_chars.append(secrets.choice(string.ascii_uppercase))

    if use_lower:
        charset += string.ascii_lowercase
        required_chars.append(secrets.choice(string.ascii_lowercase))

    if use_digits:
        charset += string.digits
        required_chars.append(secrets.choice(string.digits))

    if use_symbols:
        symbols = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        charset += symbols
        required_chars.append(secrets.choice(symbols))

    # Fill remaining positions
    remaining_len = length - len(required_chars)
    random_chars = [secrets.choice(charset) for _ in range(remaining_len)]

    # Combine and shuffle so required chars aren't always at the front
    all_chars = required_chars + random_chars
    secrets.SystemRandom().shuffle(all_chars)

    return "".join(all_chars)


# ------------------------------------------------------------------ #
#  Strength checker                                                    #
# ------------------------------------------------------------------ #

def check_strength(password: str) -> dict:
    """
    Evaluate password strength.

    Returns a dict:
        score   : 0-100
        label   : "Very Weak" | "Weak" | "Fair" | "Strong" | "Very Strong"
        color   : hex color for the UI bar
        issues  : list of improvement suggestions
    """
    score  = 0
    issues = []

    # --- Length scoring ---
    n = len(password)
    if n >= 20:   score += 30
    elif n >= 16: score += 25
    elif n >= 12: score += 20
    elif n >= 8:  score += 10
    else:
        issues.append("Use at least 8 characters")

    # --- Character class scoring ---
    has_lower   = bool(re.search(r"[a-z]", password))
    has_upper   = bool(re.search(r"[A-Z]", password))
    has_digit   = bool(re.search(r"\d",    password))
    has_symbol  = bool(re.search(r"[^a-zA-Z0-9]", password))

    classes = sum([has_lower, has_upper, has_digit, has_symbol])
    score += classes * 12

    if not has_lower:  issues.append("Add lowercase letters")
    if not has_upper:  issues.append("Add uppercase letters")
    if not has_digit:  issues.append("Add numbers")
    if not has_symbol: issues.append("Add special characters")

    # --- Entropy bonus: unique chars ---
    unique_ratio = len(set(password)) / max(len(password), 1)
    if unique_ratio > 0.8: score += 10
    elif unique_ratio < 0.4: issues.append("Avoid repeated characters")

    # --- Common pattern penalty ---
    common_patterns = [
        r"(.)\1{2,}",           # 3+ repeated chars
        r"(012|123|234|345|456|567|678|789|890)",
        r"(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm)",
        r"(password|passwd|qwerty|admin|login|welcome|letmein)",
    ]
    for pat in common_patterns:
        if re.search(pat, password.lower()):
            score -= 10
            issues.append("Avoid sequential or common patterns")
            break

    score = max(0, min(100, score))

    if score >= 80:
        label, color = "Very Strong", "#22c55e"
    elif score >= 60:
        label, color = "Strong",      "#84cc16"
    elif score >= 40:
        label, color = "Fair",        "#f59e0b"
    elif score >= 20:
        label, color = "Weak",        "#f97316"
    else:
        label, color = "Very Weak",   "#ef4444"

    return {"score": score, "label": label, "color": color, "issues": issues}
