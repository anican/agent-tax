
**grep_sed** (`django__django-16595` seq 4, class search/read; callgrind 3,465,455 Ir, perf 26 user-space samples over 3 reps)

| Category (user-space, leaf-only) | callgrind % of Ir | perf % of user samples | Δ (pp) |
|---|---|---|---|
| process lifecycle | 33.2 | 80.8 | +47.5 |
| other user-space | 46.2 | 7.7 | -38.5 |
| allocation | 10.2 | 7.7 | -2.5 |
| memory movement | 2.7 | 3.8 | +1.2 |
| core logic | 6.3 | 0.0 | -6.3 |
| unclassified | 1.3 | 0.0 | -1.3 |

**git_diff_status** (`sympy__sympy-24066` seq 11, class git; callgrind 13,021,922 Ir, perf 41 user-space samples over 3 reps)

| Category (user-space, leaf-only) | callgrind % of Ir | perf % of user samples | Δ (pp) |
|---|---|---|---|
| core logic | 67.9 | 26.8 | -41.1 |
| process lifecycle | 6.0 | 43.9 | +37.9 |
| other user-space | 13.0 | 26.8 | +13.9 |
| allocation | 8.0 | 2.4 | -5.5 |
| memory movement | 2.3 | 0.0 | -2.3 |
| compression | 1.9 | 0.0 | -1.9 |
| unclassified | 1.0 | 0.0 | -1.0 |

**flask_pytest_blueprints** (`pallets__flask-5014` seq 6, class test run; callgrind 2,576,635,958 Ir, perf 2861 user-space samples over 3 reps)

| Category (user-space, leaf-only) | callgrind % of Ir | perf % of user samples | Δ (pp) |
|---|---|---|---|
| other user-space | 72.4 | 1.0 | -71.4 |
| core logic | 0.0 | 59.1 | +59.1 |
| allocation | 15.9 | 30.6 | +14.7 |
| serialization/parsing | 8.1 | 6.0 | -2.1 |
| memory movement | 1.8 | 1.4 | -0.3 |
| hashing/crypto | 1.4 | 0.6 | -0.8 |
| process lifecycle | 0.1 | 0.8 | +0.8 |

**sympy_repro_script** (`sympy__sympy-24066` seq 6, class other; callgrind 1,981,295,823 Ir, perf 2609 user-space samples over 3 reps)

| Category (user-space, leaf-only) | callgrind % of Ir | perf % of user samples | Δ (pp) |
|---|---|---|---|
| other user-space | 76.5 | 0.7 | -75.8 |
| core logic | 0.0 | 61.5 | +61.5 |
| allocation | 15.2 | 31.4 | +16.3 |
| serialization/parsing | 4.9 | 2.7 | -2.1 |
| memory movement | 1.9 | 1.7 | -0.2 |
| hashing/crypto | 1.3 | 0.8 | -0.5 |
| process lifecycle | 0.0 | 0.8 | +0.8 |

**sympy_pytest_quantities** (`sympy__sympy-24066` seq 9, class test run; callgrind 4,263,004,126 Ir, perf 5176 user-space samples over 3 reps)

| Category (user-space, leaf-only) | callgrind % of Ir | perf % of user samples | Δ (pp) |
|---|---|---|---|
| other user-space | 77.9 | 0.7 | -77.2 |
| core logic | 0.0 | 60.2 | +60.2 |
| allocation | 14.8 | 33.8 | +19.0 |
| serialization/parsing | 3.9 | 2.7 | -1.3 |
| memory movement | 1.8 | 1.3 | -0.5 |
| hashing/crypto | 1.3 | 0.7 | -0.6 |

**django_runtests_optimizer** (`django__django-16595` seq 6, class test run; callgrind 1,023,347,371 Ir, perf 1704 user-space samples over 3 reps)

| Category (user-space, leaf-only) | callgrind % of Ir | perf % of user samples | Δ (pp) |
|---|---|---|---|
| other user-space | 66.1 | 0.9 | -65.2 |
| allocation | 19.8 | 38.2 | +18.4 |
| core logic | 0.0 | 52.6 | +52.6 |
| serialization/parsing | 9.1 | 4.0 | -5.1 |
| memory movement | 2.1 | 1.6 | -0.5 |
| hashing/crypto | 2.1 | 0.5 | -1.7 |
| process lifecycle | 0.2 | 1.8 | +1.6 |
