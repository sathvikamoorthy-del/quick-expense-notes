# REQ-275 mock: sign in and sign out

## S01 Sign in

```
+--------------------------------------------------+
|  Quick Expense Notes                             |
|                                                  |
|  Sign in to see and change only your own         |
|  expenses.                                       |
|                                                  |
|  Email                                           |
|  [ asha@example.com                          ]   |
|                                                  |
|  Password (at least 8 characters)                |
|  [ ********                                  ]   |
|                                                  |
|  ! Invalid email or password.                    |
|    (shown only after a failed sign-in)           |
|                                                  |
|                                  [ Sign in ]     |
+--------------------------------------------------+
   No sign-up, no "forgot password", no Google button
   (out of scope for this story).
```

## S02 Entry box, signed in (header only)

```
+--------------------------------------------------+
|  Quick Expense Notes        asha@example.com     |
|                                  [ Sign out ]    |
+--------------------------------------------------+
|  (entry box: REQ-276 / REQ-277)                  |
```

## Flow

```
 [ Open app / refresh ] ----------------------------+
          |                                         |
          v                                         |
   [ S01 Sign in ] <---- wrong email or password:   |
          |              "Invalid email or          |
          |              password." (401)           |
   correct email + password                         |
   (token kept in memory only)                      |
          v                                         |
   [ S02 Entry box /entries ]                       |
          |                                         |
          +-- Sign out ------------> [ S01 Sign in ]
          +-- token older than 60 min (401) --> [ S01 Sign in ]
          +-- page refresh (token lost) ---------+

 Not signed in + open /entries, saved entries or summary
          --> [ S01 Sign in ]
```
