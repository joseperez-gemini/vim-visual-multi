## Annoying points

- Alt+n on start of line matches doesn't work (try on `hello`)
```
hello
hello
```

- Alt+n + Alt+n when multi matches on single line matches everything! (try on `test`)
```
    test test hello test test
    world test test test
    test test hello world test
    test test hello world test
```

- Allow \A for visual mode (highlight `test test` above and do \A)
- Undo for inserting ` word` at end of line splits undo for `word` and ` `
