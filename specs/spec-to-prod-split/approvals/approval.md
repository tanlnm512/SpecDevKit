# Approval freeze

**Approved-at**: `3640b09`
**Algorithm**: sha256 over UTF-8 bytes

Recorded only after explicit user approval. `spec.md` is hashed without
its volatile Status line. `tech-spec.md` is verified as an immutable
prefix so implementation may append D-### decisions. `task.md` is not
frozen because it is the status holder.

## Frozen contract
- `spec.md`: exact sha256:0f5e8e28adc549dc0f6f0c66c9b0cfb5313ab1d9bc9ac16954bb213855b7cdf0 length:8042
- `plan.md`: exact sha256:1e9b4bd2462498a813efc786633266f8ba020b6e7ff8a80d8746c79cb68225f5 length:11888
- `survey.md`: exact sha256:08031e44ef8e5c8bfc47e82242a004c66591e6c8b3584f76492863dd68c545b5 length:17565
- `test.md`: exact sha256:3176b9b8ed1cf0535cb6d64c677df561d6c657a01153017a801b216483342796 length:11977
- `tech-spec.md`: prefix sha256:0bbe95b955ed9223d8a19566281c28055338f357892a8b2af67e28e9bd4f87e3 length:32639

Any other change to these files requires a fresh user approval and a
new freeze record.
