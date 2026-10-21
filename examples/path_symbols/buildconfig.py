from wosit.builder import addRule

# Every rule below runs in "src": its targets, its sources and $@, $^, $< are written from there.

# A pattern rule: src/alpha.up from src/alpha.txt, src/beta.up from src/beta.txt
addRule(
    path = "src",
    target = "%.up",
    source = "%.txt",
    command = "tr a-z A-Z < $< > $@"
)

# A source outside of the path is written from it too: ../include/header.txt
addRule(
    path = "src",
    target = "joined.txt",
    source = ["../include/header.txt", "alpha.up", "beta.up"],
    command = "cat $^ > $@"
)

# A rule without a path depends on them as seen from here
addRule(
    target = "result.txt",
    source = ["src/joined.txt", "./src/alpha.up"],
    command = "cp $< $@"
)


addRule(
    target = "all",
    source = "result.txt",
    phony = True
)


addRule(
    target = "clean",
    command = "rm -f result.txt src/joined.txt src/*.up",
    phony = True
)
