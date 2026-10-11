# D-006: Parallel waves are the default at every size

Stage waves and implementer waves spawn in one message by default.
Serial/inline is the exception needing justification: a single file with
zero unknowns, or an explicit user "go cheap". Depth shrinks with scope;
the wave shape holds.

**Why**: correctness and wall-clock beat token spend (multi-agent ≈15× a
solo pass — accepted). Parallelism is what the file-ownership contract
makes safe: disjoint intended file sets, verified before each wave; any
overlap chains those tasks serially.

**Cost if wrong**: concurrent implementers sharing files clobber each
other — mitigated by the planner's parallelization map and the
pre-wave disjointness check.
