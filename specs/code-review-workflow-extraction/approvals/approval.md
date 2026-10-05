# Approval freeze

**Approved-at**: `5d01304`
**Algorithm**: sha256 over UTF-8 bytes

Recorded only after explicit user approval. `spec.md` is hashed without
its volatile Status line. `tech-spec.md` is verified as an immutable
prefix so implementation may append D-### decisions. `task.md` is not
frozen because it is the status holder.

## Frozen contract
- `spec.md`: exact sha256:20d1b504ef04a4158b835a5fbd9dfa5a49b3bd48b51db25e6f3b346106f40550 length:4726
- `plan.md`: exact sha256:d29ba6c0e291f5aa3ec20708df7a169bae61311fad0d492f3e2043cd0b8bb7a3 length:2613
- `survey.md`: exact sha256:fb919920c05208db52af76d191677ec7b3fca1c9e889ccf1c2e46299ecb36f75 length:4450
- `test.md`: exact sha256:71eca33f7d0c348baac004e0e3dcc64db71fbb76cff23f8519b4840fbb1cb152 length:4013
- `tech-spec.md`: prefix sha256:82e591ac495370747984d0bd7d8c15823a6da5e7a283f3d1e7d23f8c952ff564 length:5226

Any other change to these files requires a fresh user approval and a
new freeze record.
