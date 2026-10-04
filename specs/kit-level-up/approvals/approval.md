# Approval freeze

**Approved-at**: `3cfc8f1`
**Algorithm**: sha256 over UTF-8 bytes

Recorded only after explicit user approval. `spec.md` is hashed without
its volatile Status line. `tech-spec.md` is verified as an immutable
prefix so implementation may append D-### decisions. `task.md` is not
frozen because it is the status holder.

## Frozen contract
- `spec.md`: exact sha256:5ddd01e8a4296a76e57790da71df7d03babd843dc3934c5315f272cff18b4e28 length:10514
- `plan.md`: exact sha256:35f916fb101481e566ad89c525c084a33bcc283bb75f0a1a16a4034b9199175b length:4658
- `survey.md`: exact sha256:0552f51de0c22cafdf54c90bd56ca72f7fd821277ef1110a883f678ceb360bad length:12892
- `test.md`: exact sha256:0fa87d7a97753dce9d91041e4b79077f9bca11457528e95d328cb37c70842666 length:15802
- `tech-spec.md`: prefix sha256:d2f9fe5f927d78016d4f5287dd990396bf45a721d5bed39443b60cd18c61965d length:19495

Any other change to these files requires a fresh user approval and a
new freeze record.
