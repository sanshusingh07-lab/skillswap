from typing import Iterable


def calculate_match(user_teach: Iterable[str], user_learn: Iterable[str], candidate_teach: Iterable[str], candidate_learn: Iterable[str]) -> dict:
    user_teach_set = {skill.lower() for skill in user_teach}
    user_learn_set = {skill.lower() for skill in user_learn}
    candidate_teach_set = {skill.lower() for skill in candidate_teach}
    candidate_learn_set = {skill.lower() for skill in candidate_learn}

    desired_match = user_learn_set & candidate_teach_set
    reciprocal_match = candidate_learn_set & user_teach_set
    score = 0
    if desired_match and reciprocal_match:
        score += 50
    if desired_match:
        score += 30
    if reciprocal_match:
        score += 20
    score = min(score, 100)
    label = 'Strong Match' if score >= 80 else 'Good Match' if score >= 60 else 'Potential Match' if score >= 40 else 'Low Match'
    reasons = []
    for skill in sorted(desired_match):
        reasons.append(f'You want to learn {skill.title()} and this student teaches it.')
    for skill in sorted(reciprocal_match):
        reasons.append(f'This student wants to learn {skill.title()} and you can teach it.')
    return {'score': score, 'label': label, 'desired_match': desired_match, 'reciprocal_match': reciprocal_match, 'reasons': reasons}
