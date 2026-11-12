# REQ-280 mock: edit flow

The documents describe neither the saved-entries list nor the edit form. Flow only:

```
 [ Saved entries (open question) ] --(pick entry)--> [ Edit entry (form: open question) ]
                                                             |
                                                  valid -----+----- invalid
                                                    v                  v
                                        [ Entry updated,        [ Error message,
                                          summary follows ]       entry unchanged ]
```
