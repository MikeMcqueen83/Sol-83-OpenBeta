# Ochrona gałęzi main / Protecting main

Instrukcja dla autora; Sol-83 sam nie zmienia ustawień repozytoriów. Wykonaj dopiero po decyzji o publikacji.

Repository settings → Branches → Add branch protection rule (`main`):
- Require a pull request before merging (min. 1 approval),
- Require status checks to pass (testy, jeśli zostanie dodane CI),
- Do not allow force pushes and deletions,
- Restrict who can push to matching branches (autor).

Tym samym za pomocą GitHub CLI (przykład, do przejrzenia przed użyciem):

```bash
gh api -X PUT repos/MikeMcqueen83/Sol-83-OpenBeta/branches/main/protection \
  -f required_status_checks=null -F enforce_admins=true \
  -f 'required_pull_request_reviews[required_approving_review_count]=1' \
  -F allow_force_pushes=false -F allow_deletions=false -f restrictions=null
```

Ochrona gałęzi nie chroni przed pobraniem kodu publicznego repozytorium: kontroluje tylko zmiany w nim.
