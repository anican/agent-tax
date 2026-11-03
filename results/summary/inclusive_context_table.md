| Class | lifecycle (incl. page faults, ld.so, teardown) | under fs-metadata syscall | under import/startup | under page fault | under python compile | under python teardown |
|---|---|---|---|---|---|---|
| search/read | 80.4 | 5.4 | 0.0 | 17.8 | 0.0 | 0.0 |
| git | 6.7 | 21.1 | 0.0 | 2.9 | 0.0 | 0.0 |
| package install | 4.7 | 1.2 | 4.7 | 2.7 | 8.7 | 1.5 |
| build | 2.2 | 0.1 | 0.4 | 1.9 | 0.1 | 0.0 |
| test run | 7.5 | 1.1 | 15.3 | 1.9 | 2.8 | 4.9 |
| other | 25.1 | 2.1 | 66.9 | 5.2 | 1.5 | 17.0 |
| ALL | 4.4 | 0.9 | 5.0 | 2.3 | 4.7 | 1.6 |
