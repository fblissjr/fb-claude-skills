#!/usr/bin/env python3
"""Author trigger eval sets: 10 should-trigger, 6 near-miss should-not per skill."""
import json
from pathlib import Path

OUT = Path(__file__).parent / "evals"
OUT.mkdir(exist_ok=True)

S = {}

S["python-tooling"] = ([
    "pyright is throwing like 40 'Arguments missing for parameters' errors on all my pydantic models in src/models.py and as far as i can tell they're all false positives. how do i actually fix this instead of sprinkling type ignores everywhere",
    "i added a [tool.pyright] section to pyproject.toml to turn reportCallIssue off but its still showing the exact same errors. what am i doing wrong",
    "we're adding httpx to this project. should i pin it exact or use a floor constraint? its an application not a library",
    "can you just add # type: ignore to all the pyright errors in this repo so CI goes green, i dont have time to fix them properly",
    "getting reportCallIssue everywhere after i upgraded pydantic to v2. wall of red in the editor. before i start suppressing them is there something structural im missing",
    "whats the pinning policy here? i see some deps with == and some with >= and i dont know which to use for a new one",
    "the type checker hates my BaseModel subclasses. every single instantiation says arguments missing for parameters, even though the fields have defaults",
    "my pyproject pyright config seems to be ignored completely, the errors dont change no matter what i put in there",
    "i need to add three new packages to this python project and i want to get the version constraints right per our conventions",
    "pyright output is unreadable, hundreds of errors, mostly on pydantic stuff. help me work out whether these are real problems or a config issue",
], [
    "mypy is complaining about Optional types in src/utils.py, can you add the right annotations",
    "my pydantic model raises ValidationError at runtime when i pass a string for an int field. how do i get it to coerce instead",
    "ruff is flagging a bunch of E501 line too long errors, can you fix them",
    "i want to pin my npm dependencies exactly in package.json, whats the right way to do that",
    "write me a pydantic model matching this API response shape",
    "set up pyright in this repo from scratch, theres no config at all yet",
])

S["configure"] = ([
    "this repo actually uses npm, not bun. the convention rule keeps telling me to use bun and its wrong for this project, can you change that",
    "turn off the lockfile guard here, im doing manual lockfile surgery and it keeps blocking me",
    "i want to add a house rule that all sql lives in a queries/ folder, and have it load every session",
    "the pip block is getting in the way for this one repo, disable it just here please",
    "can you customise the dev conventions for this project? we use poetry rather than uv",
    "remove the doc conventions rule from this repo, we dont follow it here and its noise",
    "what dev conventions are actually enforced in this repo, and how do i change which ones are on",
    "add a rule to the session context that says never edit anything under vendor/",
    "we switched this project over to yarn. update whatever is currently enforcing bun",
    "i need to change which package manager rules are active for this repo only, not globally",
], [
    "add a permission to .claude/settings.json so npm commands stop prompting me",
    "set up pre-commit hooks for black and isort in this repo",
    "create a new skill for our internal deploy process",
    "configure pyright for this repo, it has no config yet",
    "change my claude code model to sonnet",
    "add an eslint config to this project with the airbnb rules",
])

S["dep-audit"] = ([
    "are the packages in this project safe? we're about to ship and i want to know if anything has a known CVE",
    "run a security audit on our dependencies, both the python ones and the node ones",
    "check deps for vulnerabilities before the release goes out tomorrow",
    "someone flagged that one of our transitive deps had a critical advisory. can you check the whole tree",
    "vulnerability scan on this repo's dependencies please, then tell me what needs upgrading",
    "i want a CVE check across both the uv and bun packages in here",
    "before i publish this package, is anything in the dependency set vulnerable",
    "audit dependencies in this repo and tell me if anything needs upgrading urgently",
    "our security team asked for a list of known vulnerabilities in our third party packages, can you produce that",
    "is my lockfile pulling in anything with a published advisory against it",
], [
    "update all my dependencies to their latest versions",
    "do a security review of the auth code i just wrote",
    "why is uv.lock conflicting on this branch, help me resolve it",
    "scan this repo for hardcoded api keys before i push",
    "which packages am i actually importing vs whats declared in pyproject, find the unused ones",
    "add bandit to CI for static security analysis of our own code",
])

S["doc-conventions"] = ([
    "write a README for the tools/agent-state package, following whatever conventions this repo uses",
    "i need to write up a design doc for the new caching layer. where should it go and what should it look like",
    "update the README, its out of date since we removed two of the plugins yesterday",
    "write the session log for today's work",
    "document why we chose duckdb over sqlite here, as an actual doc not a code comment",
    "add docs for this module. should they go in docs/ or internal/?",
    "im about to create a bunch of new markdown docs, whats the naming convention in this repo",
    "we need a doc explaining the version cascade for new contributors, written the way our other docs are",
    "log what we did this session in the usual place",
    "add a design doc for the retry logic and make sure it has whatever header metadata our docs need",
], [
    "generate API reference docs from the docstrings in tools/",
    "add docstrings to every function in utils.py",
    "write a good commit message for these changes",
    "update CLAUDE.md with what we learned this session",
    "write release notes for the 0.13.0 release",
    "explain how this module works, im trying to understand the flow",
])

S["plain-language-us"] = ([
    "edit report.md into our house style - plain english, active voice, front loaded, no em dashes. its currently full of consultant-speak",
    "this research write up is 2000 words of passive voice and nominalizations. tighten it into plain english and keep it consistent all the way through",
    "rewrite the guidance section of draft.md so a non specialist can follow it. plain language, no jargon, sentence case headings",
    "our docs use Title Case Headings And Lots Of Bold For Emphasis. clean that up across README.md to match how i normally write",
    "make this summary readable - front load the conclusion, cut the hedging, put it in active voice",
    "apply house style to draft.md and tell me what you changed",
    "this exec summary is unreadable. do a plain english pass and strip out the em dashes, i hate them",
    "i wrote this spec in a hurry and its full of long passive sentences. edit the whole thing for clarity",
    "convert all of report.md to plain language - sentence case, no italics for emphasis, shorter sentences",
    "clean up the prose in this doc, its got that AI-ish bolded-phrase thing going on in every paragraph",
], [
    "draft a reply to this email that sounds like me, you've seen how i write in this thread",
    "translate report.md into spanish",
    "make this landing page copy punchier and more persuasive, right now its too flat",
    "proofread this for typos and grammar mistakes only, dont touch the style",
    "summarize this 40 page pdf down to 5 bullets",
    "rewrite this in formal academic register for a journal submission",
])

S["voice-match"] = ([
    "draft a reply to this recruiter email that sounds like me, not like a bot wrote it",
    "write the announcement post for this release in my voice",
    "i need to respond to this github issue. write it the way i'd actually write it",
    "can you write this slack message so it sounds like me? i dont want it reading as AI generated",
    "match my tone for this - its a note to my team about the reorg and it needs to sound like me",
    "write a short intro paragraph for my README in my style",
    "based on how ive been writing in this conversation, draft the follow up email for me",
    "i need a cover note for this proposal. make it sound like i wrote it, use my saved voice profile",
    "rewrite this draft so it reads like me rather than like a corporate press release",
    "write my part of the standup update, in my style, keep it short",
], [
    "rewrite this in plain english, active voice, no em dashes",
    "write a formal press release announcing our funding round",
    "edit this so it matches our company brand tone guidelines",
    "make this sound more professional",
    "transcribe this audio note into text",
    "write a character's dialogue for my short story, she's sarcastic and clipped",
])

S["quality"] = ([
    "are my skills ok? i just consolidated a bunch of them and want to know if anything is broken",
    "run the quality report on this skills repo",
    "check skill health for me - spec compliance, token budget, all of it",
    "how big are my skill files? am i blowing the token budget anywhere",
    "which of my skill descriptions are weak or too short to trigger properly",
    "check quality on the postmortem skill specifically",
    "give me a quality report across the repo",
    "do my plugin.json versions line up with marketplace.json across all the plugins here",
    "give me a health report for all the skills in this repo before i publish",
    "i want to see spec compliance for my skills, i think a couple have malformed frontmatter",
], [
    "run the linter and fix any code quality issues in tools/",
    "check test coverage for the skill-maintainer package",
    "review this pull request for bugs before i merge it",
    "run a full maintenance pass - pull upstream docs and sync the tracked sources",
    "assess the quality of this dataset, i think theres missing values",
    "is my CLAUDE.md any good? audit it for me",
])

S["init-maintenance"] = ([
    "set up skill-maintainer in this repo, i want the config and the pre-commit hook installed",
    "add maintenance to this project - i just started a new skills repo and want the tracking in place",
    "initialize skill-maintainer here please",
    "i need the .skill-maintainer directory with the best practices checklist set up in this repo",
    "bootstrap the maintenance tooling in this new repo so i can start using it",
    "install the skills pre-commit hook and whatever state tracking goes along with it",
    "this is a fresh repo, get maintenance set up so i can start tracking upstream drift",
    "init maintenance in this repo and show me what it created",
    "can you set up the skill maintenance system here from scratch",
    "i cloned this repo on a new machine and .skill-maintainer isnt there. set it up again",
], [
    "run a maintenance pass, check upstream docs and review the best practices",
    "set up pre-commit hooks for ruff and black in this python repo",
    "initialize a new git repo here and make the first commit",
    "set up CI for this repo with github actions",
    "check the quality of my skills, i want the health report",
    "create a new skill from scratch in this repo",
])

S["json-query"] = ([
    "ive got a 400MB json file of api logs and i need to pull out every entry where status is 500 along with the request id. whats the least painful way to do that",
    "how do i get all the values of a deeply nested key out of this config json without writing a whole script",
    "filter this json array down to only the objects where price is over 100 and print their names",
    "whats a decent alternative to jq? the syntax kills me every single time i use it",
    "i need to search a big json dump for any key containing 'token' - which tool should i reach for",
    "extract the email field from every record in users.json and dedupe them",
    "this json is too big to open in an editor. i need to query it for a few specific paths",
    "help me write a json path query to grab all the nested items[].sku values",
    "i want grep-like search across a json file, is there something better than plain grep for this",
    "i have a 2gb newline delimited json file and need to count records by their type field",
], [
    "parse this json string in my python script and handle the KeyError properly",
    "convert data.json into a csv i can open in excel",
    "validate data.json against this json schema and tell me whats wrong",
    "pretty print this json file, its all on one line and unreadable",
    "why is my json invalid? theres a trailing comma somewhere and i cant find it",
    "design the json response shape for the users endpoint of our api",
])

S["plugin-toolkit"] = ([
    "review my claude code plugin - i think the structure is off and some commands are missing",
    "whats wrong with my plugin? it installs fine but the commands dont show up properly",
    "add a help command to my plugin, plus whatever other standard commands it ought to have",
    "evaluate this plugin i built and tell me what i should improve about it",
    "i want to add a new command to my existing plugin, and remove one thats gone unused",
    "check plugin quality before i publish this one to my marketplace",
    "polish my plugin - add the standard utility commands its currently missing",
    "do a plugin review on skills/postmortem, structure and completeness",
    "improve my plugin structure, its grown organically and its a mess now",
    "analyze this claude code plugin and give me a report on whats missing from it",
], [
    "create a new skill from scratch for our deploy process",
    "publish this plugin to the marketplace and bump the version everywhere",
    "write a vscode extension that highlights our custom template syntax",
    "my eslint plugin config is broken, fix it",
    "add a hook that blocks commits containing TODO comments",
    "what plugins do i have installed and which ones are actually enabled",
])

S["scan-for-secrets"] = ([
    "im about to publish this session transcript as a blog post. check it for anything sensitive first - keys, my home path, emails",
    "did i leak an api key anywhere in this repo? check before i push it public",
    "scan these logs before i share them with the vendor",
    "strip my username out of these transcripts, theres a bunch of /Users/ paths in there",
    "pre-share scan on the internal/ folder please, its going to a client",
    "check for leaked credentials in both the git history and the working tree",
    "i need a PII scan on this export before it goes to the client - emails, ips, anything identifying",
    "find any JWTs or bearer tokens sitting around in these files",
    "audit this before i commit, i pasted a load of terminal output and im not sure whats in it",
    "redact home paths and any personal info from the files in docs/ before i publish them",
], [
    "my api key got committed last week, help me rotate it and purge it from the history",
    "add my openai key to .env and make sure the file is gitignored",
    "check this repo for absolute paths that point outside the repo root",
    "audit dependencies for CVEs before the release",
    "set up a secrets manager for our production deployment",
    "review my auth implementation for security holes",
])

for name, (pos, neg) in S.items():
    items = [{"query": q, "should_trigger": True} for q in pos]
    items += [{"query": q, "should_trigger": False} for q in neg]
    assert len(pos) == 10 and len(neg) == 6, name
    (OUT / f"{name}.json").write_text(json.dumps(items, indent=2))
    print(f"{name}: {len(items)} queries")
