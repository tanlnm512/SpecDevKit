# Approval freeze

**Approved-at**: `98fa893`
**Algorithm**: sha256 over UTF-8 bytes

Recorded only after explicit user approval. `spec.md` is hashed without
its volatile Status line (at tiny tier also without § Evidence and the
status markers inside § Tasks; the task list itself is frozen).
`tech-spec.md` is verified as an immutable prefix so implementation
may append D-### decisions. `task.md` is not frozen because it is the
status holder.

## Contract review

Docset fingerprint: 93ca090ad5f4
digest: BLOCK 0 · WARN 0 · NIT 0 · worst none`

## Freeze

- `spec.md`: exact sha256:f4e3d8d97e5bcb3d2e081845f93a023805a42b55358839f1d3045916592696ed length:7900
- `plan.md`: exact sha256:f883ea131335d79075ec825aac170a047b63bf86dbc92f28fca1336ab19edc27 length:12617
- `survey.md`: exact sha256:9decd9da2efe80dcd9bbfa137ff3eb47cbd74ae1cf3a6d35e18d2f5dbf1db670 length:21595
- `test.md`: exact sha256:f46c0b14012cec6fccf10eaa875d2c3c21cd16522ce2854563b29315ffcbdfb5 length:13618
- `tech-spec.md`: prefix sha256:d050e0e423a84e328288ec86c60af302071c77a669604a8c1c91c4bb70acc820 length:41015

Any other change to these files requires a fresh user approval and a
new freeze record.
