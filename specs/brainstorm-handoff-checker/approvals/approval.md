# Approval freeze

**Approved-at**: `5b73ac0`
**Algorithm**: sha256 over UTF-8 bytes

Recorded only after explicit user approval. `spec.md` is hashed without
its volatile Status line. `tech-spec.md` is verified as an immutable
prefix so implementation may append D-### decisions. `task.md` is not
frozen because it is the status holder.

## Frozen contract
- `spec.md`: exact sha256:20f977bbe3308c06c57bd3ef17e7b396c00882c1f0ad0cd6695e6a216fb48248 length:5694
- `plan.md`: exact sha256:de8c91092e46f85f109cf45e4b4de6a144a221e0c4d6b4464dbc2389d7975f23 length:2451
- `survey.md`: exact sha256:eab50293808504b44b51a9f821de15c375ddebbbcfbee9565247d5c595db7b10 length:10022
- `test.md`: exact sha256:b1dfa2cd6247fdf497741a7308c527864d528a6f859b60c3c58815014e03ed26 length:21764
- `tech-spec.md`: prefix sha256:16cbf4c037478af3b2498e2fca472c4b5e1b2aac98a54c783d756a626e94daf4 length:11932

Any other change to these files requires a fresh user approval and a
new freeze record.
