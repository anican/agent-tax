
**grep_sed** (`django__django-16595` seq 4, class search/read; callgrind 3,465,455 Ir, perf 480 user-space samples over 3 reps + looped profiles if any)

| Category (user-space, leaf-only) | callgrind % of Ir | perf % of user samples | Δ (pp) |
|---|---|---|---|
| process lifecycle | 33.2 | 73.5 | +40.3 |
| other user-space | 43.8 | 17.3 | -26.5 |
| allocation | 10.2 | 3.8 | -6.5 |
| core logic | 8.8 | 3.3 | -5.4 |
| memory movement | 2.7 | 1.7 | -1.0 |
| unclassified | 1.3 | 0.4 | -0.9 |

**git_diff_status** (`sympy__sympy-24066` seq 11, class git; callgrind 13,021,922 Ir, perf 981 user-space samples over 3 reps + looped profiles if any)

| Category (user-space, leaf-only) | callgrind % of Ir | perf % of user samples | Δ (pp) |
|---|---|---|---|
| core logic | 75.2 | 27.8 | -47.3 |
| process lifecycle | 6.0 | 36.3 | +30.3 |
| other user-space | 5.7 | 26.5 | +20.8 |
| allocation | 8.0 | 6.8 | -1.1 |
| memory movement | 2.3 | 1.5 | -0.7 |
| compression | 1.9 | 0.8 | -1.1 |
| unclassified | 1.0 | 0.2 | -0.8 |

**flask_pytest_blueprints** (`pallets__flask-5014` seq 6, class test run; callgrind 2,576,635,958 Ir, perf 2861 user-space samples over 3 reps + looped profiles if any)

| Category (user-space, leaf-only) | callgrind % of Ir | perf % of user samples | Δ (pp) |
|---|---|---|---|
| core logic | 70.3 | 59.1 | -11.2 |
| allocation | 15.9 | 30.6 | +14.7 |
| serialization/parsing | 10.0 | 6.0 | -4.0 |
| memory movement | 1.8 | 1.4 | -0.3 |
| hashing/crypto | 1.4 | 0.6 | -0.8 |
| other user-space | 0.1 | 1.0 | +0.9 |
| process lifecycle | 0.1 | 0.8 | +0.8 |

**sympy_repro_script** (`sympy__sympy-24066` seq 6, class other; callgrind 1,981,295,823 Ir, perf 2609 user-space samples over 3 reps + looped profiles if any)

| Category (user-space, leaf-only) | callgrind % of Ir | perf % of user samples | Δ (pp) |
|---|---|---|---|
| core logic | 76.3 | 61.5 | -14.8 |
| allocation | 15.2 | 31.4 | +16.3 |
| serialization/parsing | 5.0 | 2.7 | -2.3 |
| memory movement | 1.9 | 1.7 | -0.2 |
| hashing/crypto | 1.3 | 0.8 | -0.5 |
| process lifecycle | 0.0 | 0.8 | +0.8 |
| other user-space | 0.1 | 0.7 | +0.6 |

**sympy_pytest_quantities** (`sympy__sympy-24066` seq 9, class test run; callgrind 4,263,004,126 Ir, perf 5176 user-space samples over 3 reps + looped profiles if any)

| Category (user-space, leaf-only) | callgrind % of Ir | perf % of user samples | Δ (pp) |
|---|---|---|---|
| core logic | 77.4 | 60.2 | -17.2 |
| allocation | 14.8 | 33.8 | +19.0 |
| serialization/parsing | 4.3 | 2.7 | -1.6 |
| memory movement | 1.8 | 1.3 | -0.5 |
| hashing/crypto | 1.3 | 0.7 | -0.6 |
| other user-space | 0.1 | 0.7 | +0.6 |

**django_runtests_optimizer** (`django__django-16595` seq 6, class test run; callgrind 1,023,347,371 Ir, perf 1704 user-space samples over 3 reps + looped profiles if any)

| Category (user-space, leaf-only) | callgrind % of Ir | perf % of user samples | Δ (pp) |
|---|---|---|---|
| core logic | 64.6 | 52.6 | -12.0 |
| allocation | 19.8 | 38.2 | +18.4 |
| serialization/parsing | 10.3 | 4.0 | -6.4 |
| memory movement | 2.1 | 1.6 | -0.5 |
| hashing/crypto | 2.1 | 0.5 | -1.7 |
| process lifecycle | 0.2 | 1.8 | +1.6 |
| other user-space | 0.3 | 0.9 | +0.5 |

**sklearn_pytest_ranking** (`scikit-learn__scikit-learn-26194` seq 8, class test run; callgrind 8,183,188,574 Ir, perf 13565 user-space samples over 3 reps + looped profiles if any)

| Category (user-space, leaf-only) | callgrind % of Ir | perf % of user samples | Δ (pp) |
|---|---|---|---|
| core logic | 78.1 | 65.7 | -12.4 |
| allocation | 14.4 | 22.0 | +7.7 |
| scheduling/context switch | 0.5 | 7.1 | +6.6 |
| serialization/parsing | 3.7 | 1.5 | -2.2 |
| memory movement | 1.6 | 1.2 | -0.5 |
| process lifecycle | 0.7 | 1.0 | +0.3 |
| other user-space | 0.2 | 0.9 | +0.7 |
| hashing/crypto | 0.7 | 0.4 | -0.4 |
