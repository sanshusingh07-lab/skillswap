# Matching algorithm

`services/matching.py` compares two students using sets of skill names.

- Desired match: current student wants a skill the candidate teaches: +30.
- Reciprocal match: candidate wants a skill the current student teaches: +20.
- Mutual exchange: both directions exist: +50.
- Score is capped at 100.

Labels are Strong Match for 80-100, Good Match for 60-79, Potential Match for 40-59, and Low Match below 40. The service also returns plain-language reasons so the partner profile can explain the result instead of presenting a mysterious percentage.
