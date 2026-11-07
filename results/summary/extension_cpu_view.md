Episode commands only (setup excluded), mean ± std over 3 replays, pooled over commands (time-weighted). Commands: extension (new model): 16, original (8 episodes): 55.

| Set | core logic | memory movement | allocation | compression | hashing/crypto | serialization/parsing | process lifecycle | interpreter startup/imports | filesystem metadata | scheduling/context switch | virtualization-related | other kernel | other user-space | unclassified |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| extension (new model) | 55.4 ± 0.5 | 1.7 ± 0.2 | 17.9 ± 0.2 | 0.0 ± 0.0 | 0.4 ± 0.1 | 0.5 ± 0.1 | 4.9 ± 0.1 | 13.8 ± 0.2 | 2.8 ± 0.2 | 0.3 ± 0.1 | 0.7 ± 0.0 | 1.1 ± 0.1 | 0.5 ± 0.0 | 0.0 ± 0.0 |
| original (8 episodes) | 56.1 ± 0.5 | 2.0 ± 0.1 | 14.3 ± 0.1 | 0.0 ± 0.0 | 0.3 ± 0.0 | 0.7 ± 0.0 | 2.6 ± 0.0 | 10.6 ± 0.3 | 1.0 ± 0.1 | 8.5 ± 0.2 | 0.2 ± 0.0 | 0.9 ± 0.0 | 2.6 ± 0.0 | 0.1 ± 0.0 |

| Extension task | core logic | memory movement | allocation | compression | hashing/crypto | serialization/parsing | process lifecycle | interpreter startup/imports | filesystem metadata | scheduling/context switch | virtualization-related | other kernel | other user-space | unclassified |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| django__django-16569 | 64.4 ± 0.2 | 1.9 ± 0.2 | 17.4 ± 0.3 | 0.0 ± 0.0 | 0.2 ± 0.1 | 0.5 ± 0.0 | 5.2 ± 0.2 | 6.9 ± 0.2 | 1.0 ± 0.0 | 0.4 ± 0.1 | 0.5 ± 0.0 | 1.1 ± 0.1 | 0.6 ± 0.1 | 0.0 ± 0.0 |
| pytest-dev__pytest-10051 | 49.8 ± 1.0 | 1.4 ± 0.1 | 16.5 ± 0.5 | 0.0 ± 0.0 | 0.4 ± 0.1 | 0.4 ± 0.1 | 3.5 ± 0.4 | 19.1 ± 0.5 | 6.1 ± 0.5 | 0.2 ± 0.1 | 0.8 ± 0.1 | 1.3 ± 0.2 | 0.5 ± 0.1 | 0.0 ± 0.0 |
| sympy__sympy-24539 | 25.9 ± 0.4 | 1.9 ± 0.2 | 25.0 ± 0.8 | 0.0 ± 0.0 | 0.8 ± 0.1 | 0.9 ± 0.1 | 8.3 ± 1.2 | 32.4 ± 1.2 | 1.5 ± 0.4 | 0.2 ± 0.2 | 1.2 ± 0.1 | 1.1 ± 0.1 | 0.6 ± 0.2 | 0.0 ± 0.0 |

| Extension class | core logic | memory movement | allocation | compression | hashing/crypto | serialization/parsing | process lifecycle | interpreter startup/imports | filesystem metadata | scheduling/context switch | virtualization-related | other kernel | other user-space | unclassified |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| other | 1.6 ± 0.8 | 2.8 ± 0.7 | 26.6 ± 0.6 | 0.0 ± 0.0 | 1.0 ± 0.9 | 0.1 ± 0.2 | 11.2 ± 2.4 | 51.2 ± 2.5 | 1.5 ± 0.3 | 0.2 ± 0.4 | 1.9 ± 0.5 | 1.2 ± 0.8 | 0.7 ± 0.4 | 0.0 ± 0.0 |
| search/read | 2.3 ± 0.6 | 1.8 ± 0.4 | 6.4 ± 0.3 | 0.0 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 | 34.5 ± 1.0 | 0.0 ± 0.0 | 3.0 ± 0.2 | 0.4 ± 0.3 | 38.1 ± 1.1 | 5.3 ± 0.4 | 8.2 ± 0.4 | 0.1 ± 0.0 |
| test run | 57.1 ± 0.4 | 1.7 ± 0.1 | 17.7 ± 0.2 | 0.0 ± 0.0 | 0.3 ± 0.0 | 0.5 ± 0.1 | 4.6 ± 0.1 | 12.8 ± 0.0 | 2.9 ± 0.2 | 0.3 ± 0.1 | 0.5 ± 0.0 | 1.1 ± 0.2 | 0.5 ± 0.0 | 0.0 ± 0.0 |
