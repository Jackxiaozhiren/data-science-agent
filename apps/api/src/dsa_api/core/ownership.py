"""R-08: who a stored row belongs to -- one module owning the answer.

The hosted demo has no accounts and, by design, will not get them in this plan: `config.py` defaults
`auth_token` to `""`, and the plan's item 3 says a half-account system is worse than honesty. But *no accounts*
and *no ownership* are different things, and the second is the defect -- one visitor's uploaded file and run
ids are readable by the next visitor through the same unauthenticated API (B7).

So ownership here is a label on a row rather than an identity:

- **`OWNER_DEFAULT`** is the only owner a local instance ever uses. It is a constant, not a setting: a value
  the environment could change would let the model's column default and the migration's backfill disagree,
  and the two must be the same string by construction rather than by luck.
- **`OWNER_SHARED`** is the owner of the content this project publishes itself -- the sample datasets and the
  example runs the first screen is built from. It is a reserved id rather than a per-visitor one because a
  private demo with an empty first screen is a different product from the one R-01 shipped, and because the
  sample data is not a visitor's data to keep private. It is reserved in the strict sense: `normalise` will
  not hand it to a client, so a visitor can read the shared rows but can never stamp a row of their own
  public with them.
- **`OWNER_HEADER`** is how a browser says "these rows are mine" without an account. It is a bearer token in
  all but name -- a random id the client generates and stores -- so it is scoped to the honest threat model
  written down in `docs/hosted-demo.md`: it stops the *next visitor* reading your data, and it does not
  survive someone who deliberately forges an id they already know. Choosing a header over a cookie is not
  taste: the demo's web app and API sit on different origins, so a cookie would be third-party -- blocked
  outright in Safari and quietly dropped in Chrome -- and the exposure would remain while the code claimed
  otherwise.

`resolve_owner` is the single place that reads it, and the validation is a shape check plus a reserved-word
check rather than a trust check: an id that is not identifier-shaped, or that names the shared owner, is
ignored in favour of the default, so a request cannot smuggle a SQL fragment, a path, or a 10 KB blob into a
column that is indexed for lookups, and cannot claim the public rows as its own to write into.
"""

from __future__ import annotations

import re

from fastapi import Request

#: The owner of every row on a single-user local run, and the backfill for rows written before R-08.
OWNER_DEFAULT = "local"

#: The owner of the demo's own published content: readable from any request, never grantable to one.
OWNER_SHARED = "shared"

#: Request header a client uses to claim its own rows on a shared instance.
OWNER_HEADER = "X-DSA-Owner"

#: Query-string fallback, because a browser download (`<a href>` to an export) cannot set a header.
OWNER_QUERY = "owner"

_OWNER_SHAPE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def is_valid_owner(value: object) -> bool:
    """Whether `value` can be used as an owner id at all: a short, opaque, identifier-shaped token."""
    return isinstance(value, str) and _OWNER_SHAPE.match(value) is not None


def visible_to(owner: str) -> list[str]:
    """The owners whose rows a request acting for `owner` may read: its own, plus the published ones."""
    return [owner, OWNER_SHARED]


def normalise(value: object) -> str:
    """The value if it is well-shaped and grantable, otherwise the single local owner. Never empty."""
    if isinstance(value, str) and _OWNER_SHAPE.match(value) and value != OWNER_SHARED:
        return value
    return OWNER_DEFAULT


def resolve_owner(request: Request) -> str:
    """Which owner this request is acting for: the header, then the query, then the local default.

    Header first, and only the query as a fallback for the cases a header cannot reach -- a plain navigation
    or an anchor download. Both are shape-checked, because either is attacker-controlled.
    """
    header = request.headers.get(OWNER_HEADER)
    if header is not None:
        return normalise(header.strip())
    query = request.query_params.get(OWNER_QUERY)
    if query is not None:
        return normalise(query.strip())
    return OWNER_DEFAULT
