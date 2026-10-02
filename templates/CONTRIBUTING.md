# Contributing to Gatepost

Thank you for your interest in Gatepost. This guide explains how to make a change that we can merge.

Gatepost is unofficial. For problems with NIPOST's own app, data or API, contact NIPOST through the contact details on its official website.

## Before you start

1. Read `CODING_STANDARDS.md` and the files it names. Reviews cite their rule IDs.
2. Read `CONTEXT.md`. Use its terms in code, tests and docs.
3. For a change bigger than a small fix, open an issue first. Agree on the approach before you write code.
4. A change to the public interface starts in the `spec` repo (API-1).

## Make a change

1. Create a branch named `<type>/<short-description>`, for example `fix/unit-zero-message`.
2. Write a failing test first (T-1).
3. Make the test pass.
4. Run the repo's check command. The README of the repo names it.
5. Add a change file for each user-visible change (DOC-5).
6. If you changed the public interface, update the API report and the docs (GIT-7).

## Commit

- Use Conventional Commits, for example `fix(core): reject a unit of 00` (GIT-1).
- Keep the subject at 72 characters or fewer. Explain why in the body (TELL-18).
- Sign off each commit with `git commit -s` (GIT-2). The sign-off states that you accept the Developer Certificate of Origin at https://developercertificate.org.
- If you forget a sign-off, run `git rebase --signoff` with the base branch of your pull request, for example `git rebase --signoff origin/main`. Then push to your own branch with `git push --force-with-lease`. GIT-4 forbids a force-push only to `main` and to shared branches.
- You are the only author of your commits. Do not add co-author lines for AI tools (GIT-3).

## AI-assisted contributions

You can use AI tools. You are responsible for each line that you submit. If an AI tool wrote a large part of the change, say which parts in the pull request. The same standards apply to every line, whoever wrote it.

## Open a pull request

The title and the body of the pull request become the commit message on `main`, and CI checks both.

1. Keep it to one topic. Aim for 400 changed lines or fewer, not counting tests, vectors and generated files (GIT-5).
2. Write the title as a Conventional Commits subject, for example `fix(core): reject a unit of 00` (GIT-1). GitHub adds ` (#N)` to it, and the whole subject has 72 characters or fewer (TELL-18).
3. Fill in the pull request template.
   - Replace the first paragraph with two or three sentences of plain prose that say what the change does and why.
   - Replace `Closes #` with the number of the issue that the change closes, or remove the line.
   - Replace the sign-off line with your own name and address (GIT-2).
4. Before you ask for a review, check these points.
   - A failing test came first, and it passes now (T-1).
   - The repo's check command passes on your machine.
   - Each user-visible change has a change file (DOC-5).
   - If the public interface changed, you updated the API report and the docs (GIT-7).
   - Each new domain term is in `CONTEXT.md` (DOC-7).
   - The diff touches only the lines that the task needs (TELL-15).
   - Each commit has a sign-off from `git commit -s` (GIT-2).
5. Wait for green CI and one approval. We merge with squash (GIT-6).

## Rules from NIPOST

Gatepost follows NIPOST's terms and acceptable use policy:

- Call only the documented gateway endpoints.
- Commit only NIPOST's published test codes and synthetic values. Do not commit real API responses, NINs, email addresses or the postcodes of private homes.
- Do not use NIPOST's name or logo as branding.

## Licence

You submit each contribution under the Apache-2.0 licence.
